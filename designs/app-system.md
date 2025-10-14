# Design Document: App System

**Status**: Draft
**Author**: Morten Hansen
**Created**: 2025-10-14
**Last Updated**: 2025-10-14

## Overview

This document describes the design for an app hosting system in chapkit that allows mounting static web applications (HTML/JS/CSS) at configurable URL prefixes within a FastAPI service.

## Motivation

Chapkit services currently support:
- Dynamic API endpoints (via routers)
- Single static landing page (via `.with_landing_page()`)

However, users need to host complete web applications (dashboards, admin panels, documentation sites) alongside their APIs. The app system provides this capability while maintaining framework integration and safety constraints.

## Goals

1. **Simple Integration**: Apps should integrate via ServiceBuilder fluent API
2. **Convention-based**: Minimal configuration via manifest.json
3. **Safe by Default**: Prevent conflicts with API routes and other apps
4. **Flexible Mounting**: Apps can mount at any prefix except `/api/**`
5. **External Storage**: Apps stored outside package for easy customization

## Non-Goals

1. Server-side rendering or templating (apps are static only)
2. Dynamic asset generation or compilation
3. App lifecycle management (start/stop individual apps)
4. Inter-app communication or shared state
5. App authentication separate from service-level auth

## Design

### App Structure

Each app is a directory containing:

```
my-app/
├── manifest.json    # Required: app metadata + configuration
├── index.html       # Required: entry point (configurable)
├── style.css        # Optional: assets
├── script.js        # Optional: assets
└── assets/          # Optional: subdirectories
    └── logo.png
```

### Manifest Schema

```json
{
  "name": "Dashboard",
  "version": "1.0.0",
  "prefix": "/dashboard",
  "description": "Interactive data dashboard",
  "author": "John Doe",
  "entry": "index.html"
}
```

**Fields:**
- `name` (required, string): Human-readable app name
- `version` (required, string): Semantic version
- `prefix` (required, string): URL prefix (must start with `/`, cannot be `/api/**`)
- `description` (optional, string): App description
- `author` (optional, string): Author name
- `entry` (optional, string): Entry point filename, defaults to `index.html`

### Storage Location

**Decision: External directory (not in package)**

Apps will be stored outside the `chapkit` package:

1. **Customization**: Users can modify apps without rebuilding the package
2. **Separation**: Apps are plugins/extensions, not core framework code
3. **Deployment**: Apps can be deployed/updated independently
4. **Architecture**: Aligns with vertical slice principle (core stays framework-agnostic)

**Path Resolution**: Apps can be loaded from two sources:

1. **Filesystem paths** (relative to current working directory)
2. **Package resources** (bundled with Python packages)

**Typical Project Structure**:
```
myproject/
├── apps/                    # App directory
│   ├── dashboard/
│   │   ├── manifest.json
│   │   └── index.html
│   └── admin/
│       ├── manifest.json
│       └── index.html
├── main.py                  # ServiceBuilder code
├── pyproject.toml
└── uv.lock
```

**Path Examples**:
- Relative paths: `.with_app("./apps/dashboard")` or `.with_app("apps/dashboard")`
- Absolute paths: `.with_app("/opt/myproject/apps/dashboard")`
- Package resources: `.with_app(("chapkit.core.api", "apps/landing"))`
- Auto-discovery: `.with_apps("./apps")` discovers all apps in directory

**Package Resource Format**: Uses tuple `(package_name, path_within_package)`
- Example: `.with_app(("chapkit.core.api", "apps/landing"))` - bundled with chapkit
- Example: `.with_app(("mycompany.apps", "dashboard"))` - third-party package app
- Internally uses `importlib.util.find_spec()` to locate package, then resolves path

### ServiceBuilder API

```python
from chapkit.api import ServiceBuilder, ServiceInfo

app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_health()

    # Option 1: Register single app from filesystem (reads prefix from manifest)
    .with_app("apps/dashboard")

    # Option 2: Override prefix
    .with_app("apps/admin", prefix="/custom")

    # Option 3: Auto-discover apps from directory
    .with_apps("apps")  # Scans for subdirs with manifest.json

    # Option 4: Use bundled package app (replaces .with_landing_page())
    .with_app(("chapkit.core.api", "apps/landing"), prefix="/")

    .build()
)
```

