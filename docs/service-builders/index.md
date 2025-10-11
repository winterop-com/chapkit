# Service Builders

Service builders are the primary way to construct Chapkit applications. They use a fluent API to compose features.

## Three Builder Types

Chapkit provides three service builders for different use cases:

### 1. BaseServiceBuilder

**Location:** `chapkit.core.api`

**Use when:** Building custom services without the built-in modules (Config, Artifact, Task).

**Provides:**
- Core FastAPI setup (error handlers, middleware)
- Health checks (`.with_health()`)
- System info endpoint (`.with_system()`)
- Job scheduler (`.with_jobs()`)
- Database lifecycle management
- Logging support (`.with_logging()`)
- Custom router integration (`.include_router()`)

**Example:**

```python
from chapkit.core.api import BaseServiceBuilder, ServiceInfo

app = (
    BaseServiceBuilder(info=ServiceInfo(display_name="Custom Service"))
    .with_health()
    .with_system()
    .with_jobs()
    .include_router(custom_router)
    .build()
)
```

Learn more: [BaseServiceBuilder](base-service-builder.md)

### 2. ServiceBuilder

**Location:** `chapkit.api`

**Use when:** Building services with selective module composition.

**Extends BaseServiceBuilder with:**
- `.with_config(schema)` - Config module
- `.with_artifacts(hierarchy)` - Artifact module
- `.with_tasks()` - Task execution module
- `.with_ml(runner)` - ML train/predict module

**Example:**

```python
from chapkit.api import ServiceBuilder, ServiceInfo
from chapkit import BaseConfig

class MyConfig(BaseConfig):
    api_key: str

app = (
    ServiceBuilder(info=ServiceInfo(display_name="API Service"))
    .with_health()
    .with_config(MyConfig)
    .with_artifacts(hierarchy)
    .build()
)
```

Learn more: [ServiceBuilder](service-builder.md)

### 3. MLServiceBuilder

**Location:** `chapkit.api`

**Use when:** Building ML services with train/predict workflows.

**Auto-includes:**
- Structured logging
- Health checks
- System info
- Config module
- Artifact module
- Job scheduler
- ML endpoints

**Example:**

```python
from chapkit.api import MLServiceBuilder, ServiceInfo

app = MLServiceBuilder(
    info=ServiceInfo(display_name="ML Service"),
    config_schema=MyConfig,
    hierarchy=my_hierarchy,
    runner=my_runner,
).build()
```

**Reduces boilerplate from 8 method calls to 1!**

Learn more: [MLServiceBuilder](ml-service-builder.md)

## Comparison

| Feature | BaseServiceBuilder | ServiceBuilder | MLServiceBuilder |
|---------|-------------------|----------------|------------------|
| Health checks | ✅ `.with_health()` | ✅ `.with_health()` | ✅ Auto-enabled |
| System info | ✅ `.with_system()` | ✅ `.with_system()` | ✅ Auto-enabled |
| Job scheduler | ✅ `.with_jobs()` | ✅ `.with_jobs()` | ✅ Auto-enabled |
| Logging | ✅ `.with_logging()` | ✅ `.with_logging()` | ✅ Auto-enabled |
| Config module | ❌ | ✅ `.with_config()` | ✅ Required param |
| Artifacts | ❌ | ✅ `.with_artifacts()` | ✅ Required param |
| Tasks | ❌ | ✅ `.with_tasks()` | ❌ |
| ML endpoints | ❌ | ✅ `.with_ml()` | ✅ Required param |
| Custom routers | ✅ | ✅ | ✅ |
| Lifecycle hooks | ✅ | ✅ | ✅ |

## Common Features

All builders support:

### Service Info

```python
from chapkit.api import ServiceInfo

info = ServiceInfo(
    display_name="My Service",  # Required
    version="1.0.0",
    summary="Short description",
    description="Long description",
    contact={"email": "team@example.com"},
    license_info={"name": "MIT"},
)
```

For ML services, use `MLServiceInfo` for additional metadata.

### Database Configuration

```python
# In-memory (default, fast for tests)
database_url="sqlite+aiosqlite:///:memory:"

# File-based SQLite
database_url="sqlite+aiosqlite:///./app.db"

# PostgreSQL
database_url="postgresql+asyncpg://user:pass@localhost/db"
```

### Error Handlers

```python
# Enabled by default
ServiceBuilder(include_error_handlers=True)

# Disable to use custom error handling
ServiceBuilder(include_error_handlers=False)
```

### Lifecycle Hooks

```python
async def on_startup(app: FastAPI) -> None:
    print("Service starting...")

async def on_shutdown(app: FastAPI) -> None:
    print("Service stopping...")

app = (
    ServiceBuilder(info=info)
    .on_startup(on_startup)
    .on_shutdown(on_shutdown)
    .build()
)
```

### Custom Routers

```python
from chapkit.core.api import Router

class CustomRouter(Router):
    def _register_routes(self) -> None:
        @self.router.get("/custom")
        async def custom_endpoint():
            return {"message": "Hello"}

app = (
    ServiceBuilder(info=info)
    .include_router(CustomRouter.create(prefix="/api/v1"))
    .build()
)
```

## Choosing the Right Builder

**Use BaseServiceBuilder when:**

- You need custom entities without the built-in modules
- You want the lightest possible dependency footprint
- You're building a service that doesn't fit the module pattern

**Use ServiceBuilder when:**

- You need selective module composition
- You want explicit control over each feature
- You're building non-ML services with varying requirements

**Use MLServiceBuilder when:**

- You're building an ML service
- All ML dependencies are required (config, artifacts, jobs)
- You want minimal boilerplate

## Next Steps

- [BaseServiceBuilder](base-service-builder.md) - Core-only services
- [ServiceBuilder](service-builder.md) - Flexible composition
- [MLServiceBuilder](ml-service-builder.md) - ML services
