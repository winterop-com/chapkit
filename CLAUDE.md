# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

`chapkit` is an async SQLAlchemy database library for Python 3.13+ with FastAPI integration. Vertical slice architecture with framework-agnostic core, FastAPI layer, and domain modules.

**Primary Models:** Config (key-value with JSON), Artifact (hierarchical trees), Task (script execution with output capture), ML (train/predict operations with artifact-based model storage)

## Architecture

```
chapkit/
├── core/                 # Framework-agnostic infrastructure
│   ├── database.py      # Database, migrations
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
- `core` → framework-agnostic (Database, Repository, Manager, Entity, schemas)
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

## Using Core Only (Without Modules)

For projects that need FastAPI support but don't require the built-in modules (Config, Artifact, Task), use `BaseServiceBuilder` from `chapkit.core.api`:

```python
from chapkit.core.api import BaseServiceBuilder, ServiceInfo, CrudRouter
from chapkit.core.api.dependencies import get_session
from chapkit.core import Entity, EntityIn, EntityOut, BaseRepository, BaseManager
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from ulid import ULID

# Define your custom entity
class User(Entity):
    """User entity for authentication."""
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str]

class UserIn(EntityIn):
    """User input schema."""
    username: str
    email: str

class UserOut(EntityOut):
    """User output schema."""
    username: str
    email: str

# Repository and Manager
class UserRepository(BaseRepository[User, ULID]):
    """Repository for user data access."""
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

class UserManager(BaseManager[User, UserIn, UserOut, ULID]):
    """Manager for user business logic."""
    def __init__(self, repo: UserRepository) -> None:
        super().__init__(repo, User, UserOut)

# Dependency
def get_user_manager(session=Depends(get_session)) -> UserManager:
    """Provide user manager instance."""
    return UserManager(UserRepository(session))

# Router with auto CRUD endpoints
user_router = CrudRouter.create(
    prefix="/api/v1/users",
    tags=["users"],
    entity_in_type=UserIn,
    entity_out_type=UserOut,
    manager_factory=get_user_manager,
)

# Build app with BaseServiceBuilder (no module dependencies)
app = (
    BaseServiceBuilder(info=ServiceInfo(display_name="User Service"))
    .with_database("sqlite+aiosqlite:///./users.db")
    .with_health()
    .with_system()
    .with_jobs()
    .include_router(user_router)
    .build()
)
```

**BaseServiceBuilder provides:**
- Core FastAPI setup (error handlers, middleware)
- Health checks (`.with_health()`)
- System info endpoint (`.with_system()`)
- Job scheduler (`.with_jobs()`)
- Database lifecycle management
- Logging support (`.with_logging()`)
- Custom router integration (`.include_router()`)
- Lifecycle hooks (`.on_startup()`, `.on_shutdown()`)

**When to use:**
- Building custom services without Config/Artifact/Task modules
- Lighter dependency footprint (no module layer)
- Full control over domain models and APIs

**ServiceBuilder vs BaseServiceBuilder:**
- `BaseServiceBuilder` (in `chapkit.core.api`): Core FastAPI features only, no module dependencies
- `ServiceBuilder` (in `chapkit.api`): Extends BaseServiceBuilder, adds `.with_config()`, `.with_artifacts()`, `.with_tasks()`

## ServiceBuilder API

**Constructor:**
```python
ServiceBuilder(
    info=ServiceInfo(...),
    database_url="sqlite+aiosqlite:///:memory:",  # Optional
    include_error_handlers=True,  # Optional
)
```

**Methods:**
- `.with_health(prefix="/api/v1/health", checks=None, include_database_check=True)` - Health endpoint with custom checks
- `.with_config(schema, prefix="/api/v1/config", allow_create=True, ...)` - Config CRUD endpoints
- `.with_artifacts(hierarchy, prefix="/api/v1/artifacts", enable_config_linking=False, ...)` - Artifact CRUD
- `.with_jobs(prefix="/api/v1/jobs", max_concurrency=None)` - Job scheduler for async tasks
- `.with_tasks(prefix="/api/v1/tasks")` - Task execution CRUD with bash/script execution
- `.with_ml(runner, prefix="/api/v1/ml")` - ML train/predict endpoints with model runner
- `.with_logging()` - Enable structured logging with request tracing
- `.with_auth(api_keys=None, api_key_file=None, env_var="CHAPKIT_API_KEYS", header_name="X-API-Key", unauthenticated_paths=None)` - Enable API key authentication
- `.include_router(router)` - Add custom routers
- `.on_startup(hook)` / `.on_shutdown(hook)` - Lifecycle hooks
- `.build()` - Returns FastAPI app

**ServiceInfo:**
```python
ServiceInfo(
    display_name="My Service",  # Required
    version="1.0.0",
    summary="...",
    description="...",
    contact={"email": "..."},
    license_info={"name": "MIT"},
)
```

## MLServiceBuilder API

**Specialized builder for ML services** that bundles all required components (health, config, artifacts, jobs, ml) into a single constructor, reducing boilerplate from 7 method calls to 2.

**Constructor:**
```python
MLServiceBuilder(
    info=ServiceInfo(...),              # Required: Service metadata
    config_schema=YourConfig,           # Required: BaseConfig subclass
    hierarchy=ArtifactHierarchy(...),   # Required: Artifact hierarchy
    runner=your_runner,                 # Required: ModelRunnerProtocol implementation
    database_url="sqlite+aiosqlite:///:memory:",  # Optional
    include_error_handlers=True,        # Optional
    include_logging=True,               # Optional (enabled by default for ML services)
)
```

**Automatically enables:**
- Structured logging with request tracing
- `.with_health()` - Health check endpoint
- `.with_system()` - System info endpoint
- `.with_config(config_schema)` - Config CRUD endpoints
- `.with_artifacts(hierarchy=hierarchy)` - Artifact CRUD for model storage
- `.with_jobs()` - Job scheduler for async train/predict
- `.with_ml(runner=runner)` - ML train/predict endpoints

**Still available (optional):**
- `.with_auth()` - Enable API key authentication (inherited from ServiceBuilder)
- `.include_router(router)` - Add custom routers
- `.on_startup(hook)` / `.on_shutdown(hook)` - Lifecycle hooks
- `.build()` - Returns FastAPI app

**Example:**
```python
from chapkit import BaseConfig
from chapkit.api import MLServiceBuilder, ServiceInfo
from chapkit.modules.artifact import ArtifactHierarchy
from chapkit.modules.ml import FunctionalModelRunner

