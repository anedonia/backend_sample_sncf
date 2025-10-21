import json
from typing import Iterator, Optional, AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import Session, sessionmaker

from opticapa.shared.config.config import settings
from opticapa.shared.utils.logger import logger

_sync_sessionmaker = None
_async_sessionmaker = None


def get_async_engine(echo: bool = settings.show_logs_db_stmt) -> AsyncEngine:
    return create_async_engine(
        url=f"postgresql+asyncpg://{settings.db_url}",
        json_serializer=json.dumps,
        json_deserializer=json.loads,
        echo=echo,
        connect_args={
            "server_settings": {"statement_timeout": f"{settings.db_statement_timeout}"}
        },
    )


def get_sync_engine(echo: bool = settings.show_logs_db_stmt) -> Engine:
    return create_engine(
        f"postgresql+psycopg2://{settings.db_url}",
        json_serializer=json.dumps,
        json_deserializer=json.loads,
        echo=echo,
        connect_args={
            "options": f"-c statement_timeout={settings.db_statement_timeout}"
        },
    )


def get_async_sessionmaker():
    global _async_sessionmaker
    if _async_sessionmaker is None:
        _async_sessionmaker = async_sessionmaker(
            autocommit=False,
            autoflush=False,
            class_=AsyncSession,
            bind=get_async_engine(),
        )
    return _async_sessionmaker


def get_sync_sessionmaker():
    global _sync_sessionmaker
    if _sync_sessionmaker is None:
        _sync_sessionmaker = sessionmaker(
            autocommit=False,
            autoflush=False,
            class_=Session,
            bind=get_sync_engine(),
        )
    return _sync_sessionmaker


def set_default_timezone(session: Session, timezone_name: str = settings.timezone_name):
    """
    This statement sets a default timezone in a session
    Args:
        session: DB session
        timezone_name: str: default timezone to set
    """
    session.execute(text(f"""SET TIME ZONE '{timezone_name}';"""))
    timezone = session.execute(text("""SHOW TIME ZONE;""")).fetchone()[0]
    logger.debug(f"Session default timezone set to {timezone}")


async def async_set_default_timezone(
    session: AsyncSession, timezone_name: str = settings.timezone_name
):
    """
    This statement sets a default timezone in a session
    Args:
        session: DB session
        timezone_name: str: default timezone to set
    """
    await session.execute(text(f"""SET TIME ZONE '{timezone_name}';"""))
    timezone = await session.execute(text("""SHOW TIME ZONE;"""))
    logger.debug(f"Session default timezone set to {timezone.fetchone()[0]}")


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async_session = get_async_sessionmaker()
    async with async_session() as session:
        await async_set_default_timezone(session)
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Iterator[Session]:
    sync_session = get_sync_sessionmaker()
    db_session = sync_session()
    set_default_timezone(db_session)
    try:
        yield db_session
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()

