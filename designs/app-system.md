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
2. ✅ Apps cannot mount at `/` (conflicts with `.with_landing_page()`)
3. ✅ No prefix conflicts between apps
4. ✅ Prefix must start with `/`
5. ✅ Prefix cannot contain `..` or path traversal attempts
6. ✅ App directory must exist and contain `manifest.json`
7. ✅ Manifest must be valid JSON matching schema

**Important**: Apps mounted at `/` will intercept ALL routes, including API endpoints. For this reason, root-mounted apps are not supported. Use `.with_landing_page()` for the service landing page instead.

**Mount order:**

1. Core routers (health, system, metrics)
2. Module routers (config, artifacts, tasks, ML)
3. **Apps** ← mounted here
4. Custom routers (`.include_router()`)
5. Landing page (if enabled)

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

1. **Path Traversal**: Pydantic validator rejects `..` in prefixes
2. **Manifest Validation**: All manifest fields validated via Pydantic
3. **File Access**: StaticFiles handles path traversal prevention automatically
4. **API Protection**: `/api/**` prefix explicitly blocked
5. **Error Handling**: Invalid manifests fail fast during build, not at runtime
6. **Package Validation**: `importlib.util.find_spec()` safely resolves package locations

### Open Questions

1. Should `.with_apps()` fail if directory doesn't exist, or create it?
   - **Recommendation**: Fail fast (consistency with other validation)

2. Should apps have access to service metadata (ServiceInfo)?
   - **Recommendation**: Yes, via existing `/api/v1/info` endpoint

3. ~~Should we migrate `.with_landing_page()` to use the app system internally?~~
   - **Decision**: No. Root-mounted apps intercept all routes. Landing page stays as endpoint.

## Design Decision: No Root-Mounted Apps

After implementation and testing, we discovered that mounting apps at `/` with StaticFiles causes them to intercept ALL routes, including API endpoints. This breaks the fundamental design where APIs should always be accessible.

**Decision**: Apps cannot be mounted at `/`. The existing `.with_landing_page()` remains as an endpoint (not an app mount) to avoid this issue.

**Rationale**:
- FastAPI/Starlette mounts catch ALL traffic under their prefix
- A mount at `/` intercepts everything, including `/api/**` routes
- Routers registered before mounts still get intercepted for 404 responses
- This would break the core promise that `/api/**` is reserved for APIs

**Alternative considered**: Mount apps before routers - rejected because it's confusing and breaks the design principle that APIs have priority.

## Future Enhancements

1. **App Metadata Endpoint**: `GET /api/v1/system/apps` listing installed apps
2. **Hot Reload**: Watch app directories and reload on change (development mode)
3. **App Assets CDN**: Optional CDN integration for static assets
4. **App Dependencies**: Declare app dependencies in manifest (e.g., requires specific API version)
5. **App Permissions**: Fine-grained control over which API endpoints each app can access
6. **Package App Discovery**: `.with_apps(("mypackage", "apps"))` to auto-discover bundled apps

## References

- FastAPI StaticFiles: https://fastapi.tiangolo.com/tutorial/static-files/
- Starlette Mount: https://www.starlette.io/routing/#mount-routes
- Landing page implementation: `src/chapkit/core/api/service_builder.py:593`
