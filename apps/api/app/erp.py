from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.config import get_settings
from app.export import operation_to_csv
from app.models import Operation


class ExecutionError(Exception):
    pass


class ManualExecutionError(ExecutionError):
    pass


class ERPAdapter(ABC):
    name: str = "erp"

    @abstractmethod
    async def create_sales_order(self, operation: Operation, idempotency_key: str) -> dict: ...

    @abstractmethod
    async def verify_order(self, external_id: str) -> dict:
        """Confere o pedido no ERP depois de criado (conferência posterior)."""

    @abstractmethod
    async def health_check(self) -> bool: ...


class DemoERPAdapter(ERPAdapter):
    name = "demo"

    async def create_sales_order(self, operation: Operation, idempotency_key: str) -> dict:
        return {
            "external_id": f"DEMO-{operation.reference}",
            "status": "completed",
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": idempotency_key,
        }

    async def verify_order(self, external_id: str) -> dict:
        return {"found": True, "status": "ok"}

    async def health_check(self) -> bool:
        return True


class CSVExportAdapter(ERPAdapter):
    """Fallback: gera o arquivo CSV do pedido para importação manual no ERP."""

    name = "csv"

    async def create_sales_order(self, operation: Operation, idempotency_key: str) -> dict:
        content = operation_to_csv(operation).encode("utf-8")
        from app.storage import ObjectStorage

        try:
            key = f"{operation.organization_id}/{operation.id}/export-{operation.reference}.csv"
            await ObjectStorage().put(key, content, "text/csv")
            storage = key
        except Exception:
            storage = "local"
        return {
            "external_id": f"{operation.reference}-CSV",
            "status": "exported",
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": idempotency_key,
            "storage": storage,
        }

    async def verify_order(self, external_id: str) -> dict:
        return {"found": True, "status": "exported"}

    async def health_check(self) -> bool:
        return True


class ManualAdapter(ERPAdapter):
    """Execução exige operador humano (exporta e bloqueia automação)."""

    name = "manual"

    async def create_sales_order(self, operation: Operation, idempotency_key: str) -> dict:
        raise ManualExecutionError("Execução manual: exporte o pedido e cadastre no ERP")

    async def verify_order(self, external_id: str) -> dict:
        return {"found": False, "status": "manual"}

    async def health_check(self) -> bool:
        return False


STRATEGIES: dict[str, type[ERPAdapter]] = {
    "demo": DemoERPAdapter,
    "csv": CSVExportAdapter,
    "manual": ManualAdapter,
}


def register_http_adapter() -> None:
    from app.erp_http import HttpERPAdapter

    STRATEGIES["http"] = HttpERPAdapter


register_http_adapter()


async def execute_with_fallback(operation: Operation, idempotency_key: str) -> tuple[dict, str, str | None]:
    """Executa no adaptador primário; em falha, cai para CSV; em tudo, manual.

    Retorna (resultado, estrategia_usada, estrategia_anterior_que_falhou).
    """
    mode = get_settings().erp_mode
    primary = STRATEGIES.get(mode, DemoERPAdapter)
    fallback = CSVExportAdapter
    last_strategy = None
    try:
        return await primary().create_sales_order(operation, idempotency_key), primary.name, None
    except ManualExecutionError as exc:
        raise ManualExecutionError(str(exc)) from exc
    except Exception:
        last_strategy = primary.name
    try:
        result = await fallback().create_sales_order(operation, idempotency_key)
        return result, fallback.name, last_strategy
    except Exception as exc:
        raise ExecutionError(f"Nenhuma estratégia conseguiu executar: {exc}") from exc


def get_erp_adapter() -> ERPAdapter:
    mode = get_settings().erp_mode
    return STRATEGIES.get(mode, DemoERPAdapter)()