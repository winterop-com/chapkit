# Chapkit Roadmap

This roadmap outlines planned features and improvements for Chapkit, organized by priority and category.

## Priority Levels

- **P0 (Critical)** - Core functionality gaps that limit production readiness
- **P1 (High Priority)** - Features that significantly improve usability and scalability
- **P2 (Medium Priority)** - Quality of life improvements and ecosystem features
- **P3 (Low Priority)** - Nice-to-haves that enhance developer experience
- **P4 (Future)** - Advanced features for specialized use cases

---

## 🔐 Authentication & Authorization

### P0 - API Key Authentication ✅ COMPLETED
- [x] API key middleware with header validation (`X-API-Key`)
- [x] `.with_auth()` method on ServiceBuilder
- [x] Environment variable support (default: `CHAPKIT_API_KEYS`)
- [x] Docker secrets file support (`api_key_file` parameter)
- [x] Direct key list support (for examples/dev only)
- [x] Configurable unauthenticated paths (health checks, docs)

### P1 - Enhanced API Key Features ✅ COMPLETED
- [x] Multiple keys support (comma-separated in env var)
- [x] Key prefix conventions and validation (`sk_env_random` format)
- [x] Secure key logging (mask all but prefix: `sk_prod_****`)
- [x] Key rotation support (multiple active keys during transition)
- [ ] Custom validator function support (for advanced use cases)

### P2 - Security Enhancements
- [ ] Rate limiting per API key
- [ ] Key scoping (whitelist/blacklist endpoints per key)
- [ ] Audit logging for authentication events
- [ ] Key expiration/TTL (via custom validator)
- [ ] IP allowlisting (via custom validator)
- [ ] Endpoint-level permission configuration (CrudPermissions)
- [ ] Input sanitization middleware
- [ ] Security headers middleware (CSP, HSTS, X-Frame-Options)
- [ ] CORS configuration improvements

### P2 - Documentation & Examples ✅ MOSTLY COMPLETED
- [x] Docker Compose with environment variables example
- [x] Docker secrets setup guide (Docker Compose & Swarm)
- [x] Kubernetes secrets integration example
- [x] Key rotation best practices documentation
- [ ] Security hardening guide (covered in authentication.md)
- [x] `.env.example` file patterns and gitignore setup

---

## 📊 Monitoring & Observability

### P1 - Core Monitoring
- [ ] Prometheus metrics endpoint (`/metrics`)
- [ ] Request/response duration histograms
- [ ] Active request gauges
- [ ] Error rate counters by endpoint
- [ ] Database connection pool metrics

### P1 - ML Monitoring
- [ ] Model performance metrics (accuracy, latency, throughput)
- [ ] Training job duration and success rate
- [ ] Prediction endpoint performance
- [ ] Model artifact storage size tracking

### P2 - Advanced Monitoring
- [ ] Data drift detection for ML inputs
- [ ] Request/response sampling for debugging
- [ ] Distributed tracing integration (OpenTelemetry)
- [ ] Custom health checks with thresholds
- [ ] Alerting integration (PagerDuty, Slack)
- [ ] `.with_monitoring()` method on ServiceBuilder

### P3 - Deep Observability
- [ ] Query performance profiling
- [ ] Memory usage tracking per endpoint
- [ ] Automatic anomaly detection
- [ ] Performance regression detection

---

## 🗄️ Database & Performance

### P0 - Production Database
- [ ] PostgreSQL support with asyncpg
- [x] Connection pooling configuration (min/max connections)
- [x] Database health checks with connection testing

### P1 - Performance Optimization
- [ ] Query result caching (Redis/in-memory)
- [ ] Bulk insert/update operations
- [ ] Lazy loading for relationships
- [ ] Read replica support
- [ ] Query optimization hints

### P2 - Advanced Database
- [ ] Multi-database support (sharding)
- [ ] Database connection retry logic with exponential backoff
- [ ] Transaction isolation level control
- [ ] Database migration rollback safety checks
- [ ] Automatic index suggestions based on queries

### P3 - Scalability
- [ ] Horizontal read scaling
- [ ] Database partitioning support
- [ ] Query result streaming for large datasets
- [ ] Prepared statement caching

---

