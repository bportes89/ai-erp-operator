import re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Customer, Operation, OperationItem, ProductMapping


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


async def get_customer(
    session: AsyncSession, organization_id: str, tax_id: str | None, name: str | None
) -> Customer | None:
    if not tax_id:
        return None
    digits = re.sub(r"\D", "", tax_id)
    if not digits:
        return None
    customer = await session.scalar(
        select(Customer).where(
            Customer.organization_id == organization_id, Customer.tax_id == digits
        )
    )
    if customer:
        return customer
    if name:
        existing = await session.scalar(
            select(Customer).where(
                Customer.organization_id == organization_id, Customer.name == name
            )
        )
        if existing:
            existing.tax_id = digits
            return existing
        customer = Customer(organization_id=organization_id, tax_id=digits, name=name)
        session.add(customer)
        await session.flush()
        return customer
    return None


async def apply_matches(session: AsyncSession, op: Operation) -> None:
    """Associa itens a mapeamentos conhecidos e aplica defaults do cliente."""
    org = op.organization_id
    mappings = list(
        await session.scalars(select(ProductMapping).where(ProductMapping.organization_id == org))
    )
    by_code = {m.customer_code: m for m in mappings}
    by_desc = {_norm(m.description): m for m in mappings}
    for item in op.items:
        matched = False
        mapping = None
        if item.customer_code and item.customer_code in by_code:
            mapping = by_code[item.customer_code]
        elif item.description and _norm(item.description) in by_desc:
            mapping = by_desc[_norm(item.description)]
        if mapping:
            item.erp_code = mapping.erp_code
            item.matched = True
            mapping.usage_count += 1
            matched = True
        if not matched and item.erp_code:
            item.matched = True
    customer = await get_customer(session, org, op.tax_id, op.supplier)
    if customer:
        if customer.default_cost_center and not op.cost_center:
            op.cost_center = customer.default_cost_center
        if customer.erp_id:
            op.raw_extraction["customer_erp_id"] = customer.erp_id


async def learn_mapping(session: AsyncSession, item: OperationItem, org_id: str) -> ProductMapping | None:
    """Correção manual de item com erp_code -> memoriza o mapeamento (memória operacional)."""
    if not item.erp_code:
        return None
    if not item.customer_code and not item.description:
        return None
    key = item.customer_code or item.description
    existing = await session.scalar(
        select(ProductMapping).where(
            ProductMapping.organization_id == org_id,
            ProductMapping.customer_code == key,
        )
    )
    if existing:
        existing.erp_code = item.erp_code
        existing.description = item.description or existing.description
        return existing
    mapping = ProductMapping(
        organization_id=org_id,
        customer_code=key,
        description=item.description or key,
        erp_code=item.erp_code,
    )
    session.add(mapping)
    await session.flush()
    return mapping
