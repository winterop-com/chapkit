# Chapkit Roadmap

> **Vision:** Build the most productive async Python framework for ML/data services with FastAPI integration

## Priority Legend
- 🔥 **High Priority** - Next 1-2 releases (actively working or immediate next)
- 📌 **Medium Priority** - Next 3-6 releases (planned, design in progress)
- 💡 **Future** - Under consideration (evaluate demand/feasibility)

---

## 🔥 High Priority (Next 1-2 Releases)

### Task Execution
- [ ] **Task scheduling (Phase 2)** - Cron, interval, and one-off scheduling with in-memory storage
  - Already designed in `designs/python-tasks-and-scheduling.md`
  - Background scheduler worker
  - Schedule enable/disable controls
  - Migration path to persistent scheduling

- [ ] **Decorator-based ML runner registration** - Extend TaskRegistry with metadata
  - Reuse TaskRegistry instead of creating new registry
  - `@TaskRegistry.register("model_name", type="ml_train")`
  - `FunctionalModelRunner.from_registry()` factory method
  - Cleaner API, consistent with task patterns

### Developer Experience
- [ ] **chapkit.client.Client** - Python client for testing and working with chapkit services
  - Type-safe client with IDE support
  - Automatic serialization/deserialization
  - Request/response validation
  - Essential for testing and SDK users

### Artifact System
- [ ] **Artifact export** - Export DataFrames and data structures from artifacts
  - CSV, Parquet, JSON formats
  - Streaming for large datasets
  - Compression support (gzip, bzip2)

---

## 📌 Medium Priority (Next 3-6 Releases)

### Task Execution Enhancements
- [ ] **Retry policies** - Automatic retry with exponential backoff for failed tasks
- [ ] **Custom injectable types** - User-defined dependency injection types
- [ ] **Result caching** - Cache task results based on parameters with TTL

### ML System
- [ ] **Enhanced train/predict metadata** - Store full config, model type, framework version, hyperparameters
- [ ] **Model versioning** - Track model lineage and version history
- [ ] **Experiment tracking** - MLflow or W&B integration for experiment management

### Configuration
- [ ] **Multiple config types** - Support multiple config schemas per service
- [ ] **Config versioning** - Track and rollback config changes

### Observability
- [ ] **Distributed tracing** - OpenTelemetry integration for request tracing
- [ ] **Enhanced metrics** - Custom metrics registration and SLO tracking
- [ ] **Structured audit logging** - Comprehensive audit trails for compliance

### Type Safety
- [ ] **Stricter generic constraints** - Better compile-time type checking
- [ ] **Runtime type validation** - Optional runtime validation layer

---

## 💡 Future Considerations

### Advanced Task Features
- [ ] **Registry namespacing** - Module-scoped registries to avoid collisions
- [ ] **Function versioning** - Track function versions in artifacts
- [ ] **Parameter serialization** - Custom serializers for complex types

### ML Advanced Features
- [ ] **Model registry** - Central registry for discovering trained models
- [ ] **A/B testing** - Deploy multiple model versions with traffic splitting
- [ ] **Pipeline composition** - Chain models and transformations
- [ ] **Feature store integration** - Connect to feature stores

### Developer Tools
- [ ] **CLI tool** - Command-line tool for migrations, seeding, testing
- [ ] **Code generation** - Generate boilerplate for modules, routers, models
- [ ] **Development server** - Enhanced dev server with auto-reload

### Testing & Quality
- [ ] **Performance benchmarking** - Comprehensive benchmarks for core operations
- [ ] **Memory leak detection** - Automated leak detection in tests
- [ ] **Code coverage 95%+** - Target high coverage across all modules
- [ ] **Load testing tools** - Built-in load testing utilities

### API & Middleware
- [ ] **WebSocket support** - Real-time updates via WebSockets
- [ ] **Rate limiting** - Built-in rate limiting middleware
- [ ] **Response caching** - Intelligent caching layer
- [ ] **GraphQL support** - Optional GraphQL layer (evaluate demand first)
- [ ] **gRPC support** - High-performance gRPC endpoints (evaluate demand first)

### Security
- [ ] **RBAC** - Role-based access control
- [ ] **OAuth2/JWT** - Modern authentication flows
- [ ] **Encryption at rest** - Encrypt sensitive artifacts and configs
- [ ] **Secret management** - Vault, AWS Secrets Manager integration

### Cloud & Storage
- [ ] **Artifact cloud storage** - S3, GCS, Azure Blob backends
- [ ] **PostgreSQL adapter** - Production-grade relational DB support
- [ ] **Message queue integration** - RabbitMQ, Kafka for async processing

### Documentation
- [ ] **Tutorial series** - Step-by-step guides for common patterns
- [ ] **Architecture guide** - Deep dive into chapkit internals
- [ ] **Best practices** - Production deployment patterns
- [ ] **Video tutorials** - Screencast series for key features

---

## Recently Completed ✅

### v0.x (Current)
- ✅ **Python task execution** - TaskRegistry with decorator-based registration
- ✅ **Type-based dependency injection** - Automatic injection of framework services
- ✅ **Enable/disable controls** - Task execution controls
- ✅ **Orphaned task validation** - Auto-disable tasks with missing functions
- ✅ **App hosting system** - Host static web apps alongside API
- ✅ **Health check SSE streaming** - Server-sent events for health monitoring
- ✅ **Comprehensive testing** - 683 tests passing with extensive coverage
- ✅ **ML service builder** - Specialized builder for ML workflows

---

## Evaluation Criteria for New Features

Before adding items to this roadmap, consider:

1. **Core Value Alignment** - Does it enhance ML/data service development?
2. **Developer Experience** - Does it reduce boilerplate or improve productivity?
3. **Production Readiness** - Does it solve real production challenges?
4. **Maintenance Burden** - Can we maintain it long-term?
5. **Community Demand** - Are users asking for it?
6. **Breaking Changes** - Can we add it without breaking existing code?

## Contributing

Have ideas for the roadmap? Open an issue with:
- **Use case** - What problem does it solve?
- **Alternatives** - What workarounds exist today?
- **Impact** - How many users would benefit?
- **Effort** - Rough complexity estimate

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.
