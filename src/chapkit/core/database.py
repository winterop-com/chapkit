"""Async SQLAlchemy database connection manager."""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from alembic.config import Config
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import ConnectionPoolEntry

from alembic import command


def _install_sqlite_connect_pragmas(engine: AsyncEngine) -> None:
    """Install SQLite connection pragmas for performance and reliability."""

    def on_connect(dbapi_conn: sqlite3.Connection, _conn_record: ConnectionPoolEntry) -> None:
        """Configure SQLite pragmas on connection."""
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON;")
        cur.execute("PRAGMA synchronous=NORMAL;")
        cur.execute("PRAGMA busy_timeout=30000;")  # 30s
        cur.execute("PRAGMA temp_store=MEMORY;")
        cur.execute("PRAGMA cache_size=-64000;")  # 64 MiB (negative => KiB)
        cur.execute("PRAGMA mmap_size=134217728;")  # 128 MiB
        cur.close()

    event.listen(engine.sync_engine, "connect", on_connect)


class Database:
    """Async SQLAlchemy database connection manager."""

    def __init__(
        self, url: str, *, echo: bool = False, alembic_dir: Path | None = None, auto_migrate: bool = True
    ) -> None:
        """Initialize database with connection URL."""
        self.url = url
        self.alembic_dir = alembic_dir
        self.auto_migrate = auto_migrate
        self.engine: AsyncEngine = create_async_engine(url, echo=echo, future=True)
        _install_sqlite_connect_pragmas(self.engine)
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init(self) -> None:
        """Initialize database tables and configure SQLite using Alembic migrations."""
        import asyncio

        # Import Base here to avoid circular import at module level
        from chapkit.core.models import Base

        # Set WAL mode first (if not in-memory)
        if ":memory:" not in self.url:
            async with self.engine.begin() as conn:
                await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")

        # For in-memory databases or when migrations are disabled, use direct table creation
        if ":memory:" in self.url or not self.auto_migrate:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        else:
            # For file-based databases, use Alembic migrations
            alembic_cfg = Config()

            # Use custom alembic directory if provided, otherwise use bundled migrations
            if self.alembic_dir is not None:
                alembic_cfg.set_main_option("script_location", str(self.alembic_dir))
            else:
                alembic_cfg.set_main_option(
                    "script_location", str(Path(__file__).parent.parent.parent.parent / "alembic")
                )

            alembic_cfg.set_main_option("sqlalchemy.url", self.url)

            # Run upgrade in executor to avoid event loop conflicts
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, command.upgrade, alembic_cfg, "head")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Create a database session context manager."""
        async with self._session_factory() as s:
            yield s

    async def dispose(self) -> None:
        """Dispose of database engine and connection pool."""
        await self.engine.dispose()
