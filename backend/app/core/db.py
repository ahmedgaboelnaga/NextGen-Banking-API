from typing import AsyncGenerator, Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from backend.app.core.config import settings
from backend.app.core.logging import get_logger


logger = get_logger()

engine = create_async_engine(settings.DATABASE_URL)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"An error occurred while getting the database session: {e}")
            await session.rollback()
        finally:
            await session.close()


SesssionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def init_db() -> None:
    pass
