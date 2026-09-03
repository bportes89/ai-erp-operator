import asyncio
import re
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import record_event
from app.config import get_settings
from app.database import get_session
from app.erp import ManualExecutionError, execute_with_fallback
from app.export import operation_to_csv, operation_to_xml
from app.jobs import dispatch, process_operation
from app.matching import apply_matches, get_customer, learn_mapping
from app.rules import approval_threshold
from app.models import (
    AuditEvent,
    Customer,
    IdempotencyKey,
    Operation,
    OperationStatus,
    Organization,
    ProcessRecipe,
    ProductMapping,
    User,
    Webhook,
    WebhookDelivery,
)
from app.rate_limit import rate_limit
from app.schemas import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    DashboardOut,
    DailyROI,
    ExecuteResult,
    ItemPatch,
    LoginRequest,
    MappingCreate,
    MappingOut,
    OperationOut,
    OperationPatch,
    OrgSettings,
    RecipeCreate,
    RecipeOut,
    RecipeUpdate,
    RegisterRequest,
    ROIOut,
    Token,
    WebhookCreate,
    WebhookDeliveryOut,
    WebhookOut,
)
from app.security import create_token, current_user, hash_password, require_roles, verify_password
from app.storage import ObjectStorage
from app.webhooks import fire_webhooks

router = APIRouter(prefix="/api/v1")


@router.post("/auth/login", response_model=Token, dependencies=[Depends(rate_limit(5, 60))])
async def login(body: LoginRequest, session: AsyncSession = Depends(get_session)):
    user = await session.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas")
    return Token(access_token=create_token(user))


