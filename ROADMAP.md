# Chapkit Roadmap

This document outlines the development phases for chapkit, tracking completed work and planned future enhancements.

## Project Status

**Current Version:** 1.0.0
**Architecture:** Vertical slice with framework-agnostic core, FastAPI layer, and domain modules
**Primary Models:** Config, Artifact, Task, ML

---

## ✅ Completed Phases

### Phase 0: Core Infrastructure
**Status:** Complete
**Key Commits:** `6d792f5`, `028ae35`, `28823b0`

**Delivered:**
- Framework-agnostic core layer
  - Database with automatic Alembic migrations
  - Entity ORM base classes
  - Repository pattern with BaseRepository
  - Manager pattern with BaseManager
  - Structured logging with request tracing
  - JobScheduler for async operations
- FastAPI framework layer
  - Router base class with fluent API
  - CrudRouter with auto-generated CRUD endpoints
  - Schema endpoints (`/$schema`) for Pydantic schema introspection
  - Error handlers (RFC 9457 compliance)
  - Middleware (logging, error handling)
  - Pagination helpers
  - BaseServiceBuilder for core-only usage
- API versioning
  - All endpoints use `/api/v1/` prefix for future version management
  - Default prefixes configurable in ServiceBuilder methods

### Phase 1: Domain Modules
**Status:** Complete
**Key Commits:** Multiple

**Config Module:**
- Key-value config storage with JSON payloads
- BaseConfig schema validation
- Generic ConfigManager with type safety
- Full CRUD API endpoints

**Artifact Module:**
- Hierarchical artifact trees
- Level-based organization
- ArtifactHierarchy for structure validation
- Optional config linking
- Tree operations (`$tree` endpoint)

**Task Module:**
- Script execution templates
- Bash/shell script runner
- Async job execution
- Output capture and storage
- Task execution endpoint (`$execute`)

### Phase 2: ML Module
**Status:** Complete
**Key Commits:** `0fe13ce`, `6e980fb`, `428b882`, `37a0cfe`, `9442333`, `df21acb`

**Delivered:**
- Complete ML train/predict workflow
- Artifact-based model storage with lineage
- Job scheduler integration for async operations
- Three ModelRunner implementations:
  - **FunctionalModelRunner** - Functional style with async callbacks (now generic over ConfigT)
  - **BaseModelRunner** - Class-based with lifecycle hooks (on_init, on_cleanup)
  - **ShellModelRunner** - Language-agnostic via external scripts
- MLServiceBuilder for reduced boilerplate (7 calls → 2)
- MLServiceInfo with extended metadata:
  - Author attribution and notes
  - AssessedStatus enum (gray/red/orange/yellow/green)
  - Organization details with logo
  - Citation information
- REST API endpoints:
  - `POST /api/v1/ml/$train` - Async model training
  - `POST /api/v1/ml/$predict` - Async predictions
- Full test coverage with functional, class-based, and shell examples
- Example applications showcase MLServiceInfo usage with maturity assessment
- **Comprehensive API Documentation:**
  - Complete cURL guides for all three ML examples (`ml_basic.md`, `ml_class.md`, `ml_shell.md`)
  - Quick reference guides (`README.md`, `quick_reference.md`)
  - Sample datasets with real ULIDs for reproducibility
  - Error handling and troubleshooting sections
- **Postman Collection v2.1 JSON files:**
  - Import-ready collections for all ML examples
  - Auto-capture variables via test scripts
  - Pre-configured with example responses
  - Import/usage guide (`POSTMAN.md`)
  - Collection Runner compatible for automated testing

