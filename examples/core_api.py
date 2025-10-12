"""Core-only API example using BaseServiceBuilder with custom User entity."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from ulid import ULID

from chapkit.core import BaseManager, BaseRepository, Entity, EntityIn, EntityOut
from chapkit.core.api import BaseServiceBuilder, CrudRouter, ServiceInfo
from chapkit.core.api.dependencies import get_session


class User(Entity):
    """User entity for authentication and profile management."""

    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)


class UserIn(EntityIn):
    """Input schema for creating and updating users."""

    username: str
    email: str
    full_name: str | None = None
    is_active: bool = True


class UserOut(EntityOut):
    """Output schema for user responses."""

    username: str
    email: str
    full_name: str | None
    is_active: bool


class UserRepository(BaseRepository[User, ULID]):
    """Repository for user data access with custom queries."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user repository with database session."""
        super().__init__(session, User)

    async def find_by_username(self, username: str) -> User | None:
        """Find a user by username."""
        from sqlalchemy import select

        stmt = select(self.model).where(self.model.username == username)
        result = await self.s.execute(stmt)
        return result.scalar_one_or_none()


class UserManager(BaseManager[User, UserIn, UserOut, ULID]):
    """Manager for user business logic with validation."""

    def __init__(self, repo: UserRepository) -> None:
        """Initialize user manager with repository."""
        super().__init__(repo, User, UserOut)
        self.repo: UserRepository = repo

    async def find_by_username(self, username: str) -> UserOut | None:
        """Find a user by username and return output schema."""
        user = await self.repo.find_by_username(username)
        return self._to_output_schema(user) if user else None


def get_user_manager(session: AsyncSession = Depends(get_session)) -> UserManager:
    """Provide user manager instance for dependency injection."""
    return UserManager(UserRepository(session))


user_router = CrudRouter.create(
    prefix="/api/v1/users",
    tags=["users"],
    entity_in_type=UserIn,
    entity_out_type=UserOut,
    manager_factory=get_user_manager,
)


app = (
    BaseServiceBuilder(
        info=ServiceInfo(
            display_name="Core User Service",
            version="1.0.0",
            summary="User management API using core-only features",
            description="Demonstrates BaseServiceBuilder with custom entities, "
            "CRUD operations, health checks, and job scheduling without module dependencies.",
        )
    )
    .with_database()  # Defaults to in-memory SQLite
    .with_health()
    .with_system()
    .with_jobs(max_concurrency=5)
    .with_logging()
    .include_router(user_router)
    .build()
)


if __name__ == "__main__":
    from chapkit.core.api.utilities import run_app

    # Note: Reload is disabled for this example to avoid SQLAlchemy
    # table re-registration issues when defining custom entities.
    # For reload support, use: fastapi dev examples/core_api.py
    run_app(app, reload=False)