class DiseaseConfig(BaseConfig):
    min_samples: int = 3

HIERARCHY = ArtifactHierarchy(
    name="ml_pipeline",
    level_labels={0: "trained_model", 1: "predictions"},
)

runner = FunctionalModelRunner(on_train=on_train, on_predict=on_predict)

# Before: 8 method calls
app = (
    ServiceBuilder(info=info, database_url="...")
    .with_logging()
    .with_health()
    .with_system()
    .with_config(DiseaseConfig)
    .with_artifacts(hierarchy=HIERARCHY)
    .with_jobs()
    .with_ml(runner=runner)
    .build()
)

# After: 1 method call
app = MLServiceBuilder(
    info=info,
    database_url="...",
    config_schema=DiseaseConfig,
    hierarchy=HIERARCHY,
    runner=runner,
).build()
```

**With authentication:**
```python
# Add authentication to ML service
app = (
    MLServiceBuilder(
        info=info,
        database_url="...",
        config_schema=DiseaseConfig,
        hierarchy=HIERARCHY,
        runner=runner,
    )
    .with_auth()  # Reads from CHAPKIT_API_KEYS env var
    .build()
)
```

**When to use:**
- Building ML services (train/predict workflows)
- Want minimal boilerplate
- All ML requirements are fixed (config, artifacts, jobs always needed)

**When to use ServiceBuilder instead:**
- Need selective module composition
- Building non-ML services
- Want explicit control over each component

## MLServiceInfo API

**Extended service metadata for ML services** with additional fields for author information, organization details, maturity assessment, and citation info.

**Class:**
```python
from chapkit.api import MLServiceInfo, AssessedStatus

MLServiceInfo(
    # ServiceInfo fields (inherited)
    display_name="Disease Prediction ML Model",    # Required
    version="1.0.0",
    summary="Predicts disease outbreaks from climate data",
    description="Long description...",
    contact={"email": "team@example.com"},
    license_info={"name": "MIT"},

    # ML-specific fields
    author="Dr. Jane Smith",                       # Optional: Model author
    author_note="Updated with 2024 training data", # Optional: Author notes/changelog
    author_assessed_status=AssessedStatus.green,   # Optional: Maturity assessment
    contact_email="jane.smith@example.com",        # Optional: Direct contact email
    organization="Example Research Lab",           # Optional: Organization name
    organization_logo_url="https://example.com/logo.png",  # Optional: Logo URL
    citation_info="Smith et al. (2024) ...",       # Optional: Citation information
)
```

**AssessedStatus enum values:**
- `gray` - Not intended for use, deprecated, or meant for legacy use only
- `red` - Highly experimental prototype, not validated, only for early experimentation
- `orange` - Shows promise on limited data, needs manual configuration and careful evaluation
- `yellow` - Ready for more rigorous testing
- `green` - Validated and ready for production use

**Usage with MLServiceBuilder:**
```python
from chapkit.api import MLServiceBuilder, MLServiceInfo, AssessedStatus

