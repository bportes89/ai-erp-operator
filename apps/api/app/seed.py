import asyncio
from sqlalchemy import select
from app.database import SessionLocal, engine
from app.models import Base, Organization, User
from app.security import hash_password


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        if await session.scalar(select(User).where(User.email == "admin@operator.demo")):
            return
        org = Organization(name="Empresa Demonstração")
        session.add(org)
        await session.flush()
        session.add(
            User(
                organization_id=org.id,
                email="admin@operator.demo",
                name="Administrador",
                password_hash=hash_password("operator123"),
                role="admin",
            )
        )
        await session.commit()
        print("Usuário: admin@operator.demo / operator123")


if __name__ == "__main__":
    asyncio.run(seed())
