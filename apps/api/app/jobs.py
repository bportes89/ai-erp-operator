import json

import redis.asyncio as aioredis

from app.audit import record_event
from app.config import get_settings
from app.database import SessionLocal
from app.models import Operation, OperationItem, OperationStatus
from app.extraction_llm import extract_text
from app.validation import validate_extraction
from app.matching import apply_matches
from app.webhooks import fire_webhooks


async def enqueue(operation_id: str) -> bool:
    try:
        redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        await redis.rpush("operator:jobs", json.dumps({"operation_id": operation_id}))
        await redis.aclose()
        return True
    except Exception:
        return False


async def dispatch(operation_id: str) -> None:
    """Enfileira no Redis ou, se indisponível, processa em background."""
    try:
        if not await enqueue(operation_id):
            await process_operation(operation_id)
    except Exception:
        await process_operation(operation_id)


async def process_operation(operation_id: str, session_maker=None) -> None:
    session_maker = session_maker or SessionLocal
    async with session_maker() as session:
        op = await session.get(Operation, operation_id)
        if not op:
            return
        op.status = OperationStatus.PROCESSING
        await session.commit()
        try:
            content = op.raw_content or b""
            result = extract_text(content)
            issues = validate_extraction(result)
            op.reference = result.fields.get("reference") or op.reference or f"PENDING-{operation_id[:8].upper()}"
            op.supplier = result.fields.get("supplier") or op.supplier
            op.tax_id = result.fields.get("tax_id") or op.tax_id
            op.due_date = result.fields.get("due_date") or op.due_date
            op.cost_center = result.fields.get("cost_center") or op.cost_center
            op.total = result.fields.get("total", 0)
            op.confidence = result.confidence
            op.raw_extraction = result.fields
            op.issues = issues
            op.items = [
                OperationItem(operation_id=op.id, **item)
                for item in result.items
            ]
            await apply_matches(session, op)
            op.status = (
                OperationStatus.REVIEW
                if (op.confidence < 85 or issues)
                else OperationStatus.READY
            )
            await record_event(
                session,
                op.organization_id,
                "operation.extracted",
                {"confidence": op.confidence, "items": len(op.items), "issues": issues},
                op.id,
                actor_id=None,
            )
            await session.commit()
            if op.status == OperationStatus.READY:
                fire_webhooks(
                    session,
                    op.organization_id,
                    "operation.ready",
                    {
                        "operation_id": op.id,
                        "reference": op.reference,
                        "status": op.status.value,
                        "confidence": op.confidence,
                        "items": len(op.items),
                    },
                )
        except Exception:
            await session.rollback()
            op.status = OperationStatus.FAILED
            await session.commit()
            raise