info = MLServiceInfo(
    display_name="Disease Outbreak Predictor",
    version="2.1.0",
    description="Predicts disease outbreak probability using climate indicators",
    author="Dr. Jane Smith",
    author_note="Improved accuracy with ensemble methods",
    author_assessed_status=AssessedStatus.green,
    contact_email="jane.smith@research.org",
    organization="Global Health Research Institute",
    organization_logo_url="https://ghri.org/logo.png",
    citation_info="Smith, J. et al. (2024). Climate-based disease prediction. Nature Medicine, 30(4), 123-145.",
)

app = MLServiceBuilder(
    info=info,
    config_schema=DiseaseConfig,
    hierarchy=HIERARCHY,
    runner=runner,
).build()
```

**When to use MLServiceInfo:**
- Publishing ML models for external use
- Need to track model authorship and versioning
- Want to communicate model maturity/validation status
- Require citation information for academic models
- Building model registry or marketplace

**When to use ServiceInfo:**
- Internal ML services
- Simple prototypes
- Basic service metadata is sufficient

## Common Endpoints

**Config Service** creates:
- `GET /api/v1/health` - Health check
- `POST /api/v1/config` - Create
- `GET /api/v1/config` - List all (supports `?page=1&size=20`)
- `GET /api/v1/config/$schema` - Get Pydantic JSON schema
- `GET /api/v1/config/{id}` - Get by ID
- `PUT /api/v1/config/{id}` - Update
- `DELETE /api/v1/config/{id}` - Delete

**Artifact Service** adds:
- Similar CRUD endpoints for artifacts
- `GET /api/v1/artifacts/{id}/$tree` - Get tree structure (operation)
- `POST /api/v1/config/{config_id}/artifacts/{artifact_id}` - Link config (if enabled)

**Job Scheduler** creates:
- `GET /api/v1/jobs` - List jobs (filter: `?status_filter=completed`)
- `GET /api/v1/jobs/{id}` - Get job record
- `DELETE /api/v1/jobs/{id}` - Cancel/delete

**Task Service** creates:
- `POST /api/v1/tasks` - Create task
- `GET /api/v1/tasks` - List all (supports `?page=1&size=20`)
- `GET /api/v1/tasks/{id}` - Get by ID
- `PUT /api/v1/tasks/{id}` - Update task
- `DELETE /api/v1/tasks/{id}` - Delete task
- `POST /api/v1/tasks/{id}/$execute` - Execute task asynchronously (requires `.with_jobs()`)

**ML Service** creates:
- `POST /api/v1/ml/$train` - Train model asynchronously (returns job_id + model_artifact_id)
- `POST /api/v1/ml/$predict` - Make predictions asynchronously (returns job_id + prediction_artifact_id)

## Examples

### Config + Artifacts with Linking

```python
from chapkit import BaseConfig
from chapkit.api import ServiceBuilder, ServiceInfo
from chapkit.modules.artifact import ArtifactHierarchy

class ExperimentConfig(BaseConfig):
    model: str
    learning_rate: float

HIERARCHY = ArtifactHierarchy(
    name="ml_pipeline",
    level_labels={0: "train", 1: "predict", 2: "result"}
)

app = (
    ServiceBuilder(info=ServiceInfo(display_name="ML Pipeline"))
    .with_health()
    .with_config(ExperimentConfig)
    .with_artifacts(hierarchy=HIERARCHY, enable_config_linking=True)
    .build()
)
```

### Custom Router

```python
from chapkit.api.dependencies import get_config_manager
from chapkit.core.api import Router
from fastapi import Depends

class CustomRouter(Router):
    def _register_routes(self) -> None:
        @self.router.get("/stats")
        async def get_stats(manager=Depends(get_config_manager)):
            return {"total": await manager.count()}

app.include_router(CustomRouter.create(prefix="/api/v1/custom", tags=["custom"]))
```

### Startup Hook for Seeding

```python
from chapkit import ConfigIn, ConfigManager, ConfigRepository, Database
from fastapi import FastAPI

async def seed_data(app: FastAPI) -> None:
    db: Database = app.state.database
    async with db.session() as session:
        repo = ConfigRepository(session)
        manager = ConfigManager[AppConfig](repo, AppConfig)
        await manager.save(ConfigIn[AppConfig](name="default", data=AppConfig(...)))

app = ServiceBuilder(info=info).with_config(AppConfig).on_startup(seed_data).build()
```

### API Key Authentication

For service-to-service communication in Docker Compose environments. Supports environment variables, Docker secrets, and direct keys (dev only).

**Production (Environment Variables):**
```python
from chapkit import BaseConfig
from chapkit.api import ServiceBuilder, ServiceInfo

class AppConfig(BaseConfig):
    environment: str

