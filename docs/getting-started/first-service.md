# Your First Service

A comprehensive guide to building a complete Chapkit service from scratch.

## What We'll Build

We'll create a **User Management Service** with:

- Custom user entity
- CRUD endpoints
- Health checks
- Background jobs
- Structured logging
- Custom business logic

## Step 1: Define Your Configuration

First, create a configuration schema using `BaseConfig`:

```python
from chapkit import BaseConfig

class UserServiceConfig(BaseConfig):
    """Configuration for user service."""
    max_users: int = 1000
    allow_registration: bool = True
    email_verification_required: bool = False
```

This configuration will be stored in the database and can be modified at runtime via the API.

## Step 2: Define Your Entity

Create a user entity extending `Entity`:

```python
from chapkit.core import Entity
from sqlalchemy.orm import Mapped, mapped_column

class User(Entity):
    """User entity for authentication."""
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str]
    full_name: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
```

The `Entity` base class provides `id`, `created_at`, and `updated_at` fields automatically.

## Step 3: Define Schemas

Create Pydantic schemas for input and output:

```python
from chapkit.core import EntityIn, EntityOut

class UserIn(EntityIn):
    """Input schema for creating/updating users."""
    username: str
    email: str
    full_name: str | None = None
    is_active: bool = True

class UserOut(EntityOut):
    """Output schema for API responses."""
    username: str
    email: str
    full_name: str | None
    is_active: bool
```

## Step 4: Create Repository

The repository handles database access:

```python
from chapkit.core import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

class UserRepository(BaseRepository[User, ULID]):
    """Repository for user data access."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def find_by_username(self, username: str) -> User | None:
        """Find user by username."""
        return await self.find_one_by(username=username)

    async def find_active_users(self) -> list[User]:
        """Find all active users."""
        return await self.find_all_by(is_active=True)
```

## Step 5: Create Manager

The manager adds business logic and validation:

```python
from chapkit.core import BaseManager
from chapkit.core.exceptions import ValidationError

class UserManager(BaseManager[User, UserIn, UserOut, ULID]):
    """Manager for user business logic."""

    def __init__(self, repo: UserRepository) -> None:
        super().__init__(repo, User, UserOut)

    async def _before_save(self, entity: User, input_data: UserIn) -> None:
        """Validate before saving."""
        # Check if username already exists
        existing = await self.repo.find_by_username(input_data.username)
        if existing and existing.id != entity.id:
            raise ValidationError(
                f"Username '{input_data.username}' already exists"
            )

    async def deactivate_user(self, user_id: ULID) -> UserOut:
        """Deactivate a user."""
        user = await self.get_by_id(user_id)
        user.is_active = False
        await self.repo.save(user)
        return self.to_output(user)
```

## Step 6: Create Dependency

FastAPI dependency for injecting the manager:

```python
from chapkit.core.api.dependencies import get_session
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

def get_user_manager(
    session: AsyncSession = Depends(get_session)
) -> UserManager:
    """Provide user manager instance."""
    return UserManager(UserRepository(session))
```

## Step 7: Create Router

Use `CrudRouter` for automatic CRUD endpoints:

```python
from chapkit.core.api import CrudRouter

user_router = CrudRouter.create(
    prefix="/api/v1/users",
    tags=["users"],
    entity_in_type=UserIn,
    entity_out_type=UserOut,
    manager_factory=get_user_manager,
)
```

## Step 8: Build the Application

Bring it all together with `ServiceBuilder`:

```python
from chapkit.core.api import BaseServiceBuilder, ServiceInfo

app = (
    BaseServiceBuilder(
        info=ServiceInfo(
            display_name="User Management Service",
            version="1.0.0",
            summary="Manage users with CRUD operations",
        ),
        database_url="sqlite+aiosqlite:///./users.db"
    )
    .with_health()
    .with_system()
    .with_jobs()
    .with_logging()
    .include_router(user_router)
    .build()
)
```

