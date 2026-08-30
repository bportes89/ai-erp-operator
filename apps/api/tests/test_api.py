import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_api.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["STORAGE_ENABLED"] = "false"

import pytest
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import get_session
from app.main import app
from app.models import Base, Operation, OperationStatus, Organization, User
from app.security import hash_password


def _minimal_pdf() -> bytes:
    content = (
        "BT /F1 12 Tf 72 740 Td (Referencia: PC-2026-100) Tj 0 -16 Td "
        "(Cliente: Construtora Alfa) Tj 0 -16 Td (CNPJ: 11.222.333/0001-81) Tj 0 -16 Td "
        "(Total: R$ 2.297,00) Tj 0 -24 Td (Produto Qtd Valor Total) Tj 0 -16 Td "
        "(CIM-1 Cimento Premium 30 49.90 1497.00) Tj 0 -16 Td "
        "(ARE-2 Areia Fina 10 80.00 800.00) Tj ET"
    ).encode("latin-1")
    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        b"5 0 obj << /Length " + str(len(content)).encode() + b" >> stream\n" + content + b"\nendstream\nendobj\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for obj in objects:
        offsets.append(len(out))
        out += obj
    xref_pos = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        b"trailer << /Size " + str(len(objects) + 1).encode()
        + b" /Root 1 0 R >>\nstartxref\n" + str(xref_pos).encode() + b"\n%%EOF\n"
    )
    return bytes(out)