### Phase 3: Documentation Infrastructure
**Status:** Complete
**Key PR:** [#2](https://github.com/winterop-com/chapkit/pull/2)

**Delivered:**
- **MkDocs with Material Theme:**
  - Modern, responsive documentation site
  - Instant search across all pages
  - Navigation tabs for major sections
  - Dark/light mode toggle
  - Code copy buttons and syntax highlighting
  - Mermaid diagram support
  - Mobile responsive design
- **Documentation Structure (9 Major Sections):**
  - Getting Started (installation, quickstart, first service)
  - Architecture (core/API layers, modules, dependency flow)
  - Service Builders (BaseServiceBuilder, ServiceBuilder, MLServiceBuilder)
  - Modules (config, artifacts, tasks, ML)
  - ML Workflows (functional, class-based, shell-based runners)
  - API Reference (endpoints, schemas, pagination, errors, operations)
  - Guides (custom entities/routers, modules, migrations, testing, Docker)
  - Advanced (logging, hooks, job scheduler, library usage)
  - Contributing (development, code quality, git workflow)
- **Infrastructure:**
  - GitHub Actions workflow for deployment
  - Makefile commands (`make docs`, `make docs-serve`, `make docs-build`)
  - Custom CSS for API method badges
  - Abbreviations and snippets support
- **Content Strategy:**
  - CLAUDE.md remains as comprehensive single-file reference for AI assistants
  - MkDocs site provides browsable, searchable interface for human developers
  - 50+ documentation pages (index pages + stubs for future expansion)

**Next Steps:**
- **Phase 3.1:** Expand Getting Started section with complete tutorials
- **Phase 3.2:** Migrate ML workflow examples from `examples/docs/` to documentation site
- **Phase 3.3:** Add architecture diagrams (Mermaid) to architecture section
- **Phase 3.4:** Complete API Reference with detailed endpoint documentation
- **Phase 3.5:** Migrate content from CLAUDE.md into organized documentation pages
- **Phase 3.6:** Add video tutorials and interactive examples
- **Phase 3.7:** Configure public documentation hosting (GitHub Pages, ReadTheDocs, or alternative)

---

## 🎯 Planned Phases

### Phase 4: Enhanced Landing Page for ML Services
**Status:** Proposed
**Priority:** Medium

**Goals:**
- Create ML-specific landing page template
- Improve discoverability and documentation
- Visual model status communication

**Features:**
- Display model metadata (author, version, assessment status)
- Show training/prediction examples with code snippets
- Auto-generated API documentation
- Citation information and model cards
- Visual status indicators with color coding
- Link to OpenAPI/Swagger docs

**Integration:**
- Extend `.with_landing_page()` method
- New template: `ml_landing_page.html`
- Auto-detect MLServiceInfo vs ServiceInfo
- Conditional rendering based on metadata availability

**Technical Notes:**
- Use existing `landing_page.html` as base
- Add Jinja2 templating for dynamic content
- Include minimal CSS for professional appearance
- Make it responsive for mobile/desktop

---

### Phase 5: Authentication & Authorization Module
**Status:** Proposed
**Priority:** High

**Goals:**
- Secure API endpoints
- User management
- Fine-grained access control

**Features:**
- User/session management (new `auth` module)
- API key authentication
- JWT token support
- Role-based access control (RBAC)
- Permission system (read/write/admin)
- OAuth2 integration (optional)

**Integration:**
- `.with_auth(strategy, permissions)` method on ServiceBuilder
- Dependency injection for authentication
- Per-endpoint permission decorators
- CrudPermissions extended with user context

**Technical Notes:**
- Follow vertical slice pattern (models, schemas, repository, manager, router)
- Use FastAPI security utilities
- Support multiple auth strategies
- Session management with database or Redis

**API Design:**
```python
app = (
    ServiceBuilder(info=info)
    .with_auth(
        strategy=APIKeyAuth(),
        permissions={"ml:train": ["admin"], "ml:predict": ["user", "admin"]}
    )
    .with_ml(runner)
    .build()
)
```

---

### Phase 6: Rate Limiting & Throttling
**Status:** Proposed
**Priority:** Medium

**Goals:**
- Prevent abuse and overload
- Fair resource allocation
- Cost control for expensive operations

**Features:**
- Per-user rate limits (requests/minute, requests/hour)
- Per-endpoint throttling
- Queue management for ML operations
- Backpressure handling
- Quota system with reset windows
- 429 Too Many Requests responses

**Integration:**
- `.with_rate_limiting(limits)` method
- Middleware-based implementation
- Integration with auth module for user identification
- Configurable limits per endpoint

**Technical Notes:**
- Use Redis or in-memory store for counters
- Token bucket or sliding window algorithm
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

**API Design:**
```python
app = (
    ServiceBuilder(info=info)
    .with_rate_limiting(
        default_limits=["100/minute", "1000/hour"],
        endpoint_limits={
            "/api/v1/ml/$train": ["10/hour", "50/day"],
            "/api/v1/ml/$predict": ["100/minute"]
        }
    )
    .build()
)
```

---

### Phase 7: Model Registry & Versioning
**Status:** Proposed
**Priority:** High

**Goals:**
- Semantic versioning for models
- A/B testing and comparison
- Rollback capabilities
- Deployment workflows

**Features:**
- Model versioning (semver: major.minor.patch)
- Model aliases (latest, stable, canary)
- Version comparison API
- Rollback to previous versions
- Lineage tracking (config + data → model → predictions)
- Promotion workflow (dev → staging → prod)
- Model tags and labels

**Integration:**
- Extend Artifact module with versioning
- New endpoints:
  - `GET /api/v1/models` - List all models with versions
  - `GET /api/v1/models/{name}/versions` - List versions
  - `POST /api/v1/models/{name}/versions/{version}/$promote` - Promote to alias
  - `POST /api/v1/models/{name}/versions/{version}/$rollback` - Rollback
- MLServiceBuilder automatically creates registry

**Technical Notes:**
- Use artifact hierarchy for version storage
- Immutable model artifacts
- Metadata includes training timestamp, metrics, config snapshot
- Support for model comparison (diff metrics)

---

### Phase 8: Monitoring & Observability
**Status:** Proposed
**Priority:** Medium

**Goals:**
- Production readiness
- Performance monitoring
- Issue detection and debugging

**Features:**
- Metrics collection (Prometheus/OpenTelemetry)
- Model performance monitoring (accuracy, latency, throughput)
- Data drift detection
- Request/response sampling
- Distributed tracing integration
- Custom health checks
- Alerting integration

**Integration:**
- `.with_monitoring(provider)` method
- Prometheus endpoint: `/metrics`
- OpenTelemetry auto-instrumentation
- Extend health checks with model-specific checks

**Metrics to Track:**
- Request count, latency, error rate
- Model prediction latency
- Training job duration and status
- Queue depth and processing rate
- Database query performance
- Memory and CPU usage

**Technical Notes:**
- Use prometheus-client or opentelemetry-python
- Middleware for automatic request instrumentation
- Optional Grafana dashboard templates

---

### Phase 9: Batch Processing
**Status:** Proposed
**Priority:** Low

**Goals:**
- Efficient bulk operations
- Large dataset processing
- Cost optimization

**Features:**
- Batch train/predict endpoints
- Bulk job scheduling
- Progress tracking for long-running operations
- Result aggregation and export
- Chunked processing with checkpoints
- Resume capability for interrupted jobs

**Integration:**
- New endpoints:
  - `POST /api/v1/ml/$batch-train` - Train multiple models
  - `POST /api/v1/ml/$batch-predict` - Bulk predictions
- Progress tracking via jobs API
- CSV/JSON bulk input formats

**Technical Notes:**
- Use job scheduler for orchestration
- Stream processing for large datasets
- Optional: Integration with Celery or Apache Airflow
- Export results to S3/blob storage

---

### Phase 10: Model Serving Optimization
**Status:** Proposed
**Priority:** Medium

**Goals:**
- Reduce latency
- Improve throughput
- Resource efficiency

**Features:**
- Model preloading and caching
- Connection pooling for database
- Response caching with TTL
- Warmup routines on startup
- Request batching for inference
- Model compilation/optimization
- GPU support detection

**Integration:**
- ServiceBuilder options for optimization
- Automatic detection of optimization opportunities
- Configurable cache strategies

**Technical Notes:**
- Use pickle caching for frequently accessed models
- Redis for distributed response caching
- ONNX runtime for optimized inference
- Optional: TorchScript, TensorRT support

**API Design:**
```python
app = (
    MLServiceBuilder(info=info, runner=runner)
    .with_optimization(
        model_cache_size=10,
        response_cache_ttl=300,
        warmup_models=["latest", "stable"]
    )
    .build()
)
```

---

### Phase 11: API Discovery & SDK Generation
**Status:** Proposed
**Priority:** Low

**Goals:**
- Enhanced API discoverability
- Client library generation
- Developer experience improvements

**Features:**
- Auto-generated model cards from MLServiceInfo
- Enhanced OpenAPI schemas with comprehensive examples
- SDK generation (Python, TypeScript, R clients)
- GraphQL API option as alternative to REST
- Automated changelog generation from commits
- Version-specific migration guides

**Integration:**
- CLI tools for SDK generation: `chapkit generate-sdk --language python`
- Enhanced `/api/v1/info` endpoint with rich metadata
- Model card templates using Jinja2
- OpenAPI extensions for ML-specific metadata (training data requirements, input/output schemas)

**Technical Notes:**
- Use pydantic for automatic schema extraction
- Jinja2 templates for model cards with markdown export
- OpenAPI generator for multi-language SDK creation
- GraphQL schema auto-generation from existing models
- Separate from Phase 3 (MkDocs documentation) - focuses on programmatic API access

---

## Contributing

This roadmap is a living document. Phases may be reordered, merged, or split based on:
- User feedback and feature requests
- Technical dependencies and blockers
- Community contributions
- Production deployment learnings

To propose a new phase or modification:
1. Open an issue with the `roadmap` label
2. Describe the problem/opportunity
3. Propose a solution with technical approach
4. Discuss integration points and dependencies

---

## Notes

- **Phase Priority Levels:**
  - **High** - Critical for production ML services
  - **Medium** - Valuable enhancements, nice-to-have
  - **Low** - Future improvements, optional features

- **Architectural Principles:**
  - Maintain vertical slice architecture
  - Core remains framework-agnostic
  - Modules are self-contained with clear boundaries
  - Builder pattern for fluent configuration
  - Opt-in features with sensible defaults

- **Testing Requirements:**
  - All phases require comprehensive test coverage
  - Integration tests for cross-module features
  - Performance benchmarks for optimization features
  - Example applications demonstrating usage
