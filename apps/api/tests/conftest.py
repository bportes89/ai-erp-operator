import os
import pytest

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_operator.db"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["STORAGE_ENABLED"] = "false"

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base, Organization, User
from app.security import hash_password


@pytest.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///./test_operator.db")
    yield engine
    await engine.dispose()


@pytest.fixture
def session_maker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def session(session_maker, engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with session_maker() as session:
        yield session


@pytest.fixture
async def org(session):
    org = Organization(name="Teste")
    session.add(org)
    await session.flush()
    return org


@pytest.fixture
async def user(session, org):
    user = User(
        organization_id=org.id,
        email="tester@operator.demo",
        name="Tester",
        password_hash=hash_password("operator123"),
        role="admin",
    )
    session.add(user)
    await session.commit()
    return user