## 🚀 API Features & Enhancements

### P1 - Essential API Features
- [ ] Filtering support (query params: `?name=foo&status=active`)
- [ ] Sorting support (`?sort=created_at:desc,name:asc`)
- [ ] Field selection/sparse fieldsets (`?fields=id,name,created_at`)
- [ ] Bulk operations (create/update/delete multiple entities)
- [ ] Search endpoints with full-text search

### P1 - API Versioning
- [ ] URL-based versioning (`/api/v1`, `/api/v2`)
- [ ] Header-based versioning (`Accept: application/vnd.chapkit.v2+json`)
- [ ] Deprecation warnings in responses
- [ ] Migration guides in documentation

### P2 - Advanced API Features
- [ ] GraphQL support as alternative to REST
- [ ] Webhook system for event notifications
- [ ] Server-sent events (SSE) for real-time updates
- [ ] WebSocket support for live data
- [ ] ETags for conditional requests/caching
- [ ] HATEOAS links in responses

### P2 - Request/Response Enhancements
- [ ] Compression support (gzip, brotli)
- [ ] Content negotiation (JSON, MessagePack, etc.)
- [ ] Response caching headers
- [ ] Batch request support (multiple operations in one request)

### P3 - Developer Experience
- [ ] Interactive API documentation (Swagger UI customization)
- [ ] Request/response examples in OpenAPI
- [ ] API playground/sandbox environment
- [ ] Client SDK generation (Python, TypeScript, Go)

---

## 🛠️ Developer Experience

### P1 - CLI Tools
- [ ] `chapkit init` - Project scaffolding
- [ ] `chapkit generate module` - Generate new domain module
- [ ] `chapkit generate migration` - Wrapper around Alembic
- [ ] `chapkit db upgrade/downgrade` - Migration management
- [ ] `chapkit dev` - Development server with auto-reload

### P2 - Testing Utilities
- [ ] Test fixtures for Database, Repository, Manager
- [ ] Mock job scheduler for testing async operations
- [ ] Factory pattern utilities for test data generation
- [ ] Integration test helpers for API endpoints
- [ ] Performance testing utilities

### P2 - Code Generation
- [ ] Entity generator from Pydantic schemas
- [ ] OpenAPI client generation
- [ ] Database schema visualization
- [ ] Migration script preview before applying

### P3 - IDE Support
- [ ] VS Code extension with snippets
- [ ] PyCharm plugin
- [ ] Type stub improvements
- [ ] Documentation hover support

---

## 🌐 ML Features & Enhancements

### P1 - ML Landing Pages
- [ ] ML-specific landing page template
- [ ] Display model metadata (author, version, status)
- [ ] Training/prediction examples with code snippets
- [ ] Citation information and model cards
- [ ] Visual status indicators with color coding
- [ ] Link to OpenAPI/Swagger docs
- [ ] Interactive prediction form

### P1 - Model Management
- [ ] Model versioning with semantic versioning
- [ ] Model registry with searchable metadata
- [ ] Model comparison (accuracy, performance, size)
- [ ] Model deprecation workflow
- [ ] Model rollback capabilities

### P2 - Advanced ML Features
- [ ] A/B testing framework for models
- [ ] Champion/challenger model deployment
- [ ] Batch prediction endpoints
- [ ] Streaming predictions
- [ ] Model ensembling support
- [ ] Feature store integration

### P2 - ML Operations
- [ ] Training data versioning
- [ ] Hyperparameter tracking
- [ ] Experiment tracking integration (MLflow, Weights & Biases)
- [ ] Model explainability endpoints (SHAP, LIME)
- [ ] Data validation for inputs/outputs

### P3 - ML Pipeline
- [ ] Multi-stage ML pipelines
- [ ] Scheduled retraining workflows
- [ ] Model warm-up/pre-loading
- [ ] Model serving optimization (ONNX, TensorRT)
- [ ] GPU support for training/inference

---

## 🏗️ Production Features

### P0 - Production Readiness
- [ ] Graceful shutdown handling
- [ ] Request timeout configuration
- [ ] Resource limits (memory, CPU)
- [ ] Environment-based configuration

