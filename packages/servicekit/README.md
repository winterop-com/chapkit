# servicekit

Async SQLAlchemy database library for Python 3.13+ with FastAPI integration.

## Features

- Async SQLAlchemy 2.0+ with SQLite/aiosqlite
- FastAPI integration with vertical slice architecture
- Built-in modules: Config, Artifact, Task
- Automatic Alembic migrations
- Repository and Manager patterns
- Type-safe with Pydantic schemas
- ULID-based entity identifiers

## Installation

```bash
pip install servicekit
```

## Quick Start

```python
from servicekit.api import ServiceBuilder, ServiceInfo

app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()
    .with_config()
    .build()
)
```

## Documentation

See the main repository documentation for detailed usage information.
