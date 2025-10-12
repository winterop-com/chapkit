# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

`chapkit` is an async SQLAlchemy database library for Python 3.13+ with FastAPI integration. Vertical slice architecture with framework-agnostic core, FastAPI layer, and domain modules.

**Primary Models:** Config (key-value with JSON), Artifact (hierarchical trees), Task (script execution with output capture), ML (train/predict operations with artifact-based model storage)

## Architecture

```
chapkit/
├── core/                 # Framework-agnostic infrastructure
│   ├── database.py      # Database, SqliteDatabase, SqliteDatabaseBuilder, migrations
│   ├── models.py        # Base, Entity ORM classes
│   ├── repository.py    # Repository, BaseRepository
│   ├── manager.py       # Manager, BaseManager
│   ├── schemas.py       # EntityIn, EntityOut, PaginatedResponse, JobRecord
│   ├── scheduler.py     # JobScheduler, AIOJobScheduler
│   ├── exceptions.py    # Error classes (NotFoundError, ValidationError, etc.)
│   ├── logging.py       # Structured logging
│   ├── types.py         # ULIDType, SQLAlchemy types
│   └── api/             # FastAPI framework layer
│       ├── router.py    # Router base class
│       ├── crud.py      # CrudRouter, CrudPermissions
│       ├── auth.py      # APIKeyMiddleware, key loading utilities
│       ├── dependencies.py  # get_database, get_session, get_scheduler
│       ├── middleware.py    # Error handlers, logging middleware
│       ├── pagination.py    # Pagination helpers
│       ├── utilities.py     # build_location_url, run_app
│       └── routers/     # Generic routers (HealthRouter, JobRouter, SystemRouter)
├── modules/             # Domain modules (vertical slices)
│   ├── config/         # Key-value config with JSON data
│   ├── artifact/       # Hierarchical artifact trees
│   ├── task/           # Script execution templates
│   └── ml/             # ML train/predict operations
└── api/                # Application orchestration
    ├── service_builder.py   # ServiceBuilder (app factory)
    └── dependencies.py      # get_config_manager, get_artifact_manager, get_task_manager, get_ml_manager
```

**Dependency Flow:**
- `core` → framework-agnostic (Database, SqliteDatabase, SqliteDatabaseBuilder, Repository, Manager, Entity, schemas)
- `core.api` → FastAPI layer (Router, CrudRouter, middleware, dependencies)
- `modules` → domain features, each with complete vertical slice (models, schemas, repository, manager, router)
- `api` → orchestration (ServiceBuilder, feature-specific dependencies)

**Layer Rules:**
- Core never imports from modules or api
- Modules may import from core but not from api
- Api imports from both core and modules

## Quick Start

```python
from chapkit import BaseConfig
from chapkit.api import ServiceBuilder, ServiceInfo

class MyConfig(BaseConfig):
    host: str
    port: int

app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()
    .with_config(MyConfig)
    .build()
)
```

**Run:** `fastapi dev your_file.py` or `python -m chapkit.api.run module:app`

## ServiceBuilder API

**BaseServiceBuilder** (in `chapkit.core.api`): Core FastAPI features only, no module dependencies
**ServiceBuilder** (in `chapkit.api`): Extends BaseServiceBuilder, adds `.with_config()`, `.with_artifacts()`, `.with_tasks()`, `.with_ml()`
**MLServiceBuilder** (in `chapkit.api`): Specialized builder that bundles health, config, artifacts, jobs, ml

**Key methods:**
- `.with_health()` - Health check endpoint at `/health` (operational)
- `.with_system()` - System info endpoint at `/system` (operational)
- `.with_monitoring()` - Prometheus metrics at `/metrics` (operational)
- `.with_config(schema)` - Config CRUD endpoints at `/api/v1/configs`
- `.with_artifacts(hierarchy)` - Artifact CRUD at `/api/v1/artifacts`
- `.with_jobs()` - Job scheduler at `/api/v1/jobs`
- `.with_tasks()` - Task execution at `/api/v1/tasks`
- `.with_ml(runner)` - ML train/predict at `/api/v1/ml`
- `.with_logging()` - Structured logging with request tracing
- `.with_auth()` - API key authentication
- `.with_database(url)` - Database configuration
- `.include_router(router)` - Add custom routers
- `.on_startup(hook)` / `.on_shutdown(hook)` - Lifecycle hooks
- `.build()` - Returns FastAPI app

**Endpoint Design:**
- **Operational endpoints** (root level): `/health`, `/system`, `/metrics` - infrastructure/monitoring concerns
- **API endpoints** (versioned): `/api/v1/*` - business logic and domain resources

## Common Endpoints

