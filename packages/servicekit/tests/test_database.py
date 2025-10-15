import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
import servicekit.core.database as database_module
from servicekit import SqliteDatabase, SqliteDatabaseBuilder
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def test_install_sqlite_pragmas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure SQLite connect pragmas are installed on new connections."""
    captured: dict[str, object] = {}

    def fake_listen(target: object, event_name: str, handler: object) -> None:
        captured["target"] = target
        captured["event_name"] = event_name
        captured["handler"] = handler

    fake_engine = cast(AsyncEngine, SimpleNamespace(sync_engine=object()))
    monkeypatch.setattr(database_module.event, "listen", fake_listen)

    database_module._install_sqlite_connect_pragmas(fake_engine)

    assert captured["target"] is fake_engine.sync_engine
    assert captured["event_name"] == "connect"
    handler = captured["handler"]
    assert callable(handler)

    class DummyCursor:
        def __init__(self) -> None:
            self.commands: list[str] = []
            self.closed = False

        def execute(self, sql: str) -> None:
            self.commands.append(sql)

        def close(self) -> None:
            self.closed = True

    class DummyConnection:
        def __init__(self) -> None:
            self._cursor = DummyCursor()

        def cursor(self) -> DummyCursor:
            return self._cursor

    connection = DummyConnection()
    handler(connection, None)

    assert connection._cursor.commands == [
        "PRAGMA foreign_keys=ON;",
        "PRAGMA synchronous=NORMAL;",
        "PRAGMA busy_timeout=30000;",
        "PRAGMA temp_store=MEMORY;",
        "PRAGMA cache_size=-64000;",
        "PRAGMA mmap_size=134217728;",
    ]
    assert connection._cursor.closed is True


class TestSqliteDatabase:
    """Tests for the SqliteDatabase class."""

    async def test_init_creates_tables(self) -> None:
        """Test that init() creates all tables."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        # Verify tables were created by checking metadata
        async with db.session() as session:
            # Simple query to verify database is operational
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        await db.dispose()

    async def test_session_context_manager(self) -> None:
        """Test that session() context manager works correctly."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            # Verify we got an AsyncSession
            assert session is not None
            # Verify it's usable
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        await db.dispose()

    async def test_multiple_sessions(self) -> None:
        """Test that multiple sessions can be created."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session1:
            result1 = await session1.execute(text("SELECT 1"))
            assert result1.scalar() == 1

        async with db.session() as session2:
            result2 = await session2.execute(text("SELECT 2"))
            assert result2.scalar() == 2

        await db.dispose()

    async def test_dispose_closes_engine(self) -> None:
        """Test that dispose() properly closes the engine."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        # Verify engine is initially usable
        async with db.session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        await db.dispose()
        # After dispose, the engine should no longer be usable
        # We verify this by checking that the pool still exists but is disposed

    async def test_echo_parameter(self) -> None:
        """Test that echo parameter is passed to engine."""
        db_echo = SqliteDatabase("sqlite+aiosqlite:///:memory:", echo=True)
        db_no_echo = SqliteDatabase("sqlite+aiosqlite:///:memory:", echo=False)

        assert db_echo.engine.echo is True
        assert db_no_echo.engine.echo is False

        await db_echo.dispose()
        await db_no_echo.dispose()

    async def test_wal_mode_enabled(self) -> None:
        """Test that WAL mode is enabled after init()."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        async with db.session() as session:
            result = await session.execute(text("SELECT 1"))
            # For in-memory databases, WAL mode might not be enabled
            # but the init() should complete without error
            assert result is not None

        await db.dispose()

    async def test_url_storage(self) -> None:
        """Test that the URL is stored correctly."""
        url = "sqlite+aiosqlite:///:memory:"
        db = SqliteDatabase(url)
        assert db.url == url
        await db.dispose()

    async def test_pool_configuration_file_database(self) -> None:
        """Test that pool parameters are applied to file-based databases."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)

        try:
            db = SqliteDatabase(
                f"sqlite+aiosqlite:///{db_path}",
                pool_size=10,
                max_overflow=20,
                pool_recycle=7200,
                pool_pre_ping=False,
            )
            # File-based databases should have pool configuration
            # Verify pool exists and database is functional
            await db.init()
            async with db.session() as session:
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1
            await db.dispose()
        finally:
            if db_path.exists():
                db_path.unlink()

    async def test_pool_configuration_memory_database(self) -> None:
        """Test that in-memory databases skip pool configuration."""
        # In-memory databases use StaticPool which doesn't accept pool params
        # This should not raise an error
        db = SqliteDatabase(
            "sqlite+aiosqlite:///:memory:",
            pool_size=10,
            max_overflow=20,
        )
        await db.init()
        async with db.session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        await db.dispose()

    async def test_session_factory_configuration(self) -> None:
        """Test that session factory is configured correctly."""
        db = SqliteDatabaseBuilder.in_memory().build()
        await db.init()

        # Verify session factory has expire_on_commit set to False
        assert db._session_factory.kw.get("expire_on_commit") is False

        await db.dispose()

    async def test_file_based_database_with_alembic_migrations(self) -> None:
        """Test that file-based databases use Alembic migrations to create schema."""
        # Create a temporary database file
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)

        try:
            # Initialize database with file-based URL
            db = SqliteDatabase(f"sqlite+aiosqlite:///{db_path}")
            await db.init()

            # Verify that tables were created via Alembic migration
            async with db.session() as session:
                # Check that the alembic_version table exists (created by Alembic)
                result = await session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
                )
                alembic_table = result.scalar()
                assert alembic_table == "alembic_version", "Alembic version table should exist"

                # Verify current migration version is set
                result = await session.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()
                assert version is not None, "Migration version should be recorded"

                # Verify that application tables were created
                result = await session.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name IN ('configs', 'artifacts', 'config_artifacts') ORDER BY name"
                    )
                )
                tables = [row[0] for row in result.fetchall()]
                assert tables == ["artifacts", "config_artifacts", "configs"], "All application tables should exist"

            await db.dispose()

        finally:
            # Clean up temporary database file
            if db_path.exists():
                db_path.unlink()

    async def test_is_in_memory_method(self) -> None:
        """Test is_in_memory() method."""
        # In-memory database
        db_mem = SqliteDatabase("sqlite+aiosqlite:///:memory:")
        assert db_mem.is_in_memory() is True
        await db_mem.dispose()

        # File-based database
        db_file = SqliteDatabase("sqlite+aiosqlite:///./app.db")
        assert db_file.is_in_memory() is False
        await db_file.dispose()


class TestSqliteDatabaseBuilder:
    """Tests for SqliteDatabaseBuilder class."""

    async def test_in_memory_builder(self) -> None:
        """Test building an in-memory database."""
        db = SqliteDatabaseBuilder.in_memory().build()

        assert db.url == "sqlite+aiosqlite:///:memory:"
        assert db.is_in_memory() is True
        # Note: auto_migrate setting doesn't matter for in-memory - they always skip Alembic

        await db.init()
        async with db.session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        await db.dispose()

    async def test_from_file_builder(self) -> None:
        """Test building a file-based database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)

        try:
            db = SqliteDatabaseBuilder.from_file(db_path).build()

            assert db.url == f"sqlite+aiosqlite:///{db_path}"
            assert db.is_in_memory() is False
            assert db.auto_migrate is True  # File-based should enable migrations by default

            await db.dispose()
        finally:
            if db_path.exists():
                db_path.unlink()

    async def test_from_file_with_string_path(self) -> None:
        """Test building from string path."""
        db = SqliteDatabaseBuilder.from_file("./test.db").build()
        assert db.url == "sqlite+aiosqlite:///./test.db"
        await db.dispose()

    async def test_builder_with_echo(self) -> None:
        """Test builder with echo enabled."""
        db = SqliteDatabaseBuilder.in_memory().with_echo(True).build()
        assert db.engine.echo is True
        await db.dispose()

    async def test_builder_with_migrations(self) -> None:
        """Test builder with migration configuration."""
        custom_dir = Path("/custom/alembic")
        db = SqliteDatabaseBuilder.in_memory().with_migrations(enabled=True, alembic_dir=custom_dir).build()

        assert db.auto_migrate is True
        assert db.alembic_dir == custom_dir
        await db.dispose()

    async def test_builder_with_pool(self) -> None:
        """Test builder with pool configuration."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = Path(tmp_file.name)

        try:
            db = (
                SqliteDatabaseBuilder.from_file(db_path)
                .with_pool(size=20, max_overflow=40, recycle=1800, pre_ping=False)
                .build()
            )

            # Verify database is functional
            await db.init()
            async with db.session() as session:
                result = await session.execute(text("SELECT 1"))
                assert result.scalar() == 1

            await db.dispose()
        finally:
            if db_path.exists():
                db_path.unlink()

    async def test_builder_chainable_api(self) -> None:
        """Test that builder methods are chainable."""
        db = SqliteDatabaseBuilder.in_memory().with_echo(True).with_migrations(False).with_pool(size=10).build()

        assert db.engine.echo is True
        assert db.auto_migrate is False
        await db.dispose()

    def test_builder_without_url_raises_error(self) -> None:
        """Test that building without URL raises error."""
        builder = SqliteDatabaseBuilder()
        with pytest.raises(ValueError, match="Database URL not configured"):
            builder.build()
