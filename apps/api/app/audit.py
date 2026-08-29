import hashlib
import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AuditEvent


async def record_event(
    session: AsyncSession,
    organization_id: str,
    event_type: str,
    payload: dict,
    operation_id: str | None = None,
    actor_id: str | None = None,
) -> AuditEvent:
    last = await session.scalar(
        select(AuditEvent)
        .where(AuditEvent.organization_id == organization_id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(1)
    )
    previous = last.hash if last else None
    canonical = json.dumps(
        {"event": event_type, "operation": operation_id, "payload": payload, "previous": previous},
        sort_keys=True,
        ensure_ascii=True,
    )
    event = AuditEvent(
        organization_id=organization_id,
        operation_id=operation_id,
        actor_id=actor_id,
        event_type=event_type,
        payload=payload,
        previous_hash=previous,
        hash=hashlib.sha256(canonical.encode()).hexdigest(),
    )
    session.add(event)
    return event