# Reads from CHAPKIT_API_KEYS environment variable
app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()
    .with_config(AppConfig)
    .with_auth()  # Reads from CHAPKIT_API_KEYS env var
    .build()
)
```

Run with:
```bash
export CHAPKIT_API_KEYS="sk_prod_abc123,sk_prod_xyz789"
fastapi dev your_file.py
```

**Docker Secrets:**
```python
app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()
    .with_config(AppConfig)
    .with_auth(api_key_file="/run/secrets/api_keys")
    .build()
)
```

**Development (Direct Keys):**
```python
# WARNING: Only for examples and local development
app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()
    .with_config(AppConfig)
    .with_auth(api_keys=["sk_dev_test123"])
    .build()
)
```

**Configuration Options:**
```python
.with_auth(
    api_keys=None,                      # Direct list (dev only)
    api_key_file=None,                  # File path (Docker secrets)
    env_var="CHAPKIT_API_KEYS",         # Environment variable name
    header_name="X-API-Key",            # HTTP header for API key
    unauthenticated_paths=None,         # Paths without auth
)
```

**Key Format Convention:**
```
sk_prod_a1b2c3d4e5f6g7h8     # Production
sk_dev_test123               # Development
```

**Testing Authenticated Endpoints:**
```bash
# Valid request
curl -H "X-API-Key: sk_dev_test123" http://localhost:8000/api/v1/config

# Missing key (returns 401)
curl http://localhost:8000/api/v1/config

# Unauthenticated path (no key needed)
curl http://localhost:8000/api/v1/health
```

**Default Unauthenticated Paths:**
- `/docs` - Swagger UI
- `/redoc` - ReDoc
- `/openapi.json` - OpenAPI schema
- `/api/v1/health` - Health check
- `/` - Landing page

**Custom Unauthenticated Paths:**
```python
.with_auth(unauthenticated_paths=["/health", "/public", "/status"])
```

**Key Rotation:**
Support multiple active keys during rotation:
```bash
# Step 1: Add new key (both keys work)
export CHAPKIT_API_KEYS="sk_prod_old123,sk_prod_new456"

# Step 2: Update all clients to use new key

# Step 3: Remove old key
export CHAPKIT_API_KEYS="sk_prod_new456"
```

**Security Features:**
- Only first 7 characters logged (`sk_prod_****`)
- RFC 9457 error responses (401 Unauthorized)
- Prefix attached to request state for tracing
- No database storage required

**For complete documentation, see:** `docs/authentication.md`

### ML Train/Predict with Artifacts

```python
from typing import Any
import pandas as pd
from geojson_pydantic import FeatureCollection
from sklearn.linear_model import LinearRegression

from chapkit import BaseConfig
from chapkit.api import MLServiceBuilder, ServiceInfo
from chapkit.modules.artifact import ArtifactHierarchy
from chapkit.modules.ml import FunctionalModelRunner

class DiseaseConfig(BaseConfig):
    """Configuration for disease prediction model."""
    pass

async def on_train(
    config: DiseaseConfig,
    data: pd.DataFrame,
    geo: FeatureCollection | None = None,
) -> Any:
    """Train a linear regression model."""
    features = ["rainfall", "mean_temperature"]
    X = data[features]
    Y = data["disease_cases"].fillna(0)

    model = LinearRegression()
    model.fit(X, Y)
    return model

async def on_predict(
    config: DiseaseConfig,
    model: Any,
    historic: pd.DataFrame | None,
    future: pd.DataFrame,
    geo: FeatureCollection | None = None,
) -> pd.DataFrame:
    """Make predictions using trained model."""
    X = future[["rainfall", "mean_temperature"]]
    future["sample_0"] = model.predict(X)
    return future

runner = FunctionalModelRunner(on_train=on_train, on_predict=on_predict)

HIERARCHY = ArtifactHierarchy(
    name="ml_pipeline",
    level_labels={0: "trained_model", 1: "predictions"},
)

app = MLServiceBuilder(
    info=ServiceInfo(display_name="Disease Prediction"),
    config_schema=DiseaseConfig,
    hierarchy=HIERARCHY,
    runner=runner,
).build()
```

**Usage:**
1. Create config: `POST /api/v1/config` with `{"name": "prod", "data": {}}`
2. Train model: `POST /api/v1/ml/$train` with `{"config_id": "...", "data": {"columns": [...], "data": [...]}}`
3. Check job: `GET /api/v1/jobs/{job_id}`
4. Get model: `GET /api/v1/artifacts/{model_artifact_id}`
5. Predict: `POST /api/v1/ml/$predict` with `{"model_artifact_id": "...", "future": {"columns": [...], "data": [...]}}`
6. Get predictions: `GET /api/v1/artifacts/{prediction_artifact_id}`

### ML with Class-Based Runner

For OOP-style ML workflows, subclass `BaseModelRunner` instead of using functions:

```python
from typing import Any
import pandas as pd
from sklearn.preprocessing import StandardScaler
from chapkit import BaseConfig
from chapkit.modules.ml import BaseModelRunner