**Notes**:
- Filesystem paths (strings) are relative to the current working directory
- Package resources (tuples) use format `(package_name, path_within_package)`
- Type signature: `with_app(path: str | tuple[str, str], prefix: str | None = None)`

### Mount Rules & Validation

**Validation rules (fail fast during `build()`):**

1. ✅ Apps cannot mount at `/api/**` (reserved for API routes)
2. ✅ Duplicate prefixes use "last wins" semantics (later calls override earlier ones)
3. ✅ Prefix must start with `/`
4. ✅ Prefix cannot contain `..` or path traversal attempts
5. ✅ App directory must exist and contain `manifest.json`
6. ✅ Manifest must be valid JSON matching schema

**Important**: Root apps (`prefix="/"`) ARE fully supported. `.with_landing_page()` internally mounts a built-in app at `/`, which can be overridden by calling `.with_app(..., prefix="/")` afterward.

**Mount order in `build()`:**

1. Core routers (health, system, metrics)
2. Module routers (config, artifacts, tasks, ML)
3. Custom routers (`.include_router()`)
4. Route endpoints (info endpoint, landing page)
5. **Apps** ← mounted here (after all routes)
6. Dependency overrides

**Why this order matters**: FastAPI/Starlette matches routes before mounts. By registering all routes (routers + endpoints) before mounting apps, we ensure API routes take precedence. Apps act as catch-all for unmatched paths.

### Implementation Overview

#### New Files

- `src/chapkit/core/api/app.py` - AppManifest, App, AppLoader classes
- `tests/test_app_loader.py` - Unit tests for app loading
- `tests/test_service_builder_apps.py` - Integration tests
- `examples/apps/sample-dashboard/` - Example app
- `examples/app_hosting_api.py` - Demo service

#### Modified Files

- `src/chapkit/core/api/service_builder.py` - Add `.with_app()` and `.with_apps()` methods
- `src/chapkit/core/api/__init__.py` - Export new classes

### Technical Implementation

**Path Resolution via StaticFiles**:

Chapkit leverages Starlette's `StaticFiles` class which supports both filesystem and package resources:

```python
# Filesystem app
StaticFiles(directory="/path/to/app", html=True)

# Package app (uses importlib to locate package)
StaticFiles(packages=[("mypackage", "apps/dashboard")], html=True)
```

The `html=True` parameter enables SPA-style routing (serves `index.html` for directory requests).

**App Loading Process**:
1. Parse path: detect string (filesystem) vs tuple (package)
2. Resolve to directory: `Path.resolve()` or `importlib.util.find_spec()`
3. Load and validate `manifest.json` from resolved directory
4. Create `StaticFiles` instance with `html=True`
5. Mount via `app.mount(prefix, static_files_instance)`

**Package Resolution Example**:
```python
import importlib.util

# For ("chapkit.core.api", "apps/landing")
spec = importlib.util.find_spec("chapkit.core.api")
# spec.origin = "/path/to/site-packages/chapkit/core/api/__init__.py"
app_dir = Path(spec.origin).parent / "apps/landing"
# app_dir = "/path/to/site-packages/chapkit/core/api/apps/landing"
```

### Security Considerations

**Path Traversal Protection** (implemented 2025-10-14):

1. **Prefix Field**: Pydantic validator rejects `..` in mount prefixes
2. **Entry Field**: Pydantic validator rejects:
   - Path traversal patterns (`..`)
   - Absolute paths (must be relative to app directory)
   - Normalized traversal attempts (e.g., `subdir/../../etc/passwd`)
3. **Package Subpath**: Pre-validation before path joining:
   - Rejects `..` in subpath parameter
   - Rejects absolute paths
   - Post-join verification: ensures resolved path stays within package directory using `relative_to()`

**Validation & Error Handling**:

4. **Strict Schema**: `extra="forbid"` in AppManifest catches typos and unknown fields
5. **JSON Errors**: Wrapped in helpful `ValueError` with context
6. **Fail Fast**: All validation happens during `build()`, not at runtime
7. **API Protection**: `/api/**` prefix explicitly blocked for apps

**Runtime Safety**:

8. **StaticFiles**: Starlette's StaticFiles class provides additional path traversal protection
9. **Package Resolution**: `importlib.util.find_spec()` safely locates packages without user-controlled imports

**Test Coverage**: 27 unit tests including 7 dedicated security tests covering all path traversal attack vectors

### Open Questions

