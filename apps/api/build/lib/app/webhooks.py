import asyncio
import hashlib
import hmac
import json

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Webhook, WebhookDelivery


def sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def _deliver(webhook_id: str, event: str, payload: dict) -> None:
    from app.database import SessionLocal

    async with SessionLocal() as session:
        webhook = await session.get(Webhook, webhook_id)
        if not webhook or not webhook.active:
            return
        body = json.dumps(payload, ensure_ascii=True).encode()
        signature = sign_payload(body, webhook.secret)
        headers = {
            "Content-Type": "application/json",
            "X-Signature": signature,
            "X-Event": event,
        }
        delivery = WebhookDelivery(
            webhook_id=webhook.id, event=event, payload=payload, status="pending"
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)
        status = "failed"
        async with httpx.AsyncClient(timeout=10) as client:
            for attempt in (1, 2):
                try:
                    response = await client.post(webhook.url, data=body, headers=headers)
                    if response.status_code < 400:
                        status = "delivered"
                        break
                except httpx.HTTPError:
                    pass
        delivery.status = status
        delivery.attempts = 2
        await session.commit()


def fire_webhooks(
    session: AsyncSession, organization_id: str, event: str, payload: dict
) -> None:
    """Dispara webhooks da organização sem bloquear o fluxo."""
    from app.database import SessionLocal

    async def _collect():
        async with SessionLocal() as s:
            rows = await s.scalars(
                select(Webhook).where(
                    Webhook.organization_id == organization_id,
                    Webhook.active.is_(True),
                )
            )
            return [w for w in rows if not w.events or event in w.events]

    async def _run():
        webhooks = await _collect()
        for webhook in webhooks:
            asyncio.create_task(_deliver(webhook.id, event, payload))

    asyncio.create_task(_run())