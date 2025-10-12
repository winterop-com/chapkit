# Chapkit

[![CI](https://img.shields.io/github/actions/workflow/status/winterop-com/chapkit/ci.yml?branch=main&label=CI)](https://github.com/winterop-com/chapkit/actions/workflows/ci.yml)
[![codecov](https://img.shields.io/codecov/c/github/winterop-com/chapkit/main)](https://codecov.io/gh/winterop-com/chapkit)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

Async SQLAlchemy database library for Python 3.13+ with FastAPI integration and ML workflow support.

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

## Links

- [Repository](https://github.com/winterop-com/chapkit)
- [Issues](https://github.com/winterop-com/chapkit/issues)
- [API Reference](api-reference.md)

## License

AGPL-3.0-or-later
