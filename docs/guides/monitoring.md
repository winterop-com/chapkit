# Monitoring with OpenTelemetry and Prometheus

Chapkit provides built-in monitoring through OpenTelemetry instrumentation with automatic Prometheus metrics export. Get instant observability for your FastAPI and SQLAlchemy operations with minimal configuration.

## Quick Start

Enable monitoring in your service with a single method call:

```python
from chapkit.api import ServiceBuilder, ServiceInfo

app = (
    ServiceBuilder(info=ServiceInfo(display_name="My Service"))
    .with_monitoring()  # Enables OpenTelemetry + Prometheus endpoint
    .with_database()
    .with_health()
    .build()
)
```

That's it! Your service now exposes Prometheus metrics at `/metrics`.

## Features

### Automatic Instrumentation

- **FastAPI**: HTTP request metrics (duration, status codes, paths)
- **SQLAlchemy**: Database query metrics (connection pool, query duration)
- **Python Runtime**: Garbage collection, memory usage, CPU time

### Metrics Endpoint

- **Path**: `/metrics` (operational endpoint, root level)
- **Format**: Prometheus text format
- **Content-Type**: `text/plain; version=0.0.4; charset=utf-8`

### Zero Configuration

No manual instrumentation needed - Chapkit automatically:

- Instruments all FastAPI routes
- Tracks SQLAlchemy database operations
- Exposes Python runtime metrics
- Handles OpenTelemetry lifecycle

## Configuration

### Basic Configuration

```python
.with_monitoring()  # Uses defaults
```

**Defaults:**
- Metrics endpoint: `/metrics`
- Service name: From `ServiceInfo.display_name`
- Tags: `["monitoring"]`

### Custom Configuration

```python
.with_monitoring(
    prefix="/custom/metrics",           # Custom endpoint path
    tags=["observability", "telemetry"], # Custom OpenAPI tags
    service_name="production-api",       # Override service name
)
```

### Parameters

- **prefix** (`str`): Metrics endpoint path. Default: `/metrics`
- **tags** (`List[str]`): OpenAPI tags for metrics endpoint. Default: `["monitoring"]`
- **service_name** (`str | None`): Service name in metrics labels. Default: from `ServiceInfo`

## Metrics Endpoint

### Testing the Endpoint

```bash
# Get metrics
curl http://localhost:8000/metrics

# Filter specific metrics
curl http://localhost:8000/metrics | grep http_request

# Monitor continuously
watch -n 1 'curl -s http://localhost:8000/metrics | grep http_request_duration'
```

### Expected Output

```
# HELP python_gc_objects_collected_total Objects collected during gc
# TYPE python_gc_objects_collected_total counter
python_gc_objects_collected_total{generation="0"} 234.0

# HELP http_server_request_duration_seconds HTTP request duration
# TYPE http_server_request_duration_seconds histogram
http_server_request_duration_seconds_bucket{http_method="GET",http_status_code="200",le="0.005"} 45.0

# HELP db_client_connections_usage Number of connections that are currently in use
# TYPE db_client_connections_usage gauge
db_client_connections_usage{pool_name="default",state="used"} 2.0
```

## Kubernetes Integration

### Deployment with Service Monitor

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: chapkit-service
spec:
  replicas: 3
  template:
    metadata:
      labels:
        app: chapkit-service
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      containers:
      - name: app
        image: your-chapkit-app
        ports:
        - containerPort: 8000
          name: http
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: chapkit-service
  labels:
    app: chapkit-service
spec:
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  selector:
    app: chapkit-service
```

**servicemonitor.yaml** (Prometheus Operator):
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: chapkit-service
  labels:
    app: chapkit-service
spec:
  selector:
    matchLabels:
      app: chapkit-service
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

## Prometheus Configuration

### Scrape Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'chapkit-services'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
        labels:
          service: 'chapkit-api'
          environment: 'production'
```

### Docker Compose Setup

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  chapkit-app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_AUTH_ANONYMOUS_ENABLED=true

volumes:
  prometheus-data:
  grafana-data:
```

## Grafana Dashboards

### Adding Prometheus Data Source

1. Navigate to **Configuration → Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Set URL: `http://prometheus:9090` (Docker) or `http://localhost:9090` (local)
5. Click **Save & Test**

### Example Queries

