import asyncio
from typing import AsyncGenerator, Annotated

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool


from backend.app.core.config import settings
from backend.app.core.logging import get_logger


logger = get_logger()

engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

async_session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    session = async_session_factory()
    try:
        yield session
    except Exception as e:
        logger.error(f"An error occurred while getting the database session: {e}")
        if session:
            try:
                await session.rollback()
                logger.info("Database session rolled back session after error")
            except Exception as rollback_error:
                logger.error(
                    f"An error occurred while rolling back the database session: {rollback_error}"
                )
        raise
    finally:
        if session:
            try:
                await session.close()
                logger.debug("Database session closed successfully")
            except Exception as close_error:
                logger.error(
                    f"An error occurred while closing the database session: {close_error}"
                )


SessionDep = Annotated[AsyncSession, Depends(get_async_session)]


async def init_db() -> None:
    try:
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                logger.info("Database connection verified successfully")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(
                        f"Database connection failed after {max_retries} attempts: {e}"
                    )
                    raise
                logger.warning(
                    f"Database connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds..."
                )
                await asyncio.sleep((attempt + 1) * retry_delay)
    except Exception as e:
        logger.error(f"An error occurred during database initialization: {e}")
        raise
