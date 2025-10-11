# Installation

Learn how to install Chapkit and set up your development environment.

## Requirements

- **Python 3.13+** - Chapkit uses the latest Python features
- **uv** (recommended) or pip for package management

## Using uv (Recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver:

```bash
# Install Chapkit
uv add chapkit

# For development with all optional dependencies
uv add chapkit --dev
```

## Using pip

```bash
# Install Chapkit
pip install chapkit

# For development
pip install chapkit[dev]
```

## Verify Installation

Check that Chapkit is installed correctly:

```python
import chapkit
print(chapkit.__version__)
```

Or run a simple test:

```bash
python -c "from chapkit import BaseConfig; print('Chapkit installed successfully!')"
```

## Development Setup

If you want to contribute to Chapkit or explore the examples:

### 1. Clone the Repository

```bash
git clone https://github.com/winterop-com/chapkit.git
cd chapkit
```

### 2. Install Dependencies

```bash
# Using make (recommended)
make install

# Or directly with uv
uv sync --all-groups
```

### 3. Run Tests

```bash
# Run tests
make test

# Run with coverage
make coverage

# Run linting
make lint
```

## Optional Dependencies

Chapkit has optional dependencies for different use cases:

### ML Support

For machine learning workflows:

```bash
uv add scikit-learn pandas
```

### Development Tools

For development and testing:

```bash
uv add --dev pytest pytest-cov mypy ruff pyright
```

## IDE Setup

### VS Code

Recommended extensions:

- Python
- Pylance
- Ruff

Recommended settings (`.vscode/settings.json`):

```json
{
  "python.analysis.typeCheckingMode": "strict",
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit",
      "source.organizeImports": "explicit"
    }
  }
}
```

### PyCharm

1. Enable type checking in Settings → Python Integrated Tools
2. Configure Ruff as external tool
3. Enable format on save

## Troubleshooting

### Python Version Issues

Chapkit requires Python 3.13+. Check your version:

```bash
python --version
```

If you have multiple Python versions, use:

```bash
python3.13 -m pip install chapkit
```

### Import Errors

If you get import errors, ensure Chapkit is installed in the correct environment:

```bash
# Check installed packages
uv pip list | grep chapkit

# Reinstall if needed
uv add chapkit --force-reinstall
```

### SQLAlchemy Warnings

If you see SQLAlchemy warnings about async, ensure you're using:

- `aiosqlite` for SQLite
- `asyncpg` for PostgreSQL
- `aiomysql` for MySQL

## Next Steps

Now that Chapkit is installed:

- [Quick Start](quickstart.md) - Build your first service
- [Your First Service](first-service.md) - Detailed walkthrough
- [Examples](https://github.com/winterop-com/chapkit/tree/main/examples) - Explore example code