@router.post(
    "/auth/register",
    response_model=Token,
    status_code=201,
    dependencies=[Depends(rate_limit(5, 3600))],
)
async def register(body: RegisterRequest, session: AsyncSession = Depends(get_session)):
    existing = await session.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(409, "E-mail já cadastrado")
    org = Organization(name=body.organization or f"Empresa de {body.name}")
    session.add(org)
    await session.flush()
    user = User(
        organization_id=org.id,
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        role="admin",
    )
    session.add(user)
    session.add(
        ProcessRecipe(
            organization_id=org.id,
            name="Pedido de Venda",
            description="Pedido B2B em PDF convertido em pedido de venda no ERP",
            operation_type="sales_order.create",
            required_fields=["tax_id"],
        )
    )
    await record_event(
        session,
        org.id,
        "user.created",
        {"email": body.email},
        actor_id=user.id,
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(409, "E-mail já cadastrado") from None
    return Token(access_token=create_token(user))


@router.get("/operations", response_model=list[OperationOut])
async def list_operations(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    rows = await session.scalars(
        select(Operation)
        .where(Operation.organization_id == user.organization_id)
        .order_by(Operation.created_at.desc(), Operation.id.desc())
        .limit(100)
    )
    return list(rows)


@router.post("/operations", response_model=OperationOut, status_code=202, dependencies=[Depends(rate_limit(10, 60))])
async def create_operation(
    file: UploadFile = File(...),
    recipe_id: str | None = Form(default=None),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    content = await file.read()
    limit = get_settings().max_upload_mb * 1024 * 1024
    if len(content) > limit:
        raise HTTPException(413, "Arquivo excede o limite")
    if file.content_type != "application/pdf":
        raise HTTPException(415, "Envie um arquivo PDF")
    op = Operation(
        organization_id=user.organization_id,
        reference=f"PENDING-{uuid.uuid4().hex[:8].upper()}",
        filename=file.filename or "document.pdf",
        raw_content=content,
        total=0,
        confidence=0,
        status=OperationStatus.PROCESSING,
    )
    if recipe_id:
        recipe = await session.scalar(
            select(ProcessRecipe).where(
                ProcessRecipe.id == recipe_id,
                ProcessRecipe.organization_id == user.organization_id,
            )
        )
        if not recipe:
            raise HTTPException(404, "Processo não encontrado")
        op.recipe_id = recipe.id
    session.add(op)
    await session.flush()
    try:
        key = f"{user.organization_id}/{op.id}/{file.filename}"
        await ObjectStorage().put(key, content, file.content_type)
        op.storage_key = key
    except Exception:
        op.storage_key = None
    await record_event(
        session,
        user.organization_id,
        "operation.received",
        {"filename": file.filename},
        op.id,
        user.id,
    )
    await session.commit()
    await session.refresh(op)
    if get_settings().extraction_inline:
        await process_operation(op.id)
        await session.refresh(op)
    else:
        asyncio.create_task(dispatch(op.id))
    return op


@router.patch("/operations/{operation_id}", response_model=OperationOut)
async def patch_operation(
    operation_id: str,
    body: OperationPatch,
    user: User = Depends(require_roles("operator", "admin")),
    session: AsyncSession = Depends(get_session),
):
    op = await session.scalar(
        select(Operation).where(
            Operation.id == operation_id, Operation.organization_id == user.organization_id
        )
    )
    if not op:
        raise HTTPException(404, "Operação não encontrada")
    before = {field: getattr(op, field) for field in body.model_dump(exclude_none=True)}
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(op, field, value)
    if body.tax_id:
        digits = re.sub(r"\D", "", body.tax_id)
        if digits:
            op.tax_id = digits
            customer = await get_customer(session, user.organization_id, digits, op.supplier)
            if customer and op.supplier and not customer.name:
                customer.name = op.supplier
    op.status = (
        OperationStatus.REVIEW
        if op.confidence < 85 or (op.issues or [])
        else OperationStatus.READY
    )
    await record_event(
        session,
        user.organization_id,
        "operation.corrected",
        {"before": before, "after": body.model_dump(exclude_none=True)},
        op.id,
        user.id,
    )
    await session.commit()
    await session.refresh(op)
    return op


@router.patch("/operations/{operation_id}/items/{item_id}", response_model=OperationOut)
async def patch_item(
    operation_id: str,
    item_id: str,
    body: ItemPatch,
    user: User = Depends(require_roles("operator", "admin")),
    session: AsyncSession = Depends(get_session),
):
    op = await session.scalar(
        select(Operation).where(
            Operation.id == operation_id, Operation.organization_id == user.organization_id
        )
    )
    if not op:
        raise HTTPException(404, "Operação não encontrada")
    item = next((i for i in op.items if i.id == item_id), None)
    if not item:
        raise HTTPException(404, "Item não encontrado")
    before = {field: getattr(item, field) for field in body.model_dump(exclude_none=True)}
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    if body.quantity is not None or body.unit_price is not None:
        item.total = round(item.quantity * item.unit_price, 2)
    if body.erp_code:
        item.matched = True
        mapping = await learn_mapping(session, item, user.organization_id)
        await record_event(
            session,
            user.organization_id,
            "mapping.learned",
            {"customer_code": mapping.customer_code, "erp_code": mapping.erp_code},
            op.id,
            user.id,
        )
    if body.erp_code is None and body.customer_code:
        await apply_matches(session, op)
    await record_event(
        session,
        user.organization_id,
        "item.corrected",
        {"before": before, "after": body.model_dump(exclude_none=True)},
        op.id,
        user.id,
    )
    op.status = (
        OperationStatus.REVIEW
        if op.confidence < 85 or (op.issues or [])
        else OperationStatus.READY
    )
    await session.commit()
    await session.refresh(op)
    return op


@router.post("/operations/{operation_id}/rematch", response_model=OperationOut)
async def rematch(
    operation_id: str,
    user: User = Depends(require_roles("operator", "admin")),
    session: AsyncSession = Depends(get_session),
):
    op = await session.scalar(
        select(Operation).where(
            Operation.id == operation_id, Operation.organization_id == user.organization_id
        )
    )
    if not op:
        raise HTTPException(404, "Operação não encontrada")
    for item in op.items:
        item.matched = False
    await apply_matches(session, op)
    await record_event(session, user.organization_id, "operation.rematched", {}, op.id, user.id)
    await session.commit()
    await session.refresh(op)
    return op


@router.post("/operations/{operation_id}/approve", response_model=OperationOut)
async def approve_operation(
    operation_id: str,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    op = await session.scalar(
        select(Operation).where(
            Operation.id == operation_id, Operation.organization_id == user.organization_id
        )
    )
    if not op:
        raise HTTPException(404, "Operação não encontrada")
    if op.status != OperationStatus.PENDING_APPROVAL:
        raise HTTPException(409, "Operação não está aguardando aprovação")
    op.status = OperationStatus.READY
    await record_event(
        session,
        user.organization_id,
        "operation.approved",
        {"reference": op.reference, "total": float(op.total)},
        op.id,
        user.id,
    )
    await session.commit()
    await session.refresh(op)
    return op


@router.post("/operations/{operation_id}/reject", response_model=OperationOut)
async def reject_operation(
    operation_id: str,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    op = await session.scalar(
        select(Operation).where(
            Operation.id == operation_id, Operation.organization_id == user.organization_id
        )
    )
    if not op:
        raise HTTPException(404, "Operação não encontrada")
    if op.status != OperationStatus.PENDING_APPROVAL:
        raise HTTPException(409, "Operação não está aguardando aprovação")
    op.status = OperationStatus.REVIEW
    op.issues = [*(op.issues or []), "Aprovação de valor recusada"]
    await record_event(
        session,
        user.organization_id,
        "operation.rejected",
        {"reference": op.reference, "total": float(op.total)},
        op.id,
        user.id,
    )
    await session.commit()
    await session.refresh(op)
    return op


@router.get("/organization/settings", response_model=OrgSettings)
async def organization_settings(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    org = await session.get(Organization, user.organization_id)
    return OrgSettings(
        approval_threshold=approval_threshold(org.settings if org else {})
    )


@router.patch("/organization/settings", response_model=OrgSettings)
async def update_organization_settings(
    body: OrgSettings,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    org = await session.get(Organization, user.organization_id)
    if not org:
        raise HTTPException(404, "Organização não encontrada")
    settings = dict(org.settings or {})
    settings["approval_threshold"] = body.approval_threshold
    org.settings = settings
    await record_event(
        session,
        user.organization_id,
        "organization.settings_updated",
        {"approval_threshold": body.approval_threshold},
        actor_id=user.id,
    )
    await session.commit()
    await session.refresh(org)
    return OrgSettings(approval_threshold=approval_threshold(org.settings))


@router.get("/recipes", response_model=list[RecipeOut])
async def recipes(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return list(
        await session.scalars(
            select(ProcessRecipe)
            .where(ProcessRecipe.organization_id == user.organization_id)
            .order_by(ProcessRecipe.created_at)
        )
    )


@router.post("/recipes", response_model=RecipeOut, status_code=201)
async def create_recipe(
    body: RecipeCreate,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    row = ProcessRecipe(organization_id=user.organization_id, **body.model_dump())
    session.add(row)
    await record_event(
        session,
        user.organization_id,
        "recipe.created",
        {"name": body.name, "operation_type": body.operation_type},
        actor_id=user.id,
    )
    await session.commit()
    await session.refresh(row)
    return row


@router.patch("/recipes/{recipe_id}", response_model=RecipeOut)
async def update_recipe(
    recipe_id: str,
    body: RecipeUpdate,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    row = await session.scalar(
        select(ProcessRecipe).where(
            ProcessRecipe.id == recipe_id,
            ProcessRecipe.organization_id == user.organization_id,
        )
    )
    if not row:
        raise HTTPException(404, "Processo não encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    await record_event(
        session,
        user.organization_id,
        "recipe.updated",
        {"name": row.name},
        actor_id=user.id,
    )
    await session.commit()
    await session.refresh(row)
    return row


@router.delete("/recipes/{recipe_id}", status_code=204)
async def delete_recipe(
    recipe_id: str,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    row = await session.scalar(
        select(ProcessRecipe).where(
            ProcessRecipe.id == recipe_id,
            ProcessRecipe.organization_id == user.organization_id,
        )
    )
    if not row:
        raise HTTPException(404, "Processo não encontrado")
    row.active = False
    await session.commit()


@router.post("/operations/{operation_id}/execute", response_model=ExecuteResult)
async def execute(
    operation_id: str,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    user: User = Depends(require_roles("operator", "admin")),
    session: AsyncSession = Depends(get_session),
):
    cached = await session.get(IdempotencyKey, idempotency_key)
    if cached:
        return ExecuteResult(**cached.response)
    op = await session.scalar(
        select(Operation).where(
            Operation.id == operation_id, Operation.organization_id == user.organization_id
        )
    )
    if not op:
        raise HTTPException(404, "Operação não encontrada")
    if op.status not in {OperationStatus.READY, OperationStatus.REVIEW}:
        raise HTTPException(409, "Operação não está pronta")
    if op.issues:
        raise HTTPException(422, "Corrija os problemas antes de executar")
    if any(not item.matched for item in op.items):
        raise HTTPException(422, "Existem produtos sem mapeamento")
    try:
        result, strategy, failed = await execute_with_fallback(op, idempotency_key)
    except ManualExecutionError as exc:
        raise HTTPException(409, str(exc)) from exc
    except Exception as exc:
        op.status = OperationStatus.FAILED
        await record_event(
            session,
            user.organization_id,
            "erp.failed",
            {"error": str(exc)},
            op.id,
            user.id,
        )
        await session.commit()
        raise HTTPException(502, f"Falha na execução: {exc}") from exc
    op.status = OperationStatus.COMPLETED
    response = {
        "operation_id": op.id,
        "external_id": result["external_id"],
        "status": result["status"],
        "executed_at": datetime.now(timezone.utc),
    }
    session.add(
        IdempotencyKey(
            key=idempotency_key,
            organization_id=user.organization_id,
            response={**response, "executed_at": response["executed_at"].isoformat()},
        )
    )
    await record_event(
        session,
        user.organization_id,
        "erp.executed",
        {
            "external_id": result["external_id"],
            "strategy": strategy,
            "failed_previous": failed,
        },
        op.id,
        user.id,
    )
    if failed:
        await record_event(
            session,
            user.organization_id,
            "erp.fallback",
            {"from": failed, "to": strategy},
            op.id,
            user.id,
        )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        cached = await session.get(IdempotencyKey, idempotency_key)
        if cached:
            return ExecuteResult(**cached.response)
        raise HTTPException(409, "Falha de idempotência")
    fire_webhooks(
        session,
        user.organization_id,
        "erp.executed",
        {
            "operation_id": op.id,
            "reference": op.reference,
            "external_id": response["external_id"],
            "status": "completed",
        },
    )
    return ExecuteResult(**response)


@router.get("/operations/{operation_id}/export")
async def export_operation(
    operation_id: str,
    format: str = Query(default="csv", pattern="^(csv|xml)$"),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    op = await session.scalar(
        select(Operation).where(
            Operation.id == operation_id, Operation.organization_id == user.organization_id
        )
    )
    if not op:
        raise HTTPException(404, "Operação não encontrada")
    if format == "xml":
        content = operation_to_xml(op)
        return Response(
            content=content,
            media_type="application/xml",
            headers={"Content-Disposition": f'attachment; filename="{op.reference}.xml"'},
        )
    content = operation_to_csv(op)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{op.reference}.csv"'},
    )


@router.get("/mappings", response_model=list[MappingOut])
async def mappings(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return list(
        await session.scalars(
            select(ProductMapping).where(ProductMapping.organization_id == user.organization_id)
        )
    )


@router.post("/mappings", response_model=MappingOut, status_code=201)
async def create_mapping(
    body: MappingCreate,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    row = ProductMapping(organization_id=user.organization_id, **body.model_dump())
    session.add(row)
    await record_event(
        session, user.organization_id, "mapping.created", body.model_dump(), actor_id=user.id
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(ProductMapping).where(
                ProductMapping.organization_id == user.organization_id,
                ProductMapping.customer_code == body.customer_code,
            )
        )
        if existing:
            return existing
        raise
    await session.refresh(row)
    return row


@router.get("/customers", response_model=list[CustomerOut])
async def customers(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return list(
        await session.scalars(
            select(Customer).where(Customer.organization_id == user.organization_id).limit(200)
        )
    )


@router.post("/customers", response_model=CustomerOut, status_code=201)
async def create_customer(
    body: CustomerCreate,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    row = Customer(
        organization_id=user.organization_id,
        tax_id=re.sub(r"\D", "", body.tax_id),
        **body.model_dump(exclude={"tax_id"}),
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing = await session.scalar(
            select(Customer).where(
                Customer.organization_id == user.organization_id,
                Customer.tax_id == re.sub(r"\D", "", body.tax_id),
            )
        )
        if existing:
            return existing
        raise
    await session.refresh(row)
    return row


@router.patch("/customers/{customer_id}", response_model=CustomerOut)
async def patch_customer(
    customer_id: str,
    body: CustomerUpdate,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    row = await session.scalar(
        select(Customer).where(
            Customer.id == customer_id, Customer.organization_id == user.organization_id
        )
    )
    if not row:
        raise HTTPException(404, "Cliente não encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(row, field, value)
    await record_event(
        session,
        user.organization_id,
        "customer.updated",
        body.model_dump(exclude_none=True),
        actor_id=user.id,
    )
    await session.commit()
    await session.refresh(row)
    return row


@router.get("/webhooks", response_model=list[WebhookOut])
async def webhooks(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return list(
        await session.scalars(select(Webhook).where(Webhook.organization_id == user.organization_id))
    )


@router.post("/webhooks", response_model=WebhookOut, status_code=201)
async def create_webhook(
    body: WebhookCreate,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    row = Webhook(
        organization_id=user.organization_id,
        url=body.url,
        secret=body.secret or secrets.token_hex(32),
        events=body.events or ["erp.executed", "operation.ready"],
    )
    session.add(row)
    await record_event(
        session, user.organization_id, "webhook.created", {"url": body.url}, actor_id=user.id
    )
    await session.commit()
    await session.refresh(row)
    return row


@router.delete("/webhooks/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: str,
    user: User = Depends(require_roles("admin")),
    session: AsyncSession = Depends(get_session),
):
    row = await session.scalar(
        select(Webhook).where(
            Webhook.id == webhook_id, Webhook.organization_id == user.organization_id
        )
    )
    if not row:
        raise HTTPException(404, "Webhook não encontrado")
    row.active = False
    await session.commit()


@router.get("/webhooks/deliveries", response_model=list[WebhookDeliveryOut])
async def webhook_deliveries(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    return list(
        await session.scalars(
            select(WebhookDelivery)
            .join(Webhook, Webhook.id == WebhookDelivery.webhook_id)
            .where(Webhook.organization_id == user.organization_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(50)
        )
    )


@router.get("/audit")
async def audit(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(
        select(AuditEvent)
        .where(AuditEvent.organization_id == user.organization_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(100)
    )
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "operation_id": e.operation_id,
            "payload": e.payload,
            "hash": e.hash,
            "previous_hash": e.previous_hash,
            "created_at": e.created_at,
        }
        for e in rows
    ]


@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(
    user: User = Depends(current_user), session: AsyncSession = Depends(get_session)
):
    rows = list(
        await session.scalars(
            select(Operation).where(Operation.organization_id == user.organization_id)
        )
    )
    completed = sum(o.status == OperationStatus.COMPLETED for o in rows)
    pending = len(rows) - completed
    rate = round(completed / len(rows) * 100, 1) if rows else 0
    return DashboardOut(
        pending=pending,
        completed=completed,
        automation_rate=rate,
        minutes_saved=round(completed * 7.3, 1),
        processed_value=sum(o.total for o in rows if o.status == OperationStatus.COMPLETED),
    )


MANUAL_MINUTES_PER_ORDER = 8.0


@router.get("/roi", response_model=ROIOut)
async def roi(user: User = Depends(current_user), session: AsyncSession = Depends(get_session)):
    org = user.organization_id
    ops = list(
        await session.scalars(
            select(Operation).where(Operation.organization_id == org)
        )
    )
    events = list(
        await session.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == org)
            .order_by(AuditEvent.created_at)
        )
    )
    by_op: dict[str, dict[str, datetime]] = {}
    corrected: set[str] = set()
    for event in events:
        if not event.operation_id:
            continue
        by_op.setdefault(event.operation_id, {})[event.event_type] = event.created_at
        if event.event_type in ("operation.corrected", "item.corrected"):
            corrected.add(event.operation_id)

    completed_ops = [o for o in ops if o.status == OperationStatus.COMPLETED]
    processing_times: list[float] = []
    to_erp_times: list[float] = []
    for op in ops:
        times = by_op.get(op.id, {})
        received = times.get("operation.received")
        extracted = times.get("operation.extracted")
        executed = times.get("erp.executed")
        if received and extracted:
            processing_times.append((extracted - received).total_seconds())
        if received and executed:
            to_erp_times.append((executed - received).total_seconds())

    total = len(ops)
    exceptions = len(corrected) + sum(
        1 for o in ops if o.status in (OperationStatus.REVIEW, OperationStatus.FAILED)
    )
    exception_rate = round(exceptions / total * 100, 1) if total else 0.0
    automation_rate = round(100 - exception_rate, 1)
    processed_value = sum(float(o.total) for o in completed_ops)
    hours_saved = round(len(completed_ops) * MANUAL_MINUTES_PER_ORDER / 60, 1)
    avg_confidence = round(sum(o.confidence for o in ops) / total) if total else 0

    daily: dict[str, list] = {}
    for op in ops:
        day = op.created_at.date().isoformat()
        row = daily.setdefault(day, {"operations": 0, "completed": 0, "value": 0.0})
        row["operations"] += 1
        if op.status == OperationStatus.COMPLETED:
            row["completed"] += 1
            row["value"] += float(op.total)
    daily_rows = [
        DailyROI(
            date=day,
            operations=row["operations"],
            completed=row["completed"],
            value=round(row["value"], 2),
        )
        for day, row in sorted(daily.items())[-14:]
    ]

    return ROIOut(
        total_operations=total,
        completed=len(completed_ops),
        pending=total - len(completed_ops),
        automation_rate=automation_rate,
        exception_rate=exception_rate,
        avg_processing_seconds=round(sum(processing_times) / len(processing_times), 1)
        if processing_times
        else 0.0,
        avg_time_to_erp_seconds=round(sum(to_erp_times) / len(to_erp_times), 1)
        if to_erp_times
        else 0.0,
        processed_value=processed_value,
        hours_saved=hours_saved,
        avg_confidence=avg_confidence,
        daily=daily_rows,
    )
