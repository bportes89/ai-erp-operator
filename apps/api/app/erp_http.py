import json
import time
from datetime import datetime, timezone

import httpx

from app.config import get_settings
from app.erp import ERPAdapter, ExecutionError
from app.models import Operation


class HttpERPAdapter(ERPAdapter):
    """Conector HTTP genérico e configurável por env.

    Funciona com qualquer ERP que exponha uma API REST de criação de pedidos.
    O payload é um template JSON com placeholders (ex.: {reference}, {total}, {items});
    a resposta é lida por caminho (ex.: "data.id") para extrair o external_id.
    """

    name = "http"

    def __init__(self, transport=None):
        self._transport = transport

    def _settings(self):
        s = get_settings()
        return s, s.erp_http_payload or ""

    def _headers(self):
        s = get_settings()
        headers = {}
        if s.erp_http_token:
            header = s.erp_http_auth_header or "Authorization"
            if s.erp_http_auth_scheme:
                headers[header] = f"{s.erp_http_auth_scheme} {s.erp_http_token}"
            else:
                headers[header] = s.erp_http_token
        return headers

    def _render_payload(self, template: str, op: Operation, key: str) -> dict:
        s = get_settings()
        item_fields: dict = {}
        try:
            item_fields = json.loads(s.erp_http_item_fields or "{}")
        except json.JSONDecodeError:
            item_fields = {}
        items = []
        for item in op.items:
            row = {
                "customer_code": item.customer_code,
                "erp_code": item.erp_code,
                "description": item.description,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "total": float(item.total),
            }
            if item_fields:
                row = {item_fields.get(k, k): v for k, v in row.items()}
            items.append(row)
        values = {
            "reference": op.reference or "",
            "supplier": op.supplier or "",
            "tax_id": op.tax_id or "",
            "due_date": op.due_date or "",
            "cost_center": op.cost_center or "",
            "total": float(op.total),
            "idempotency_key": key,
        }
        text = template
        for k, v in values.items():
            token = "{" + k + "}"
            if token in text:
                text = text.replace(token, json.dumps(v, ensure_ascii=False) if isinstance(v, str) else str(v))
        text = text.replace("{items}", json.dumps(items, ensure_ascii=False))
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ExecutionError(f"ERP_HTTP_PAYLOAD inválido após renderização: {exc}") from exc

    @staticmethod
    def _dig(data, path: str):
        if not path:
            return None
        current = data
        for part in path.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _client(self, timeout: int) -> httpx.AsyncClient:
        if self._transport is not None:
            return httpx.AsyncClient(timeout=timeout, transport=self._transport)
        return httpx.AsyncClient(timeout=timeout)

    async def create_sales_order(self, operation: Operation, idempotency_key: str) -> dict:
        s, template = self._settings()
        base = (s.erp_http_base_url or "").rstrip("/")
        if not base:
            raise ExecutionError("ERP_HTTP_BASE_URL não configurada")
        payload = self._render_payload(template, operation, idempotency_key)
        headers = self._headers()
        headers["Idempotency-Key"] = idempotency_key
        url = base + s.erp_http_create_path
        last_error: ExecutionError | None = None
        for attempt in range(1 + s.erp_http_retries):
            try:
                async with self._client(s.erp_http_timeout) as client:
                    response = await client.post(url, json=payload, headers=headers)
                if response.status_code < 400:
                    body = response.json() if response.content else {}
                    external = self._dig(body, s.erp_http_external_id_path)
                    if not external:
                        raise ExecutionError(
                            f"Resposta sem external_id (path '{s.erp_http_external_id_path}')"
                        )
                    return {
                        "external_id": str(external),
                        "status": "completed",
                        "executed_at": datetime.now(timezone.utc).isoformat(),
                        "idempotency_key": idempotency_key,
                        "response": body,
                    }
                if response.status_code == 409:
                    body = response.json() if response.content else {}
                    external = self._dig(body, s.erp_http_external_id_path)
                    if external:
                        return {
                            "external_id": str(external),
                            "status": "already_exists",
                            "executed_at": datetime.now(timezone.utc).isoformat(),
                            "idempotency_key": idempotency_key,
                            "response": body,
                        }
                    raise ExecutionError(f"ERP HTTP 409 sem external_id: {response.text[:200]}")
                last_error = ExecutionError(f"ERP HTTP {response.status_code}: {response.text[:200]}")
            except ExecutionError:
                raise
            except httpx.HTTPError as exc:
                last_error = ExecutionError(f"ERP HTTP erro de conexão: {exc}")
            if attempt > 0:
                time.sleep(0.2 * attempt)
        raise last_error or ExecutionError("Falha desconhecida no conector HTTP")

    async def verify_order(self, external_id: str) -> dict:
        s = get_settings()
        base = (s.erp_http_base_url or "").rstrip("/")
        if not base:
            return {"found": False, "status": "not_configured"}
        path = (s.erp_http_verify_path or "/orders/{external_id}").replace("{external_id}", external_id)
        headers = self._headers()
        try:
            async with self._client(s.erp_http_timeout) as client:
                response = await client.get(base + path, headers=headers)
            if response.status_code >= 400:
                return {"found": False, "status": "not_found", "http": response.status_code}
            body = response.json() if response.content else {}
            return {
                "found": True,
                "status": self._dig(body, "status") or "ok",
                "http": response.status_code,
                "response": body,
            }
        except httpx.HTTPError as exc:
            return {"found": False, "status": "error", "error": str(exc)}

    async def health_check(self) -> bool:
        s = get_settings()
        base = (s.erp_http_base_url or "").rstrip("/")
        if not base:
            return False
        try:
            async with self._client(s.erp_http_timeout) as client:
                response = await client.get(base + "/health", headers=self._headers())
            return response.status_code < 400
        except httpx.HTTPError:
            return False