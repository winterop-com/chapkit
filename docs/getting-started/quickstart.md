# Quick Start

Build your first Chapkit service in 5 minutes!

## Minimal Example

Create a file called `app.py`:

```python
from chapkit import BaseConfig
from chapkit.api import ServiceBuilder, ServiceInfo

class MyConfig(BaseConfig):
    """Your custom configuration schema."""
    host: str
    port: int

app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()
    .with_config(MyConfig)
    .build()
)
```

Run it:

```bash
fastapi dev app.py
```

Your service is now running at `http://127.0.0.1:8000`!

## Try It Out

### 1. Check Health

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "checks": {
    "database": "healthy"
  }
}
```

### 2. View Interactive Docs

Visit `http://127.0.0.1:8000/docs` in your browser to see the auto-generated Swagger UI.

### 3. Create a Config

```bash
curl -X POST http://127.0.0.1:8000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "name": "production",
    "data": {
      "host": "api.example.com",
      "port": 443
    }
  }'
```

Response:

```json
{
  "id": "01JB4K1234567890ABCDEFGHJK",
  "name": "production",
  "data": {
    "host": "api.example.com",
    "port": 443
  },
  "created_at": "2025-01-11T10:00:00Z",
  "updated_at": "2025-01-11T10:00:00Z"
}
```

### 4. List All Configs

```bash
curl http://127.0.0.1:8000/api/v1/config
```

### 5. Get By ID

```bash
curl http://127.0.0.1:8000/api/v1/config/01JB4K1234567890ABCDEFGHJK
```

## What Just Happened?

With just a few lines of code, you created a REST API with:

- ✅ Health check endpoint
- ✅ Full CRUD operations for configs
- ✅ Automatic database setup and migrations
- ✅ Request validation with Pydantic
- ✅ Interactive API documentation
- ✅ Error handling with RFC 9457 format

## Common Endpoints

Your service automatically includes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/config` | GET | List all configs |
| `/api/v1/config` | POST | Create new config |
| `/api/v1/config/{id}` | GET | Get by ID |
| `/api/v1/config/{id}` | PUT | Update by ID |
| `/api/v1/config/{id}` | DELETE | Delete by ID |
| `/api/v1/config/$schema` | GET | Get JSON schema |

## Add More Features

### Add System Info

```python
app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()
    .with_system()  # Add this
    .with_config(MyConfig)
    .build()
)
```

Now you can check system info:

```bash
curl http://127.0.0.1:8000/api/v1/system
```

### Add Background Jobs

```python
app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()
    .with_jobs()  # Add this
    .with_config(MyConfig)
    .build()
)
```

### Add Artifacts

```python
from chapkit.modules.artifact import ArtifactHierarchy

hierarchy = ArtifactHierarchy(
    name="my_pipeline",
    level_labels={0: "input", 1: "output"}
)

app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()
    .with_config(MyConfig)
    .with_artifacts(hierarchy=hierarchy)  # Add this
    .build()
)
```

## Use Persistent Database

By default, Chapkit uses an in-memory SQLite database. For persistence:

```python
app = (
    ServiceBuilder(
        info=ServiceInfo(display_name="My Service"),
        database_url="sqlite+aiosqlite:///./myapp.db"  # Persist to file
    )
    .with_health()
    .with_config(MyConfig)
    .build()
)
```

For PostgreSQL:

```bash
# Install async PostgreSQL driver
uv add asyncpg
```

```python
database_url = "postgresql+asyncpg://user:pass@localhost/dbname"
```

## Next Steps

- [Your First Service](first-service.md) - Deep dive into service creation
- [Service Builders](../service-builders/index.md) - Learn about different builders
- [Architecture](../architecture/index.md) - Understand the design
- [Modules](../modules/index.md) - Explore built-in modules
