# Chapkit

[![CI](https://github.com/winterop-com/chapkit/actions/workflows/ci.yml/badge.svg)](https://github.com/winterop-com/chapkit/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/winterop-com/chapkit/branch/main/graph/badge.svg)](https://codecov.io/gh/winterop-com/chapkit)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

**Async SQLAlchemy database library for Python 3.13+ with FastAPI integration and ML workflow support.**

Chapkit provides a vertical slice architecture with a framework-agnostic core, FastAPI layer, and domain modules for building REST APIs with automatic CRUD operations, job scheduling, and ML train/predict workflows.

## Features

- **Framework-Agnostic Core**: Database, Repository, Manager patterns independent of web framework
- **FastAPI Integration**: Automatic CRUD endpoints, health checks, job scheduling
- **Domain Modules**: Config (key-value store), Artifacts (hierarchical trees), Tasks (script execution), ML (train/predict)
- **ML Workflows**: Support for functional, class-based, and shell-based model runners
- **Async First**: Built on SQLAlchemy async with aiosqlite
- **Type Safe**: Full type annotations with mypy and pyright strict mode
- **Automatic Migrations**: Alembic migrations applied automatically

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

Run with: `fastapi dev your_file.py`

## Installation

```bash
uv add chapkit
```

## Development

```bash
# Install dependencies
make install

# Run tests
make test

# Run linting
make lint

# Generate coverage report
make coverage
```

## Links

- **Repository**: [https://github.com/winterop-com/chapkit](https://github.com/winterop-com/chapkit)
- **Issues**: [https://github.com/winterop-com/chapkit/issues](https://github.com/winterop-com/chapkit/issues)
- **Documentation**: You're reading it!

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](https://github.com/winterop-com/chapkit/blob/main/LICENSE) file for details.

## Next Steps

- [Installation Guide](getting-started/installation.md) - Install Chapkit and set up your environment
- [Quick Start](getting-started/quickstart.md) - Build your first service in 5 minutes
- [Architecture Overview](architecture/index.md) - Understand Chapkit's vertical slice architecture
- [ML Workflows](ml-workflows/index.md) - Train and predict with machine learning models