### P1 - Resilience
- [ ] Rate limiting per endpoint/user
- [ ] Circuit breaker pattern for external services
- [ ] Retry logic with exponential backoff
- [ ] Request queuing with max queue size
- [ ] Deadlock detection and recovery

### P2 - Operational Features
- [ ] Background job priority queues
- [ ] Scheduled jobs/cron support
- [ ] Job deduplication
- [ ] Dead letter queue for failed jobs
- [ ] Job result persistence to database

### P2 - Secrets Management
- [ ] Secrets management integration (Vault, AWS Secrets Manager)
- [ ] Environment variable validation and type coercion
- [ ] Configuration schema validation at startup

### P3 - Advanced Production
- [ ] Blue-green deployment support
- [ ] Canary deployment helpers
- [ ] Feature flags system
- [ ] Dynamic configuration reloading
- [ ] Multi-region deployment support

---

## 💾 Storage & Integration

### P1 - Storage Backends
- [ ] File storage abstraction (local, S3, Azure Blob, GCS)
- [ ] Artifact storage optimization (compression, deduplication)
- [ ] Large artifact streaming (chunked upload/download)
- [ ] Artifact expiration/cleanup policies

### P2 - External Integrations
- [ ] Message queue integration (RabbitMQ, Kafka, SQS)
- [ ] Cache backends (Redis, Memcached)
- [ ] Email service integration
- [ ] SMS notification support
- [ ] Slack/Discord webhook notifications

### P3 - Data Export/Import
- [ ] CSV/Excel export for entities
- [ ] Bulk data import from files
- [ ] Database backup/restore utilities
- [ ] Data migration tools between environments
- [ ] ETL pipeline support

---

## 📚 Documentation & Examples

### P2 - Enhanced Documentation
- [ ] Video tutorials for common workflows
- [ ] Architecture decision records (ADRs)
- [ ] Performance tuning guide
- [ ] Security best practices guide
- [ ] Production deployment guide

### P2 - More Examples
- [ ] E-commerce API example
- [ ] Multi-tenant SaaS example
- [ ] Real-time dashboard example
- [ ] Microservices communication example
- [ ] Complete ML workflow (end-to-end)

### P3 - Interactive Learning
- [ ] Interactive tutorials in documentation
- [ ] Runnable code snippets
- [ ] Common patterns cookbook
- [ ] Migration guides from other frameworks

---

## 🔧 Core Improvements

### P1 - Error Handling
- [ ] Better error messages with suggestions
- [ ] Error aggregation for validation
- [ ] Custom error codes system
- [ ] Error recovery strategies

### P2 - Type Safety
- [ ] Stricter generic type constraints
- [ ] Runtime type validation options
- [ ] Better inference for generic managers
- [ ] Type-safe configuration builder

### P3 - Code Quality
- [ ] Performance benchmarking suite
- [ ] Memory leak detection
- [ ] Code coverage improvements (target 95%+)
- [ ] Dependency injection improvements

---

## 🌟 Ecosystem & Community

### P2 - Plugin System
- [ ] Plugin architecture for extensions
- [ ] Third-party integration marketplace
- [ ] Custom router plugins
- [ ] Custom storage backend plugins

### P3 - Community Features
- [ ] Contribution guidelines
- [ ] Community showcase
- [ ] Example project templates
- [ ] Starter kits for common use cases

---

## 📝 Notes

- This roadmap is subject to change based on community feedback and priorities
- Feature requests can be submitted via GitHub Issues
- Community contributions are welcome for all items
- Priority levels may be adjusted based on demand and dependencies

## 🎯 Current Focus (Next Release)

The immediate focus is on:
1. **API Key Authentication (P0)** ✅ COMPLETED - Simple service-to-service auth with env vars and Docker secrets
2. **Database Connection Pooling (P0)** ✅ COMPLETED - Production-grade connection pool configuration
3. **Database Health Checks (P0)** ✅ COMPLETED - Connection testing in health endpoints
4. **PostgreSQL Support (P0)** - Production-grade database backend (deferred)
5. **Core API Features (P1)** - Filtering, sorting, field selection, bulk operations
6. **Production Readiness (P0-P1)** - Graceful shutdown, timeouts, rate limiting
7. **ML Landing Pages (P1)** - Model metadata display and interactive forms
