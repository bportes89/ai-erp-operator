import httpx
import pytest
from types import SimpleNamespace

from app.erp import execute_with_fallback
from app.erp_http import HttpERPAdapter
from app.fake_erp import app as fake_app
from app.fake_erp import reset


def _settings(**kw):
    base = {
        "erp_http_base_url": "http://fake",
        "erp_http_token": "token-teste",
        "erp_http_auth_header": "Authorization",
        "erp_http_auth_scheme": "Bearer",
        "erp_http_create_path": "/orders",
        "erp_http_verify_path": "/orders/{external_id}",
        "erp_http_payload": (
            '{"reference":{reference},"total":{total},'
            '"idempotency_key":{idempotency_key},"items":{items}}'
        ),
        "erp_http_item_fields": "{}",
        "erp_http_external_id_path": "id",
        "erp_http_timeout": 5,
        "erp_http_retries": 1,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def _op():
    return SimpleNamespace(
        reference="PC-1",
        supplier="ACME",
        tax_id="11.222.333/0001-81",
        due_date=None,
        cost_center=None,
        total=100.0,
        status=SimpleNamespace(value="ready"),
        items=[
            SimpleNamespace(
                customer_code="A-1",
                erp_code="ERP-A1",
                description="Produto A",
                quantity=2,
                unit_price=50.0,
                total=100.0,
            )
        ],
    )


@pytest.fixture
def adapter(monkeypatch):
    reset()
    config = _config_dict()
    return HttpERPAdapter(config=config, transport=httpx.ASGITransport(app=fake_app))


def _config_dict(**overrides):
    base = _settings()
    config = {
        "erp_http_base_url": base.erp_http_base_url,
        "erp_http_token": base.erp_http_token,
        "erp_http_auth_header": base.erp_http_auth_header,
        "erp_http_auth_scheme": base.erp_http_auth_scheme,
        "erp_http_create_path": base.erp_http_create_path,
        "erp_http_verify_path": base.erp_http_verify_path,
        "erp_http_payload": base.erp_http_payload,
        "erp_http_item_fields": base.erp_http_item_fields,
        "erp_http_external_id_path": base.erp_http_external_id_path,
        "erp_http_timeout": base.erp_http_timeout,
        "erp_http_retries": base.erp_http_retries,
    }
    config.update(overrides)
    return config


@pytest.mark.asyncio
async def test_http_create_and_verify(adapter):
    result = await adapter.create_sales_order(_op(), "key-1")
    assert result["external_id"]
    assert result["status"] == "completed"

    verification = await adapter.verify_order(result["external_id"])
    assert verification["found"] is True
    assert verification["status"] == "created"


@pytest.mark.asyncio
async def test_http_idempotent_same_key(adapter):
    first = await adapter.create_sales_order(_op(), "key-replay")
    second = await adapter.create_sales_order(_op(), "key-replay")
    assert first["external_id"] == second["external_id"]
    assert second["status"] == "already_exists"


@pytest.mark.asyncio
async def test_http_item_fields_mapping():
    reset()
    config = _config_dict(erp_http_item_fields='{"customer_code":"sku","quantity":"qtd"}')
    adapter = HttpERPAdapter(config=config, transport=httpx.ASGITransport(app=fake_app))
    result = await adapter.create_sales_order(_op(), "key-map")
    assert result["external_id"]
    sent = result["response"]
    assert sent["items"][0]["sku"] == "A-1"
    assert sent["items"][0]["qtd"] == 2


@pytest.mark.asyncio
async def test_fallback_to_csv_when_http_fails(monkeypatch):
    reset()
    settings = _settings(erp_http_base_url="http://nohost.invalid")
    monkeypatch.setattr("app.erp.get_settings", lambda: SimpleNamespace(erp_mode="http"))
    monkeypatch.setattr("app.erp_http.get_settings", lambda: settings)
    result, strategy, failed = await execute_with_fallback(_op(), "key-fallback")
    assert strategy == "csv"
    assert failed == "http"
    assert result["status"] == "exported"


@pytest.mark.asyncio
async def test_injected_adapter_is_primary(monkeypatch):
    reset()
    adapter = HttpERPAdapter(
        config=_config_dict(),
        transport=httpx.ASGITransport(app=fake_app),
    )
    result, strategy, failed = await execute_with_fallback(_op(), "key-inj", adapter=adapter)
    assert strategy == "http"
    assert failed is None
    assert result["external_id"]


@pytest.mark.asyncio
async def test_http_fake_erp_failure_raises_then_fallback(monkeypatch):
    reset()
    settings = _settings(erp_http_base_url="http://nohost.invalid")
    monkeypatch.setattr("app.erp.get_settings", lambda: SimpleNamespace(erp_mode="http"))
    monkeypatch.setattr("app.erp_http.get_settings", lambda: settings)
    result, strategy, failed = await execute_with_fallback(_op(), "key-fail")
    assert strategy == "csv"