class WeatherConfig(BaseConfig):
    """Configuration with training parameters."""
    min_samples: int = 5
    normalize_features: bool = True

class WeatherModelRunner(BaseModelRunner):
    """Custom runner with preprocessing and shared state."""

    def __init__(self) -> None:
        """Initialize runner with shared state."""
        self.feature_names: list[str] = ["rainfall", "temperature", "humidity"]
        self.scaler: StandardScaler | None = None

    async def on_init(self) -> None:
        """Optional initialization hook before train/predict."""
        # Setup resources, logging, etc.
        pass

    async def on_cleanup(self) -> None:
        """Optional cleanup hook after train/predict."""
        # Clean up resources
        pass

    async def on_train(
        self,
        config: WeatherConfig,
        data: pd.DataFrame,
        geo: FeatureCollection | None = None,
    ) -> Any:
        """Train with preprocessing."""
        # Validate
        if len(data) < config.min_samples:
            raise ValueError(f"Need {config.min_samples} samples")

        # Preprocess
        X = data[self.feature_names]
        if config.normalize_features:
            self.scaler = StandardScaler()
            X = self.scaler.fit_transform(X)

        # Train and return model + preprocessing artifacts
        model = LinearRegression()
        model.fit(X, data["target"])

        return {"model": model, "scaler": self.scaler, "features": self.feature_names}

    async def on_predict(
        self,
        config: WeatherConfig,
        model: Any,
        historic: pd.DataFrame | None,
        future: pd.DataFrame,
        geo: FeatureCollection | None = None,
    ) -> pd.DataFrame:
        """Predict with same preprocessing."""
        # Extract artifacts
        trained_model = model["model"]
        scaler = model.get("scaler")
        features = model["features"]

        # Apply same preprocessing
        X = future[features]
        if scaler is not None:
            X = scaler.transform(X)

        future["prediction"] = trained_model.predict(X)
        return future

# Use class-based runner with MLServiceBuilder
runner = WeatherModelRunner()
hierarchy = ArtifactHierarchy(
    name="weather_ml_pipeline",
    level_labels={0: "trained_model", 1: "predictions"},
)

app = MLServiceBuilder(
    info=info,
    config_schema=WeatherConfig,
    hierarchy=hierarchy,
    runner=runner,
).build()
```

**When to use class-based:**
- Need shared state between train/predict (scalers, feature names, etc.)
- Want lifecycle hooks for setup/cleanup
- Prefer OOP over functional style
- Complex ML pipelines with multiple steps

**When to use functional:**
- Simple stateless train/predict logic
- Prefer functional programming style
- Quick prototypes and examples

### ML with Shell-Based Runner

For language-agnostic ML workflows, use `ShellModelRunner` to execute external scripts:

```python
import sys
from pathlib import Path
from chapkit import BaseConfig
from chapkit.modules.ml import ShellModelRunner

class DiseaseConfig(BaseConfig):
    """Configuration accessible to external scripts via JSON."""
    model_type: str = "linear_regression"

# Path to external scripts (Python, R, Julia, etc.)
SCRIPTS_DIR = Path(__file__).parent / "scripts"

# Command templates with variable substitution
train_command = (
    f"{sys.executable} {SCRIPTS_DIR}/train_model.py "
    "--config {config_file} "
    "--data {data_file} "
    "--model {model_file}"
)

predict_command = (
    f"{sys.executable} {SCRIPTS_DIR}/predict_model.py "
    "--config {config_file} "
    "--model {model_file} "
    "--future {future_file} "
    "--output {output_file}"
)

# Create shell-based runner
runner = ShellModelRunner(
    train_command=train_command,
    predict_command=predict_command,
    model_format="pickle",  # or "joblib"
)

hierarchy = ArtifactHierarchy(
    name="shell_ml_pipeline",
    level_labels={0: "trained_model", 1: "predictions"},
)

app = MLServiceBuilder(
    info=info,
    config_schema=DiseaseConfig,
    hierarchy=hierarchy,
    runner=runner,
).build()
```

**Variable substitution patterns:**
- `{config_file}` - Path to config JSON file
- `{data_file}` - Path to training data CSV
- `{model_file}` - Path to save/load model (pickle/joblib)
- `{output_file}` - Path for prediction results CSV
- `{historic_file}` - Path to historic data CSV (optional, empty string if None)
- `{future_file}` - Path to future data CSV (for predict)
- `{geo_file}` - Path to GeoJSON file (optional, empty string if None)

**Example external training script (Python):**
```python
#!/usr/bin/env python3
import argparse
import json
import pickle
import pandas as pd
from sklearn.linear_model import LinearRegression

parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True)
parser.add_argument("--data", required=True)
parser.add_argument("--model", required=True)
args = parser.parse_args()

