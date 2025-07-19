"""Database connection and session management."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.settings import Settings, get_settings

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize database.

        Args:
            settings: Application settings
        """
        self.settings = settings or get_settings()
        
        # Create engine
        self.engine: AsyncEngine = create_async_engine(
            self.settings.database_url,
            echo=self.settings.database_echo,
            pool_size=self.settings.database_pool_size,
            max_overflow=self.settings.database_max_overflow,
            pool_pre_ping=True
        )
        
        # Create session factory
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("Database initialized")

    async def create_tables(self) -> None:
        """Create all tables."""
        from src.models.db import Base
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("Database tables created")

    async def drop_tables(self) -> None:
        """Drop all tables."""
        from src.models.db import Base
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        logger.warning("Database tables dropped")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session.

        Yields:
            Database session
        """
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self) -> None:
        """Close database connection."""
        await self.engine.dispose()
        logger.info("Database connection closed")


# Global database instance
_database: Database | None = None


def get_database() -> Database:
    """Get database instance.

    Returns:
        Database instance
    """
    global _database
    if _database is None:
        _database = Database()
    return _database