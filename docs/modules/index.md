# Modules

Chapkit includes four built-in domain modules that provide common functionality for services.

## Available Modules

### Config

Key-value configuration storage with typed JSON data.

- Store runtime configuration
- Pydantic schema validation
- Full CRUD operations
- Link configs to artifacts

[Learn more →](config.md)

### Artifacts

Hierarchical artifact storage for organizing data and models.

- Tree-based organization
- Custom hierarchy definitions
- Parent-child relationships
- Data and file storage

[Learn more →](artifacts.md)

### Tasks

Script execution templates with output capture.

- Define reusable task templates
- Execute bash or Python scripts
- Async execution via job scheduler
- Output and error capture

[Learn more →](tasks.md)

### ML

Machine learning train/predict workflows.

- Functional, class-based, and shell-based runners
- Automatic model artifact storage
- Async train/predict via jobs
- DataFrame and GeoJSON support

[Learn more →](ml.md)

## Module Architecture

Each module follows the same vertical slice pattern:

```
module/
├── __init__.py          # Public API
├── models.py            # ORM entities
├── schemas.py           # Pydantic validation
├── repository.py        # Data access
├── manager.py           # Business logic
└── router.py            # HTTP endpoints
```

## Using Modules

Enable modules in ServiceBuilder:

```python
from chapkit import BaseConfig
from chapkit.api import ServiceBuilder, ServiceInfo
from chapkit.modules.artifact import ArtifactHierarchy

class MyConfig(BaseConfig):
    api_key: str

hierarchy = ArtifactHierarchy(
    name="pipeline",
    level_labels={0: "input", 1: "output"}
)

app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_config(MyConfig)
    .with_artifacts(hierarchy=hierarchy)
    .with_tasks()
    .build()
)
```

## Creating Custom Modules

You can create your own modules following the same pattern:

```python
from chapkit.core import Entity, EntityIn, EntityOut, BaseRepository, BaseManager
from chapkit.core.api import CrudRouter

# 1. Define entity (models.py)
class Notification(Entity):
    __tablename__ = "notifications"
    message: Mapped[str]

# 2. Define schemas (schemas.py)
class NotificationIn(EntityIn):
    message: str

class NotificationOut(EntityOut):
    message: str

# 3. Create repository (repository.py)
class NotificationRepository(BaseRepository[Notification, ULID]):
    pass

# 4. Create manager (manager.py)
class NotificationManager(BaseManager[Notification, NotificationIn, NotificationOut, ULID]):
    pass

# 5. Create router (router.py)
notification_router = CrudRouter.create(
    prefix="/api/v1/notifications",
    tags=["notifications"],
    entity_in_type=NotificationIn,
    entity_out_type=NotificationOut,
    manager_factory=get_notification_manager,
)
```

[Learn more →](../guides/creating-modules.md)

## Next Steps

- [Config Module](config.md) - Key-value configuration
- [Artifacts Module](artifacts.md) - Hierarchical storage
- [Tasks Module](tasks.md) - Script execution
- [ML Module](ml.md) - Machine learning workflows