# Load config and data
with open(args.config) as f:
    config = json.load(f)
data = pd.read_csv(args.data)

# Train model
X = data[["rainfall", "temperature"]]
y = data["disease_cases"]
model = LinearRegression()
model.fit(X, y)

# Save model
with open(args.model, "wb") as f:
    pickle.dump(model, f)

print("Training completed")
```

**When to use shell-based:**
- Integrate existing ML scripts without modification
- Language-agnostic workflows (R, Julia, CLI tools)
- Container-based execution
- External tools that can't run in Python process
- Team has expertise in different languages

**When to use class-based:**
- Need shared state between train/predict
- Want lifecycle hooks for setup/cleanup
- Prefer OOP over functional style
- Pure Python workflows

**When to use functional:**
- Simple stateless train/predict logic
- Prefer functional programming style
- Quick prototypes and examples

## ML Examples & Documentation

### Complete cURL Guides

Comprehensive step-by-step guides with real ULIDs in `examples/docs/`:

**ML Example Guides:**
- `ml_basic.md` - Functional runner with LinearRegression (2 features)
- `ml_class.md` - Class-based runner with preprocessing (3 features, StandardScaler)
- `ml_shell.md` - Shell-based runner for language-agnostic workflows

**Quick References:**
- `README.md` - ML workflow overview and common patterns
- `quick_reference.md` - One-page cheat sheet with bash workflow script

Each guide includes:
- Complete workflow (health → config → train → predict)
- Sample datasets (minimal, realistic, with outliers)
- Error handling and troubleshooting
- Advanced features and tips
- Real ULIDs for reproducibility

### Postman Collections

Import-ready Postman Collection v2.1 JSON files in `examples/docs/`:

- `ml_basic.postman_collection.json` - Functional runner workflow (20+ requests)
- `ml_class.postman_collection.json` - Class-based with preprocessing
- `ml_shell.postman_collection.json` - Language-agnostic shell runner
- `POSTMAN.md` - Import instructions, usage guide, troubleshooting

**Features:**
- Auto-capture IDs via test scripts (config_id, job_id, artifact_id)
- Pre-configured with real ULIDs
- Organized folder structure (Health, Config, Training, Predictions)
- Example responses for all requests
- Environment variable support for dev/staging/production
- Collection Runner compatible for automated testing

**Import to Postman:**
1. Open Postman → Click "Import"
2. Select `.postman_collection.json` files
3. Collections appear in sidebar ready to use

**Re-import updates:** Simply re-import and choose "Replace" - no manual deletion needed

## CRUD Operations with $ Prefix

The `$` prefix indicates **operations** (computed/derived data) vs resource access:
- Entity: `GET /artifacts/{id}/$tree` - Compute tree
- Entity: `POST /tasks/{id}/$execute` - Execute task
- Collection: `POST /configs/$bulk-delete` - Bulk action
- Collection: `GET /users/$schema` - Get Pydantic JSON schema (auto-registered for all CrudRouters)

**Supports all HTTP methods:** GET (retrieve), POST (action), PUT/PATCH (update), DELETE (remove)

Use for: computed data, complex queries, side effects, bulk operations

**Schema Endpoint:** All CrudRouter-based endpoints automatically include a `/$schema` collection operation that returns the Pydantic JSON schema for the output type. This is useful for documentation, validation, and code generation.

## API Responses

**Strategy:**
1. Simple operations (`GET /config/{id}`) return pure objects
2. Collections support optional pagination (`?page=1&size=20`)
3. Errors follow RFC 9457 with URN identifiers
4. Custom operations use typed models (BulkOperationResult, etc.)

**Pagination (opt-in):**
```python
# Without: returns list
GET /api/v1/config/

# With: returns PaginatedResponse
GET /api/v1/config/?page=1&size=20
```

**Error Handling (RFC 9457):**
```python
from chapkit.core.exceptions import NotFoundError, InvalidULIDError, ValidationError, ConflictError

if not config:
    raise NotFoundError(f"Config {id} not found", instance=f"/api/v1/config/{id}")
```

**URN Types:** `not-found` (404), `invalid-ulid` (400), `validation-failed` (400), `conflict` (409), `unauthorized` (401), `forbidden` (403)

## Structured Logging

Enable: `.with_logging()` in ServiceBuilder. Env vars: `LOG_FORMAT` (console/json), `LOG_LEVEL` (DEBUG/INFO/etc)

```python
from chapkit.core.logging import get_logger

logger = get_logger(__name__)
logger.info("processing_config", config_name="prod", version=2)  # Structured fields, snake_case events
```

Features: Auto request tracing with ULID request IDs, `X-Request-ID` response headers, context binding

## Database & Migrations

**Automatic migrations:**
- File DBs: Run Alembic migrations automatically on `Database.init()`
- In-memory: Skip migrations (fast tests)

**Connection pooling:**
Configure connection pool settings for production deployments:

```python
# Default pool settings (suitable for most applications)
app = ServiceBuilder(info=info).with_database("sqlite+aiosqlite:///./app.db").build()

