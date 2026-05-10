from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from core.config import get_settings

settings = get_settings()
is_sqlite = settings.async_db_uri.startswith("sqlite+aiosqlite://")

engine_kwargs = {"echo": False}
if not is_sqlite:
    engine_kwargs.update(
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
        pool_size=5,
        max_overflow=10,
    )

engine = create_async_engine(settings.async_db_uri, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