**HTTP Request Rate:**
```promql
rate(http_server_requests_total{job="chapkit-services"}[5m])
```

**Request Duration (p95):**
```promql
histogram_quantile(0.95,
  rate(http_server_request_duration_seconds_bucket[5m])
)
```

**Database Connection Pool Usage:**
```promql
db_client_connections_usage{state="used"} /
db_client_connections_limit
```

**Error Rate:**
```promql
rate(http_server_requests_total{http_status_code=~"5.."}[5m])
```

## Available Metrics

### HTTP Metrics (FastAPI)

- `http_server_request_duration_seconds` - Request duration histogram
- `http_server_requests_total` - Total requests counter
- `http_server_active_requests` - Active requests gauge

**Labels**: `http_method`, `http_status_code`, `http_route`

### Database Metrics (SQLAlchemy)

- `db_client_connections_usage` - Connection pool usage
- `db_client_connections_limit` - Connection pool limit
- `db_client_operation_duration_seconds` - Query duration

**Labels**: `pool_name`, `state`, `operation`

### Python Runtime Metrics

- `python_gc_objects_collected_total` - GC collections
- `python_gc_collections_total` - GC runs
- `python_info` - Python version info
- `process_cpu_seconds_total` - CPU time
- `process_resident_memory_bytes` - Memory usage

## Best Practices

### ✅ DO

- **Enable monitoring in production** - Essential for observability
- **Set meaningful service names** - Helps identify services in multi-service setups
- **Monitor key metrics** - Focus on request rate, error rate, duration (RED method)
- **Set up alerts** - Alert on error rates, high latency, resource exhaustion
- **Use service labels** - Tag metrics with environment, version, region
- **Keep `/metrics` unauthenticated** - Prometheus needs access (use network policies)

### ❌ DON'T

- **Don't expose metrics publicly** - Use internal network or auth proxy
- **Don't scrape too frequently** - 15-30s interval is usually sufficient
- **Don't ignore high cardinality** - Avoid unbounded label values
- **Don't skip resource limits** - Monitor and limit Prometheus storage growth

## Combining with Other Features

### With Authentication

```python
app = (
    ServiceBuilder(info=info)
    .with_monitoring()
    .with_auth(
        unauthenticated_paths=[
            "/health",      # Health check
            "/metrics",     # Prometheus scraping
            "/docs"         # API docs
        ]
    )
    .build()
)
```

### With Health Checks

```python
app = (
    ServiceBuilder(info=info)
    .with_health()         # /health - Kubernetes liveness/readiness
    .with_system()         # /system - System info
    .with_monitoring()     # /metrics - Prometheus metrics
    .build()
)
```

All operational endpoints (`/health`, `/system`, `/metrics`) use root-level paths for easy discovery and configuration.

## Troubleshooting

### Metrics Endpoint Returns 404

**Problem**: `/metrics` endpoint not found.

**Solution**: Ensure you called `.with_monitoring()` in your ServiceBuilder chain.

### No Metrics Appear

**Problem**: Endpoint returns empty or minimal metrics.

**Solution**:
1. Make some requests to your API endpoints
2. Verify FastAPI instrumentation with: `curl http://localhost:8000/api/v1/config`
3. Check metrics again: `curl http://localhost:8000/metrics | grep http_request`

### Prometheus Cannot Scrape

**Problem**: Prometheus shows targets as "DOWN".

**Solution**:
1. Verify service is running: `curl http://localhost:8000/health`
2. Check network connectivity
3. Verify scrape config matches service port and path
4. Check for firewall/network policies blocking access

### High Memory Usage

**Problem**: Prometheus uses too much memory.

**Solution**:
1. Reduce retention time: `--storage.tsdb.retention.time=15d`
2. Increase scrape interval: `scrape_interval: 30s`
3. Limit metric cardinality (check for unbounded labels)

## Next Steps

- **Alerting**: Set up Prometheus Alertmanager for notifications
- **Distributed Tracing**: Future support for OpenTelemetry traces (see ROADMAP.md)
- **Custom Metrics**: Use `get_meter()` for application-specific metrics
- **SLOs**: Define Service Level Objectives based on metrics

## Examples

- `examples/monitoring_api.py` - Complete monitoring example
- `examples/docs/monitoring_api.postman_collection.json` - Postman collection

For more details, see:
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