**Config Service:** Health check, CRUD operations, pagination (`?page=1&size=20`), schema endpoint (`/$schema`)
**Artifact Service:** CRUD + tree operations (`/$tree`), optional config linking
**Job Scheduler:** List/get/delete jobs, status filtering
**Task Service:** CRUD + execute operation (`/$execute`)
**ML Service:** Train (`/$train`) and predict (`/$predict`) operations

**Operation prefix:** `$` indicates operations (computed/derived data) vs resource access

## API Responses

- Simple operations return pure objects
- Collections support optional pagination (`?page=1&size=20`)
- Errors follow RFC 9457 with URN identifiers (`not-found`, `invalid-ulid`, `validation-failed`, `conflict`, `unauthorized`, `forbidden`)
- Schema endpoint auto-registered for all CrudRouters

## Database & Migrations

**Database classes:**
- `Database` - Generic base class (framework-agnostic)
- `SqliteDatabase` - SQLite-specific with WAL mode, pragmas, in-memory detection
- `SqliteDatabaseBuilder` - Fluent builder API (recommended)

**Migrations:**
- File DBs: Automatic Alembic migrations on `SqliteDatabase.init()`
- In-memory: Skip migrations (fast tests)

**Commands:**
```bash
make migrate MSG='description'  # Generate migration
make upgrade                    # Apply migrations (auto-applied on init)
```

**Workflow:**
1. Modify ORM models in `src/chapkit/modules/*/models.py`
2. Generate: `make migrate MSG='description'`
3. Review in `alembic/versions/`
4. Restart app (auto-applies)
5. Commit migration file

## Creating a New Module

1. **Structure:** Create `src/chapkit/modules/{name}/{__init__.py,models.py,schemas.py,repository.py,manager.py,router.py}`
2. **ORM Model:** Subclass `Entity` with `__tablename__` and `Mapped` fields
3. **Schemas:** Define `{Name}In(EntityIn)` and `{Name}Out(EntityOut)`
4. **Repository:** Subclass `BaseRepository[Model, ULID]`
5. **Manager:** Subclass `BaseManager[Model, ModelIn, ModelOut, ULID]`
6. **Router:** Subclass `CrudRouter[ModelIn, ModelOut]` or use `CrudRouter.create()`
7. **Export:** List all classes in `__all__` in `__init__.py`
8. **Migration:** Run `make migrate MSG='add {name} module'`
9. **Use:** Include router via `.include_router()` in ServiceBuilder

See full example in extended documentation or `examples/` directory.

## Code Quality

**Standards:**
- Python 3.13+, line length 120, type annotations required
- Double quotes, async/await, conventional commits
- Class order: public → protected → private
- `__all__` declarations only in `__init__.py` files

**Documentation Requirements:**
- Every Python file: one-line module docstring at top
- Every class: one-line docstring
- Every method/function: one-line docstring
- Use triple quotes `"""docstring"""`
- Keep concise - one line preferred

**Testing:**
```bash
make test      # Fast tests
make coverage  # With coverage
make lint      # Linting
```

**Always run `make lint` and `make test` after changes**

## Common Patterns

**Repository naming:**
- `find_*`: Single entity or None
- `find_all_*`: Sequence
- `exists_*`: Boolean
- `count`: Integer

**Manager vs Repository:**
- Repository: Low-level ORM data access
- Manager: Pydantic validation + business logic

## Dependency Management

**Always use `uv`:**
```bash
uv add <package>          # Runtime dependency
uv add --dev <package>    # Dev dependency
uv add <package>@latest   # Update specific
uv lock --upgrade         # Update all
```

**Never manually edit `pyproject.toml`**

## Git Workflow

**All changes must go through the branch + PR workflow.**

**Branch naming:**
- `feature/description` - New features
- `fix/description` - Bug fixes
- `chore/description` - Maintenance tasks
- `docs/description` - Documentation updates
- `github/description` - GitHub-specific changes

**Process:**
1. Create branch from `main`: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -m "feat: add new feature"`
3. Push: `git push -u origin feature/my-feature`
4. Create PR: `gh pr create --title "..." --body "..."`
5. Wait for manual review and merge

**Commit message prefixes:** `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`

**PR requirements:**
- All tests must pass (`make test`)
- All linting must pass (`make lint`)
- Code coverage should not decrease
- Descriptive PR title and body

## Key Dependencies

- sqlalchemy[asyncio] >= 2.0
- aiosqlite >= 0.21
- pydantic >= 2.11
- fastapi, ulid-py

## Additional Resources

- Full examples: `examples/` directory
- ML workflow guides: `examples/docs/` (ml_basic.md, ml_class.md, ml_shell.md)
- Postman collections: `examples/docs/*.postman_collection.json`
- Authentication docs: `docs/authentication.md`
