import pytest
from types import SimpleNamespace

from app.erp import (
    CSVExportAdapter,
    DemoERPAdapter,
    ExecutionError,
    ManualAdapter,
    ManualExecutionError,
    execute_with_fallback,
)


def _op():
    return SimpleNamespace(
        id="op-1",
        organization_id="org-1",
        reference="PC-42",
        filename="p.pdf",
        supplier="ACME",
        tax_id="11.222.333/0001-81",
        due_date="30/11/2026",
        cost_center="FILIAL-MG",
        total=1497.0,
        status=SimpleNamespace(value="ready"),
        items=[],
    )


@pytest.mark.asyncio
async def test_demo_erp_is_idempotency_aware():
    result = await DemoERPAdapter().create_sales_order(_op(), "key-42")
    assert result["external_id"] == "DEMO-PC-42"
    assert result["idempotency_key"] == "key-42"


@pytest.mark.asyncio
async def test_csv_adapter_returns_exported():
    result = await CSVExportAdapter().create_sales_order(_op(), "key-42")
    assert result["external_id"] == "PC-42-CSV"
    assert result["status"] == "exported"


@pytest.mark.asyncio
async def test_manual_adapter_raises():
    with pytest.raises(ManualExecutionError):
        await ManualAdapter().create_sales_order(_op(), "key")


@pytest.mark.asyncio
async def test_execute_fallback_to_csv(monkeypatch):
    async def boom(self, operation, idempotency_key):
        raise RuntimeError("ERP fora do ar")

    monkeypatch.setattr(DemoERPAdapter, "create_sales_order", boom)
    monkeypatch.setattr("app.erp.get_settings", lambda: SimpleNamespace(erp_mode="demo"))
    result, strategy, failed = await execute_with_fallback(_op(), "key-42")
    assert strategy == "csv"
    assert failed == "demo"
    assert result["status"] == "exported"


@pytest.mark.asyncio
async def test_execute_all_strategies_fail(monkeypatch):
    async def boom(self, operation, idempotency_key):
        raise RuntimeError("falha total")

    monkeypatch.setattr(DemoERPAdapter, "create_sales_order", boom)
    monkeypatch.setattr(CSVExportAdapter, "create_sales_order", boom)
    monkeypatch.setattr("app.erp.get_settings", lambda: SimpleNamespace(erp_mode="demo"))
    with pytest.raises(ExecutionError):
        await execute_with_fallback(_op(), "key")