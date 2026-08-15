"""Core Service — SQLAlchemy async engine and session factory."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.get_database_url(),
    echo=settings.DEBUG,
    future=True,
    pool_size=getattr(settings, "DB_POOL_SIZE", 20),
    max_overflow=getattr(settings, "DB_MAX_OVERFLOW", 10),
    pool_timeout=getattr(settings, "DB_POOL_TIMEOUT", 30),
    pool_recycle=getattr(settings, "DB_POOL_RECYCLE", 1800),
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