# Custom pool settings for high-concurrency scenarios
app = (
    ServiceBuilder(info=info)
    .with_database(
        "sqlite+aiosqlite:///./app.db",
        pool_size=20,          # Number of connections to maintain (default: 5)
        max_overflow=40,       # Max overflow connections beyond pool_size (default: 10)
        pool_recycle=1800,     # Recycle connections after seconds (default: 3600)
        pool_pre_ping=True,    # Test connections before use (default: True)
    )
    .build()
)

# Or configure Database directly
from chapkit.core import Database
db = Database(
    "sqlite+aiosqlite:///./app.db",
    pool_size=20,
    max_overflow=40,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```

**SqliteDatabaseBuilder (recommended):**
Cleaner, type-safe database configuration with builder pattern:

```python
from chapkit.core import SqliteDatabaseBuilder

# In-memory database for development/testing
db = SqliteDatabaseBuilder.in_memory().build()

# File-based database with default settings
db = SqliteDatabaseBuilder.from_file("app.db").build()

# Production configuration with custom pool settings
db = (
    SqliteDatabaseBuilder.from_file("app.db")
    .with_pool(size=20, max_overflow=40, recycle=1800)
    .with_echo(False)
    .build()
)

# Use with ServiceBuilder
app = (
    ServiceBuilder(info=info)
    .with_database_instance(SqliteDatabaseBuilder.from_file("app.db").build())
    .with_health()
    .build()
)
```

**Pool parameters:**
- `pool_size`: Number of connections to maintain in the pool (default: 5)
- `max_overflow`: Maximum overflow connections beyond pool_size (default: 10)
- `pool_recycle`: Recycle connections after this many seconds (default: 3600)
- `pool_pre_ping`: Test connections before using them (default: True, recommended)

**Create migration:**
```bash
make migrate MSG='add_user_table'  # or: uv run alembic revision --autogenerate -m "..."
make upgrade                        # or: uv run alembic upgrade head
```

**Workflow:**
1. Modify ORM models in `src/chapkit/modules/*/models.py`
2. Generate: `make migrate MSG='description'`
3. Review in `alembic/versions/`
4. Restart app (auto-applies)
5. Commit migration file

## Using Chapkit as a Library

**Installation:** `uv add chapkit`

**Custom Entity (full vertical slice):**
```python
from chapkit.core import Entity, EntityIn, EntityOut, BaseRepository, BaseManager
from chapkit.core.api import CrudRouter
from chapkit.core.api.dependencies import get_session
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from ulid import ULID

# 1. ORM Model
class User(Entity):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str]

# 2. Schemas
class UserIn(EntityIn):
    username: str
    email: str

class UserOut(EntityOut):
    username: str
    email: str

# 3. Repository
class UserRepository(BaseRepository[User, ULID]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

# 4. Manager
class UserManager(BaseManager[User, UserIn, UserOut, ULID]):
    def __init__(self, repo: UserRepository) -> None:
        super().__init__(repo, User, UserOut)

# 5. Dependency
def get_user_manager(session=Depends(get_session)) -> UserManager:
    return UserManager(UserRepository(session))

# 6. Router (auto CRUD endpoints)
user_router = CrudRouter.create(
    prefix="/api/v1/users",
    tags=["users"],
    entity_in_type=UserIn,
    entity_out_type=UserOut,
    manager_factory=get_user_manager,
)

# 7. Build app
from chapkit.api import ServiceBuilder, ServiceInfo
app = ServiceBuilder(info=ServiceInfo(display_name="My App")).with_health().include_router(user_router).build()
```

**Alembic migrations:**
```python
# alembic/env.py - import your models to include in migrations
from chapkit.core.models import Base
from my_service.models import User
target_metadata = Base.metadata
```

## Creating a New Module

To add a new domain module to chapkit (e.g., `notification`):

**1. Create module directory structure:**
```bash
mkdir -p src/chapkit/modules/notification
touch src/chapkit/modules/notification/{__init__.py,models.py,schemas.py,repository.py,manager.py,router.py}
```

**2. Define ORM model (`models.py`):**
```python
"""ORM models for notification entities."""
from chapkit.core.models import Entity
from sqlalchemy.orm import Mapped, mapped_column

class Notification(Entity):
    """Notification model for user alerts."""
    __tablename__ = "notifications"
    message: Mapped[str]
    read: Mapped[bool] = mapped_column(default=False)
```

**3. Define schemas (`schemas.py`):**
```python
"""Pydantic schemas for notification validation."""
from chapkit.core.schemas import EntityIn, EntityOut

class NotificationIn(EntityIn):
    """Input schema for creating notifications."""
    message: str
    read: bool = False

class NotificationOut(EntityOut):
    """Output schema for notification responses."""
    message: str
    read: bool
```

**4. Define repository (`repository.py`):**
```python
"""Repository for notification data access."""
from chapkit.core.repository import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID
from .models import Notification

class NotificationRepository(BaseRepository[Notification, ULID]):
    """Repository for notification CRUD operations."""
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Notification)
```

**5. Define manager (`manager.py`):**
```python
"""Manager for notification business logic."""
from chapkit.core.manager import BaseManager
from ulid import ULID
from .models import Notification
from .repository import NotificationRepository
from .schemas import NotificationIn, NotificationOut

class NotificationManager(BaseManager[Notification, NotificationIn, NotificationOut, ULID]):
    """Manager for notification operations with lifecycle hooks."""
    def __init__(self, repo: NotificationRepository) -> None:
        super().__init__(repo, Notification, NotificationOut)
```

**6. Define router (`router.py`):**
```python
"""REST API router for notification endpoints."""
from chapkit.core.api.crud import CrudRouter
from .schemas import NotificationIn, NotificationOut

class NotificationRouter(CrudRouter[NotificationIn, NotificationOut]):
    """Router with auto-generated CRUD endpoints for notifications."""
    pass
```

**7. Export from `__init__.py`:**
```python
"""Notification module - user alerts and messaging."""
from .models import Notification
from .schemas import NotificationIn, NotificationOut
from .repository import NotificationRepository
from .manager import NotificationManager
from .router import NotificationRouter

__all__ = [
    "Notification",
    "NotificationIn",
    "NotificationOut",
    "NotificationRepository",
    "NotificationManager",
    "NotificationRouter",
]
```

**8. Create migration:**
```bash
make migrate MSG='add notification module'
```

**9. Use in ServiceBuilder:**
```python
from chapkit.api import ServiceBuilder, ServiceInfo
from chapkit.modules.notification import NotificationRouter, NotificationIn, NotificationOut

def get_notification_manager(session=Depends(get_session)):
    from chapkit.modules.notification import NotificationRepository, NotificationManager
    return NotificationManager(NotificationRepository(session))

app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .include_router(NotificationRouter.create(
        prefix="/api/v1/notifications",
        tags=["notifications"],
        entity_in_type=NotificationIn,
        entity_out_type=NotificationOut,
        manager_factory=get_notification_manager,
    ))
    .build()
)
```

## Dependency Management

**Always use `uv`:**
```bash
uv add <package>          # Runtime dependency
uv add --dev <package>    # Dev dependency
uv add <package>@latest   # Update specific
uv lock --upgrade         # Update all
```

**Never manually edit `pyproject.toml`**

## Docker

Quick: `make docker-build && make docker-run EXAMPLE=config_api`

Env vars: `EXAMPLE_MODULE` (module:app), `PORT` (8000), `WORKERS` (auto), `LOG_FORMAT` (console/json), `LOG_LEVEL` (INFO)

## Code Quality

**Standards:**
- Python 3.13+, line length 120, type annotations required
- Double quotes, async/await, conventional commits
- Class order: public → protected → private
- `__all__` declarations should only be used in `__init__.py` files

**Documentation Requirements:**
- **Every Python file** must have a one-line docstring at the top explaining what the file does
- **Every class** must have a one-line docstring explaining what the class does
- **Every method/function** must have a one-line docstring explaining what the method does
- Use triple quotes (`"""docstring"""`) for all docstrings
- Keep docstrings concise - one line is preferred, expand only when necessary

**Example:**
```python
"""Service manager for handling user authentication."""

class AuthManager:
    """Manager for user authentication and session handling."""

    def authenticate(self, credentials: Credentials) -> Token:
        """Authenticate user and return access token."""
        pass
```

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

## Key Dependencies

- sqlalchemy[asyncio] >= 2.0
- aiosqlite >= 0.21
- pydantic >= 2.11
- fastapi, ulid-py

## Git Workflow

**All changes must go through the branch + PR workflow.**

### Branch Naming
- `feature/description` - New features
- `fix/description` - Bug fixes
- `chore/description` - Maintenance tasks
- `docs/description` - Documentation updates
- `github/description` - GitHub-specific changes

### Process
1. Create a new branch from `main`: `git checkout -b feature/my-feature`
2. Make your changes and commit: `git commit -m "feat: add new feature"`
3. Push to GitHub: `git push -u origin feature/my-feature`
4. Create a PR via GitHub CLI: `gh pr create --title "..." --body "..."`
5. Wait for manual review and merge

### Commit Messages
Follow conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `chore:` - Maintenance
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring

### PR Requirements
- All tests must pass (`make test`)
- All linting must pass (`make lint`)
- Code coverage should not decrease
- Descriptive PR title and body