Note: We use `BaseServiceBuilder` instead of `ServiceBuilder` because we're not using the built-in Config/Artifact/Task modules.

## Complete Code

Here's the full `app.py`:

```python
"""User Management Service."""
from chapkit.core import Entity, EntityIn, EntityOut, BaseRepository, BaseManager
from chapkit.core.api import BaseServiceBuilder, ServiceInfo, CrudRouter
from chapkit.core.api.dependencies import get_session
from chapkit.core.exceptions import ValidationError
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from ulid import ULID


class User(Entity):
    """User entity for authentication."""
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str]
    full_name: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)


class UserIn(EntityIn):
    """Input schema for creating/updating users."""
    username: str
    email: str
    full_name: str | None = None
    is_active: bool = True


class UserOut(EntityOut):
    """Output schema for API responses."""
    username: str
    email: str
    full_name: str | None
    is_active: bool


class UserRepository(BaseRepository[User, ULID]):
    """Repository for user data access."""
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def find_by_username(self, username: str) -> User | None:
        """Find user by username."""
        return await self.find_one_by(username=username)


class UserManager(BaseManager[User, UserIn, UserOut, ULID]):
    """Manager for user business logic."""
    def __init__(self, repo: UserRepository) -> None:
        super().__init__(repo, User, UserOut)

    async def _before_save(self, entity: User, input_data: UserIn) -> None:
        """Validate before saving."""
        existing = await self.repo.find_by_username(input_data.username)
        if existing and existing.id != entity.id:
            raise ValidationError(f"Username '{input_data.username}' already exists")


def get_user_manager(session: AsyncSession = Depends(get_session)) -> UserManager:
    """Provide user manager instance."""
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
            display_name="User Management Service",
            version="1.0.0",
            summary="Manage users with CRUD operations",
        ),
        database_url="sqlite+aiosqlite:///./users.db"
    )
    .with_health()
    .with_system()
    .with_jobs()
    .with_logging()
    .include_router(user_router)
    .build()
)
```

## Run It

```bash
fastapi dev app.py
```

## Test the API

### Create a User

```bash
curl -X POST http://127.0.0.1:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "john@example.com",
    "full_name": "John Doe"
  }'
```

### List Users

```bash
curl http://127.0.0.1:8000/api/v1/users
```

### Get User by ID

```bash
curl http://127.0.0.1:8000/api/v1/users/01JB4K1234567890ABCDEFGHJK
```

### Update User

```bash
curl -X PUT http://127.0.0.1:8000/api/v1/users/01JB4K1234567890ABCDEFGHJK \
  -H "Content-Type: application/json" \
  -d '{
    "username": "johndoe",
    "email": "newemail@example.com",
    "full_name": "John Updated Doe"
  }'
```

### Delete User

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/users/01JB4K1234567890ABCDEFGHJK
```

## Add Custom Endpoints

Extend the router with custom operations:

```python
from chapkit.core.api import Router
from fastapi import Depends, HTTPException

class UserRouter(Router):
    """Custom user router with additional endpoints."""

    def _register_routes(self) -> None:
        @self.router.post("/{user_id}/$deactivate")
        async def deactivate_user(
            user_id: ULID,
            manager: UserManager = Depends(get_user_manager)
        ) -> UserOut:
            """Deactivate a user."""
            return await manager.deactivate_user(user_id)

        @self.router.get("/$active")
        async def list_active_users(
            manager: UserManager = Depends(get_user_manager)
        ) -> list[UserOut]:
            """List all active users."""
            users = await manager.repo.find_active_users()
            return [manager.to_output(user) for user in users]

# Include both routers
app.include_router(user_router)
app.include_router(UserRouter.create(prefix="/api/v1/users", tags=["users"]))
```

## Next Steps

- [Architecture](../architecture/index.md) - Understand the vertical slice pattern
- [Custom Routers](../guides/custom-routers.md) - Build advanced routers
- [Migrations](../guides/migrations.md) - Manage database schema changes
- [Testing](../guides/testing.md) - Test your service