1. Should `.with_apps()` fail if directory doesn't exist, or create it?
   - **Recommendation**: Fail fast (consistency with other validation)

2. Should apps have access to service metadata (ServiceInfo)?
   - **Recommendation**: Yes, via existing `/api/v1/info` endpoint

3. ~~Should we migrate `.with_landing_page()` to use the app system internally?~~
   - **Decision**: Yes. Landing page is now implemented as a built-in app at `/`.

## Design Decision: Landing Page as App + Override Semantics

**Decision**: `.with_landing_page()` internally mounts a built-in app at `/`. Duplicate prefixes use "last wins" semantics.

**Rationale**:
- Simplifies implementation - single code path for all static content
- Enables customization - users can override landing page by calling `.with_app(..., prefix="/")` after
- Consistent with user expectations - later configuration overrides earlier
- FastAPI/Starlette routes still take precedence over all mounts

**Implementation**:
1. `.with_landing_page()` calls `.with_app(("chapkit.core.api", "apps/landing"))`
2. Built-in landing page lives in `src/chapkit/core/api/apps/landing/`
3. Validation deduplicates apps with same prefix, keeping only the last one
4. Warning logged when an app overrides another (helps debugging)
5. Routes are registered before apps are mounted in `build()`

**Override Examples**:
```python
# Use built-in landing page
.with_landing_page()

# Override landing page with custom app
.with_landing_page()
.with_app("my-custom-landing", prefix="/")  # Replaces built-in

# Override any app
.with_app("apps/dashboard")
.with_app("apps/better-dashboard", prefix="/dashboard")  # Replaces first
```

**Known Limitation**:
Root mounts catch requests that would normally trigger FastAPI's trailing slash redirect. This means `/api/v1/configs/` (with slash) returns 404 if the actual route is `/api/v1/configs` (no slash). Users should use exact paths.

## Implemented Features

### App Metadata Endpoint (implemented 2025-10-14)

**Endpoint**: `GET /api/v1/system/apps`

Lists all installed apps with their metadata. Available when `.with_system()` is called on ServiceBuilder.

**Response Schema** (`AppInfo`):
```json
{
  "name": "Dashboard",
  "version": "1.0.0",
  "prefix": "/dashboard",
  "description": "Interactive data dashboard",
  "author": "John Doe",
  "entry": "index.html",
  "is_package": false
}
```

**Implementation**:
- `AppManager` class: Lightweight manager holding loaded app list
- Global dependency injection via `get_app_manager()` / `set_app_manager()`
- Initialized in `ServiceBuilder.build()` (always, even with no apps)
- New endpoint in `SystemRouter` at `/apps`

**Test Coverage**: 3 unit tests + 3 integration tests

### Package App Discovery (implemented 2025-10-14)

**Feature**: `.with_apps()` supports package resources for auto-discovering bundled apps

Auto-discover multiple apps from package resources using tuple format `(package_name, subpath)`.

**Usage Example**:
```python
# Discover all apps in mycompany.webapps/apps directory
.with_apps(("mycompany.webapps", "apps"))

# For package structure:
# mycompany/
#   webapps/
#     apps/
#       dashboard/
#         manifest.json
#         index.html
#       admin/
#         manifest.json
#         index.html
```

**Implementation**:
- `AppLoader.discover_apps()` detects tuple format and resolves package path
- Scans package subdirectories for `manifest.json` files
- Loads each discovered app using package resource loading
- All discovered apps marked with `is_package=True`
- Security: Path traversal protection for package subpaths

**Comparison with filesystem discovery**:
```python
# Filesystem discovery (relative to CWD)
.with_apps("./apps")

# Package discovery (bundled with Python package)
.with_apps(("mypackage", "apps"))
```

**Test Coverage**: 6 unit tests + 1 integration test

## Future Enhancements

1. **Hot Reload**: Watch app directories and reload on change (development mode)
3. **App Assets CDN**: Optional CDN integration for static assets
4. **App Dependencies**: Declare app dependencies in manifest (e.g., requires specific API version)
5. **App Permissions**: Fine-grained control over which API endpoints each app can access

## References

- FastAPI StaticFiles: https://fastapi.tiangolo.com/tutorial/static-files/
- Starlette Mount: https://www.starlette.io/routing/#mount-routes
- Landing page implementation: `src/chapkit/core/api/service_builder.py:593`
