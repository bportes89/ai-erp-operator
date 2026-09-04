import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="FakeERP")

_store: dict[str, dict] = {}
_by_id: dict[str, dict] = {}
_fail_next: int = 0


class OrderIn(BaseModel):
    reference: str = ""
    supplier: str = ""
    tax_id: str = ""
    due_date: str = ""
    cost_center: str = ""
    total: float = 0.0
    idempotency_key: str = ""
    items: list = []


@app.post("/orders")
async def create_order(body: OrderIn):
    global _fail_next
    if _fail_next > 0:
        _fail_next -= 1
        raise HTTPException(503, "indisponível (falha injetada)")
    key = body.idempotency_key
    if key and key in _store:
        return JSONResponse(_store[key], status_code=409)
    order_id = str(uuid.uuid4())
    order = {
        **body.model_dump(),
        "id": order_id,
        "status": "created",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if key:
        _store[key] = order
    _by_id[order_id] = order
    return JSONResponse(order, status_code=201)


@app.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = _by_id.get(order_id)
    if not order:
        raise HTTPException(404, "pedido não encontrado")
    return order


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/__fail")
async def set_fail(payload: dict):
    global _fail_next
    _fail_next = int(payload.get("count", 1))
    return {"fail_next": _fail_next}


def reset():
    global _store, _by_id, _fail_next
    _store = {}
    _by_id = {}
    _fail_next = 0