from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as aioredis
from sqlalchemy import text
from app.config import get_settings
from app.database import engine
from app.models import Base
from app.routes import router
from app.storage import _endpoint_reachable


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="AI ERP Operator API", version="0.1.0", lifespan=lifespan)
cors_origins = [origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

_started_at = datetime.now(timezone.utc)


@app.get("/health")
async def health():
    s = get_settings()
    checks: dict[str, str] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "fail"
    try:
        redis = aioredis.from_url(s.redis_url, decode_responses=True)
        await redis.ping()
        await redis.aclose()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "fail"
    if s.storage_enabled:
        checks["storage"] = "ok" if _endpoint_reachable(s.storage_endpoint) else "unreachable"
    else:
        checks["storage"] = "disabled"
    checks["erp_mode"] = s.erp_mode
    checks["llm"] = "off" if s.llm_provider == "none" else s.llm_provider
    status = "ok" if checks.get("database") == "ok" else "degraded"
    return {
        "status": status,
        "service": "ai-erp-operator-api",
        "uptime_seconds": round((datetime.now(timezone.utc) - _started_at).total_seconds()),
        "checks": checks,
    }
