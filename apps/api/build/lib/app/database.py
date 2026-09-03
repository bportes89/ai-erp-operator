from collections.abc import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import get_settings


def _normalize_database_url(url: str) -> str:
    """Ajusta URLs de bancos gerenciados (ex.: Neon pooled) para o asyncpg."""
    if not url.startswith("postgresql"):
        return url, {}
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query))
    query.pop("channel_binding", None)
    connect_args: dict = {}
    sslmode = query.pop("sslmode", None)
    if sslmode == "require":
        connect_args["ssl"] = "require"
    elif sslmode == "disable":
        connect_args["ssl"] = False
    if "-pooler." in (parsed.hostname or "") or "pooler" in (parsed.hostname or ""):
        connect_args["prepared_statement_cache_size"] = 0
    normalized = urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
    return normalized, connect_args


_database_url, _connect_args = _normalize_database_url(get_settings().database_url)

engine = create_async_engine(
    _database_url,
    pool_pre_ping=True,
    **(dict(connect_args=_connect_args) if _connect_args else {}),
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