@pytest.fixture
async def api_env():
    engine = create_async_engine("sqlite+aiosqlite:///./test_api.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        org = Organization(name="API")
        session.add(org)
        await session.flush()
        session.add(
            User(
                organization_id=org.id,
                email="admin@operator.demo",
                name="Admin",
                password_hash=hash_password("operator123"),
                role="admin",
            )
        )
        await session.commit()
    yield maker
    await engine.dispose()


@pytest.fixture
async def client(api_env):
    async def override_get_session():
        async with api_env() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _token(client) -> str:
    r = await client.post(
        "/api/v1/auth/login", json={"email": "admin@operator.demo", "password": "operator123"}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_upload_extract_execute_flow(api_env, client):
    maker = api_env
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/operations", headers=headers, files={"file": ("pedido.pdf", _minimal_pdf(), "application/pdf")}
    )
    assert r.status_code == 202, r.text
    op = r.json()
    assert op["status"] == "processing"

    from app.jobs import process_operation

    await process_operation(op["id"], session_maker=maker)
    async with maker() as session:
        row = await session.get(Operation, op["id"])
        await session.refresh(row)
        assert row.items, "itens nÃ£o extraÃ­dos"
        assert len(row.items) == 2
        assert row.items[0].customer_code == "CIM-1"
        assert row.reference == "PC-2026-100"
        assert row.status in {OperationStatus.READY, OperationStatus.REVIEW}

    r = await client.get("/api/v1/operations", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert len(data[0]["items"]) == 2


@pytest.mark.asyncio
async def test_execute_requires_matched_items(api_env, client):
    maker = api_env
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    async with maker() as session:
        org = await session.scalar(select(Organization))
        op = Operation(
            organization_id=org.id,
            reference="PC-X",
            filename="x.pdf",
            total=100.0,
            confidence=90,
            status=OperationStatus.READY,
        )
        session.add(op)
        await session.commit()
        op_id = op.id

    r = await client.post(
        f"/api/v1/operations/{op_id}/execute",
        headers={**headers, "Idempotency-Key": "exec-1"},
    )
    assert r.status_code == 200, r.text
    first = r.json()
    assert first["external_id"].startswith("DEMO-")

    r = await client.post(
        f"/api/v1/operations/{op_id}/execute",
        headers={**headers, "Idempotency-Key": "exec-1"},
    )
    assert r.status_code == 200
    assert r.json()["external_id"] == first["external_id"]


@pytest.mark.asyncio
async def test_rbac_blocks_operator_from_mappings(api_env, client):
    maker = api_env
    async with maker() as session:
        org = await session.scalar(select(Organization))
        session.add(
            User(
                organization_id=org.id,
                email="operator@operator.demo",
                name="Operador",
                password_hash=hash_password("operator123"),
                role="operator",
            )
        )
        await session.commit()

    r = await client.post(
        "/api/v1/auth/login", json={"email": "operator@operator.demo", "password": "operator123"}
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/mappings",
        headers=headers,
        json={"customer_code": "X-1", "description": "Produto X", "erp_code": "ERP-X"},
    )
    assert r.status_code == 403

    async with maker() as session:
        org = await session.scalar(select(Organization))
        op = Operation(
            organization_id=org.id,
            reference="PC-R",
            filename="r.pdf",
            supplier="ACME",
            total=10.0,
            confidence=90,
            status=OperationStatus.REVIEW,
        )
        session.add(op)
        await session.commit()
        op_id = op.id

    r = await client.patch(
        f"/api/v1/operations/{op_id}", headers=headers, json={"supplier": "ACME LTDA"}
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_export_csv_endpoint(api_env, client):
    maker = api_env
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    async with maker() as session:
        org = await session.scalar(select(Organization))
        op = Operation(
            organization_id=org.id,
            reference="PC-CSV",
            filename="c.pdf",
            supplier="ACME",
            total=100.0,
            confidence=90,
            status=OperationStatus.READY,
        )
        session.add(op)
        await session.commit()
        op_id = op.id

    r = await client.get(f"/api/v1/operations/{op_id}/export?format=csv", headers=headers)
    assert r.status_code == 200
    assert "PC-CSV" in r.text

    r = await client.get(f"/api/v1/operations/{op_id}/export?format=xml", headers=headers)
    assert r.status_code == 200
    assert "sales_order.create" in r.text


@pytest.mark.asyncio
async def test_register_creates_account_and_token(api_env, client):
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "name": "Novo Usuário",
            "email": "novo@empresa.com",
            "password": "senha123",
            "organization": "Empresa Nova",
        },
    )
    assert r.status_code == 201, r.text
    assert "access_token" in r.json()

    r2 = await client.post(
        "/api/v1/auth/register",
        json={"name": "Duplicado", "email": "novo@empresa.com", "password": "senha123"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_approval_flow(api_env, client):
    maker = api_env
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    async with maker() as session:
        org = await session.scalar(select(Organization))
        org.settings = {"approval_threshold": 1000.0}
        op = Operation(
            organization_id=org.id,
            reference="PC-APR",
            filename="a.pdf",
            total=5000.0,
            confidence=90,
            status=OperationStatus.PENDING_APPROVAL,
        )
        session.add(op)
        await session.commit()
        op_id = op.id

    r = await client.post(f"/api/v1/operations/{op_id}/approve", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "ready"

    r = await client.post(
        f"/api/v1/operations/{op_id}/execute",
        headers={**headers, "Idempotency-Key": "apr-1"},
    )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_reject_moves_to_review(api_env, client):
    maker = api_env
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    async with maker() as session:
        org = await session.scalar(select(Organization))
        op = Operation(
            organization_id=org.id,
            reference="PC-REJ",
            filename="r.pdf",
            total=9000.0,
            confidence=90,
            status=OperationStatus.PENDING_APPROVAL,
        )
        session.add(op)
        await session.commit()
        op_id = op.id

    r = await client.post(f"/api/v1/operations/{op_id}/reject", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "review"
    assert any("Aprovação" in i for i in r.json()["issues"])


@pytest.mark.asyncio
async def test_org_settings_patch(api_env, client):
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/v1/organization/settings", headers=headers)
    assert r.status_code == 200
    assert r.json()["approval_threshold"] > 0

    r = await client.patch(
        "/api/v1/organization/settings", headers=headers, json={"approval_threshold": 2500.0}
    )
    assert r.status_code == 200
    assert r.json()["approval_threshold"] == 2500.0


@pytest.mark.asyncio
async def test_patch_operation_and_customer(api_env, client):
    maker = api_env
    token = await _token(client)
    headers = {"Authorization": f"Bearer {token}"}

    async with maker() as session:
        org = await session.scalar(select(Organization))
        op = Operation(
            organization_id=org.id,
            reference="PC-Y",
            filename="y.pdf",
            supplier="Antiga",
            total=0.0,
            confidence=60,
            status=OperationStatus.REVIEW,
        )
        session.add(op)
        await session.commit()
        op_id = op.id

    r = await client.patch(
        f"/api/v1/operations/{op_id}",
        headers=headers,
        json={"supplier": "Construtora Alfa", "tax_id": "11.222.333/0001-81"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["supplier"] == "Construtora Alfa"

    r = await client.get("/api/v1/customers", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Construtora Alfa"

    cid = r.json()[0]["id"]
    r = await client.patch(
        f"/api/v1/customers/{cid}", headers=headers, json={"erp_id": "CLI-9382"}
    )
    assert r.status_code == 200
    assert r.json()["erp_id"] == "CLI-9382"
