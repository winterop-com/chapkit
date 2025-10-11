# ML Service cURL Examples

This directory contains cURL guides for interacting with the ML service examples.

## Available Examples

- **[ml_basic.md](ml_basic.md)** - Basic functional model runner with LinearRegression
- **[ml_class.md](ml_class.md)** - Class-based model runner with feature preprocessing
- **[ml_shell.md](ml_shell.md)** - Shell-based runner using external Python scripts

## Common ML Workflow

All ML services follow the same basic workflow:

### 1. Start the Service

```bash
# Choose one example
fastapi dev examples/ml_basic.py   # Basic functional example
fastapi dev examples/ml_class.py   # Class-based with preprocessing
fastapi dev examples/ml_shell.py   # Shell-based with external scripts
```

Service runs at: `http://127.0.0.1:8000`

### 2. Check Health

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### 3. Create Configuration

```bash
curl -X POST http://127.0.0.1:8000/api/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_model_config",
    "data": {
      "min_samples": 3
    }
  }'
```

Save the returned `id` for training.

### 4. Train Model

```bash
curl -X POST http://127.0.0.1:8000/api/v1/ml/\$train \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": "YOUR_CONFIG_ID",
    "data": {
      "columns": ["rainfall", "mean_temperature", "disease_cases"],
      "data": [
        [100.5, 25.3, 12],
        [85.2, 27.1, 8],
        [120.8, 24.5, 15],
        [95.3, 26.2, 10]
      ]
    }
  }'
```

Save the returned `job_id` and `model_artifact_id`.

### 5. Check Job Status

```bash
# Poll until status is "completed"
curl http://127.0.0.1:8000/api/v1/jobs/YOUR_JOB_ID
```

### 6. Get Trained Model Artifact

```bash
curl http://127.0.0.1:8000/api/v1/artifacts/YOUR_MODEL_ARTIFACT_ID
```

### 7. Make Predictions

```bash
curl -X POST http://127.0.0.1:8000/api/v1/ml/\$predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_artifact_id": "YOUR_MODEL_ARTIFACT_ID",
    "future": {
      "columns": ["rainfall", "mean_temperature"],
      "data": [
        [110.0, 26.0],
        [90.0, 28.0]
      ]
    }
  }'
```

Save the returned `prediction_artifact_id`.

### 8. Get Predictions

```bash
curl http://127.0.0.1:8000/api/v1/artifacts/YOUR_PREDICTION_ARTIFACT_ID
```

## Common Endpoints

All ML services provide these endpoints:

### Health & Info
- `GET /api/v1/health` - Health check
- `GET /api/v1/system` - System information (if `.with_system()` enabled)

### Configuration
- `POST /api/v1/config` - Create config
- `GET /api/v1/config` - List all configs (supports pagination)
- `GET /api/v1/config/{id}` - Get specific config
- `PUT /api/v1/config/{id}` - Update config
- `DELETE /api/v1/config/{id}` - Delete config
- `GET /api/v1/config/$schema` - Get config JSON schema

### Artifacts
- `POST /api/v1/artifacts` - Create artifact
- `GET /api/v1/artifacts` - List all artifacts (supports pagination)
- `GET /api/v1/artifacts/{id}` - Get specific artifact
- `GET /api/v1/artifacts/{id}/$tree` - Get artifact tree
- `DELETE /api/v1/artifacts/{id}` - Delete artifact

### Jobs
- `GET /api/v1/jobs` - List all jobs (supports `?status_filter=completed`)
- `GET /api/v1/jobs/{id}` - Get job status and result
- `DELETE /api/v1/jobs/{id}` - Cancel/delete job

### ML Operations
- `POST /api/v1/ml/$train` - Train model asynchronously
- `POST /api/v1/ml/$predict` - Make predictions asynchronously

## Data Format

### Training Data

Training data uses the pandas-compatible JSON format:

```json
{
  "columns": ["feature1", "feature2", "target"],
  "data": [
    [value1, value2, target1],
    [value3, value4, target2]
  ]
}
```

**Required columns depend on the model:**
- Disease models: `rainfall`, `mean_temperature`, `disease_cases`
- Weather models: `rainfall`, `mean_temperature`, `humidity`, `disease_cases`

### Prediction Data

Prediction data only includes features (no target):

```json
{
  "columns": ["feature1", "feature2"],
  "data": [
    [value1, value2],
    [value3, value4]
  ]
}
```

### Optional GeoJSON Data

Some models support geospatial data:

```json
{
  "geo": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Point",
          "coordinates": [-122.4194, 37.7749]
        },
        "properties": {
          "name": "San Francisco"
        }
      }
    ]
  }
}
```

## Pagination

List endpoints support optional pagination:

```bash
# Without pagination (returns array)
curl http://127.0.0.1:8000/api/v1/config

# With pagination (returns PaginatedResponse)
curl "http://127.0.0.1:8000/api/v1/config?page=1&size=10"
```

## Error Handling

All services use RFC 9457 problem details format:

```json
{
  "type": "urn:chapkit:error:not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Config 01K72P60ZNX2PJ6QJWZK7RMCRV not found",
  "instance": "/api/v1/config/01K72P60ZNX2PJ6QJWZK7RMCRV"
}
```

Common error types:
- `not-found` (404) - Resource not found
- `validation-failed` (400) - Input validation error
- `invalid-ulid` (400) - Invalid ID format
- `conflict` (409) - Resource conflict

## Tips

1. **Save IDs**: Store `config_id`, `model_artifact_id`, and `job_id` for later use
2. **Poll Jobs**: Training and prediction are async - poll `/api/v1/jobs/{id}` until status is `completed`
3. **Use jq**: Parse JSON responses: `curl ... | jq '.id'`
4. **Logging**: Services with `.with_logging()` provide structured logs with request tracing
5. **Interactive Docs**: Visit `http://127.0.0.1:8000/docs` for Swagger UI

## Next Steps

- See example-specific guides for detailed workflows
- Check [../ml_basic.py](../ml_basic.py) source code for implementation details
- Read [../../CLAUDE.md](../../CLAUDE.md) for architecture and API reference
