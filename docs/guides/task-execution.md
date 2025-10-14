# Task Execution

Chapkit provides a task execution system for running shell commands asynchronously with artifact-based result storage. Tasks are reusable command templates that can be executed multiple times, with each execution creating a Job and storing results in an Artifact.

## Quick Start

### Create and Execute a Task

```bash
# Start the example service
fastapi dev examples/task_execution_api.py

# Create a task template
TASK_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"command": "echo \"Hello World\""}' | jq -r '.id')

echo "Task ID: $TASK_ID"

# Execute the task
JOB_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks/$TASK_ID/\$execute | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# Wait for completion and get results
sleep 1
ARTIFACT_ID=$(curl -s http://localhost:8000/api/v1/jobs/$JOB_ID | jq -r '.artifact_id')

# View execution results
curl http://localhost:8000/api/v1/artifacts/$ARTIFACT_ID | jq '.data'
```

Output:
```json
{
  "task": {
    "id": "01JCSEED...",
    "command": "echo \"Hello World\"",
    "created_at": "2025-10-14T...",
    "updated_at": "2025-10-14T..."
  },
  "stdout": "Hello World\n",
  "stderr": "",
  "exit_code": 0
}
```

---

## Architecture

The Task execution system uses a clean separation of concerns:

### Task Templates

**Tasks** are reusable command templates stored in the database:
- Contain only the command to execute
- No status or output fields (stateless)
- Can be executed multiple times
- Immutable history (past executions unaffected by template changes)

### Job Execution

When a task is executed:
1. Task snapshot is captured (ID, command, timestamps)
2. Job is submitted to the scheduler
3. Command runs asynchronously via `asyncio.subprocess`
4. stdout, stderr, and exit code are captured

### Artifact Storage

Execution results are stored as Artifacts:
- **task**: Full snapshot of the task template at execution time
- **stdout**: Command standard output
- **stderr**: Command standard error
- **exit_code**: Process exit code

The Job record links to the result artifact via `Job.artifact_id`.

**Benefits:**
- Tasks remain reusable templates
- Complete execution history preserved
- Modifying task doesn't affect past results
- Deleting task preserves execution artifacts

---

## Task Lifecycle

```
1. CREATE TEMPLATE          2. EXECUTE              3. RESULTS STORED
   POST /tasks             POST /tasks/:id/$execute   Artifact created
   └─> Task stored         └─> Job submitted          └─> Job.artifact_id
       (reusable)              (async execution)          (immutable result)
```

### State Transitions

**Task:** Stateless template (no execution state)

**Job:** Tracks execution state
- `pending` → `running` → `completed` (success)
                       → `failed` (error)
                       → `canceled` (user canceled)

**Artifact:** Immutable result record containing task snapshot + outputs

---

## ServiceBuilder Setup

### Minimal Configuration

```python
from chapkit import ArtifactHierarchy
from chapkit.api import ServiceBuilder, ServiceInfo

# Simple hierarchy for task execution artifacts
TASK_HIERARCHY = ArtifactHierarchy(
    name="task_executions",
    level_labels={0: "execution"},
)

app = (
    ServiceBuilder(info=ServiceInfo(display_name="Task Service"))
    .with_health()
    .with_artifacts(hierarchy=TASK_HIERARCHY)  # Required first
    .with_jobs(max_concurrency=5)              # Required second
    .with_tasks()                               # Enables task execution
    .build()
)
```

**Requirements:**
1. `.with_artifacts()` must be called before `.with_tasks()`
2. `.with_jobs()` must be called before `.with_tasks()`
3. Without these, `execute_task()` will raise `ValueError`

### With Database Configuration

```python
app = (
    ServiceBuilder(info=ServiceInfo(display_name="Task Service"))
    .with_database("tasks.db")  # Persist tasks and artifacts
    .with_artifacts(hierarchy=TASK_HIERARCHY)
    .with_jobs(max_concurrency=3)
    .with_tasks()
    .build()
)
```

---

## API Reference

### POST /api/v1/tasks

Create a new task template.

**Request:**
```json
{
  "command": "echo 'Hello World'"
}
```

**Response (201):**
```json
{
  "id": "01JCSEED0000000000000TASK1",
  "command": "echo 'Hello World'",
  "created_at": "2025-10-14T10:30:00Z",
  "updated_at": "2025-10-14T10:30:00Z"
}
```

### GET /api/v1/tasks

List all task templates with optional pagination.

```bash
# List all tasks
curl http://localhost:8000/api/v1/tasks

# With pagination
curl http://localhost:8000/api/v1/tasks?page=1&size=20
```

**Response:**
```json
[
  {
    "id": "01JCSEED0000000000000TASK1",
    "command": "ls -la /tmp",
    "created_at": "2025-10-14T10:30:00Z",
    "updated_at": "2025-10-14T10:30:00Z"
  }
]
```

### GET /api/v1/tasks/{task_id}

Retrieve a specific task template by ID.

```bash
curl http://localhost:8000/api/v1/tasks/01JCSEED0000000000000TASK1
```

### PUT /api/v1/tasks/{task_id}

Update a task template command.

**Request:**
```json
{
  "command": "echo 'Updated command'"
}
```

**Note:** Updating a task does not affect previous execution artifacts.

### DELETE /api/v1/tasks/{task_id}

Delete a task template.

```bash
curl -X DELETE http://localhost:8000/api/v1/tasks/01JCSEED0000000000000TASK1
```

Returns `204 No Content` on success.

**Note:** Deleting a task preserves all execution artifacts.

### POST /api/v1/tasks/{task_id}/$execute

Execute a task asynchronously.

```bash
curl -X POST http://localhost:8000/api/v1/tasks/01JCSEED0000000000000TASK1/\$execute
```

**Response (202 Accepted):**
```json
{
  "job_id": "01JQR7X...",
  "message": "Task submitted for execution. Job ID: 01JQR7X..."
}
```

**Errors:**
- `400 Bad Request` - Task not found or invalid ID
- `409 Conflict` - Scheduler or artifact manager not configured

---

## Artifact Integration

### Result Structure

Each execution creates an artifact with this structure:

```json
{
  "id": "01ARTIFACT...",
  "data": {
    "task": {
      "id": "01TASK...",
      "command": "echo 'test'",
      "created_at": "2025-10-14T10:30:00Z",
      "updated_at": "2025-10-14T10:30:00Z"
    },
    "stdout": "test\n",
    "stderr": "",
    "exit_code": 0
  },
  "created_at": "2025-10-14T10:31:00Z",
  "updated_at": "2025-10-14T10:31:00Z"
}
```

### Task Snapshot Preservation

The artifact contains a **complete snapshot** of the task at execution time:

```bash
# Create task
curl -X POST http://localhost:8000/api/v1/tasks \
  -d '{"command": "echo original"}' > task.json
TASK_ID=$(jq -r '.id' task.json)

# Execute task
curl -X POST http://localhost:8000/api/v1/tasks/$TASK_ID/\$execute > exec1.json
JOB1=$(jq -r '.job_id' exec1.json)

# Modify task
curl -X PUT http://localhost:8000/api/v1/tasks/$TASK_ID \
  -d '{"command": "echo modified"}'

# Execute again
curl -X POST http://localhost:8000/api/v1/tasks/$TASK_ID/\$execute > exec2.json
JOB2=$(jq -r '.job_id' exec2.json)

# First execution has original command
curl http://localhost:8000/api/v1/jobs/$JOB1 | jq '.artifact_id' | \
  xargs -I {} curl http://localhost:8000/api/v1/artifacts/{} | \
  jq '.data.task.command'
# Output: "echo original"

# Second execution has modified command
curl http://localhost:8000/api/v1/jobs/$JOB2 | jq '.artifact_id' | \
  xargs -I {} curl http://localhost:8000/api/v1/artifacts/{} | \
  jq '.data.task.command'
# Output: "echo modified"
```

### Finding Task Executions

```bash
# Get all artifacts (includes task execution results)
curl http://localhost:8000/api/v1/artifacts

# Filter by task ID in application code
artifacts=$(curl -s http://localhost:8000/api/v1/artifacts)
echo "$artifacts" | jq --arg task_id "$TASK_ID" \
  '[.[] | select(.data.task.id == $task_id)]'
```

---

## Examples

### Simple Commands

```bash
# Directory listing
curl -X POST http://localhost:8000/api/v1/tasks \
  -d '{"command": "ls -la /tmp"}' | jq -r '.id'

# Date command
curl -X POST http://localhost:8000/api/v1/tasks \
  -d '{"command": "date"}' | jq -r '.id'

# Echo with output
curl -X POST http://localhost:8000/api/v1/tasks \
  -d '{"command": "echo \"Task execution works!\""}' | jq -r '.id'
```

### Python Scripts

```bash
# Python one-liner
curl -X POST http://localhost:8000/api/v1/tasks -d '{
  "command": "python3 -c \"import sys; print(sys.version); print(2+2)\""
}'

# Python script with multiple operations
curl -X POST http://localhost:8000/api/v1/tasks -d '{
  "command": "python3 -c \"import json; print(json.dumps({\\\"result\\\": 42}))\""
}'
```

### Multi-line Commands

```bash
# Using printf for multi-line output
curl -X POST http://localhost:8000/api/v1/tasks -d '{
  "command": "printf \"Line 1\\nLine 2\\nLine 3\""
}'

# Using bash -c for complex commands
curl -X POST http://localhost:8000/api/v1/tasks -d '{
  "command": "bash -c \"for i in {1..5}; do echo Step $i; done\""
}'
```

### Failing Commands

```bash
# Command that fails (non-existent path)
curl -X POST http://localhost:8000/api/v1/tasks -d '{
  "command": "ls /nonexistent/directory"
}'

# Execute and check results
TASK_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -d '{"command": "ls /nonexistent/directory"}' | jq -r '.id')

JOB_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks/$TASK_ID/\$execute | jq -r '.job_id')

# Wait and check artifact
sleep 1
curl http://localhost:8000/api/v1/jobs/$JOB_ID | jq '.artifact_id' | \
  xargs -I {} curl http://localhost:8000/api/v1/artifacts/{} | jq '.data'

# Output shows:
# - exit_code: non-zero (e.g., 1 or 2)
# - stderr: error message about missing directory
# - Job status: "completed" (job succeeded even though command failed)
```

**Note:** Job status is `completed` even if command fails. Check `exit_code` in artifact to determine command success.

### Capturing stderr

```bash
# Write to stderr
curl -X POST http://localhost:8000/api/v1/tasks -d '{
  "command": ">&2 echo \"error message\""
}'

# Execute and check stderr in artifact
TASK_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -d '{"command": ">&2 echo \"error message\""}' | jq -r '.id')
JOB_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks/$TASK_ID/\$execute | jq -r '.job_id')

sleep 1
curl http://localhost:8000/api/v1/jobs/$JOB_ID | jq '.artifact_id' | \
  xargs -I {} curl http://localhost:8000/api/v1/artifacts/{} | jq '.data.stderr'
```

### Concurrent Execution

```bash
# Create task
TASK_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -d '{"command": "sleep 2 && echo done"}' | jq -r '.id')

# Execute multiple times concurrently
for i in {1..5}; do
  curl -s -X POST http://localhost:8000/api/v1/tasks/$TASK_ID/\$execute &
done
wait

# List all jobs to see concurrent executions
curl http://localhost:8000/api/v1/jobs | jq
```

---

## Error Handling

### Task Not Found (400)

```bash
curl -X POST http://localhost:8000/api/v1/tasks/01K72P5N5KCRM6MD3BRE4P0999/\$execute
```

**Response:**
```json
{
  "detail": "Task 01K72P5N5KCRM6MD3BRE4P0999 not found"
}
```

### Invalid ULID (400)

```bash
curl -X POST http://localhost:8000/api/v1/tasks/invalid-id/\$execute
```

**Response:**
```json
{
  "type": "urn:chapkit:error:invalid-ulid",
  "title": "Invalid ULID",
  "status": 400,
  "detail": "Invalid ULID format: invalid-id"
}
```

### Missing Dependencies (409)

If `.with_artifacts()` or `.with_jobs()` not configured:

```json
{
  "detail": "Task execution requires artifacts. Use ServiceBuilder.with_artifacts() before with_tasks()."
}
```

### Validation Errors (422)

```bash
# Missing command field
curl -X POST http://localhost:8000/api/v1/tasks -d '{}'
```

**Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "command"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## Testing

### Manual Testing

**Terminal 1: Start service**
```bash
fastapi dev examples/task_execution_api.py
```

**Terminal 2: Test workflow**
```bash
# Create task
TASK_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"command": "echo \"test\""}' | jq -r '.id')

echo "Task ID: $TASK_ID"

# Execute task
JOB_ID=$(curl -s -X POST http://localhost:8000/api/v1/tasks/$TASK_ID/\$execute | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# Monitor job status
curl -N http://localhost:8000/api/v1/jobs/$JOB_ID/\$stream

# Get results
ARTIFACT_ID=$(curl -s http://localhost:8000/api/v1/jobs/$JOB_ID | jq -r '.artifact_id')
curl http://localhost:8000/api/v1/artifacts/$ARTIFACT_ID | jq '.data'
```

### Automated Testing

```python
import httpx
import time
from collections.abc import Generator

def wait_for_job_completion(
    client: httpx.Client,
    job_id: str,
    timeout: float = 5.0
) -> dict:
    """Poll job status until completion or timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = client.get(f"/api/v1/jobs/{job_id}")
        job = response.json()

        if job["status"] in ["completed", "failed", "canceled"]:
            return job

        time.sleep(0.1)

    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


def test_task_execution():
    """Test creating and executing a task."""
    with httpx.Client(base_url="http://localhost:8000") as client:
        # Create task
        response = client.post(
            "/api/v1/tasks",
            json={"command": "echo 'test'"}
        )
        assert response.status_code == 201
        task = response.json()
        task_id = task["id"]

        # Execute task
        response = client.post(f"/api/v1/tasks/{task_id}/$execute")
        assert response.status_code == 202
        job_id = response.json()["job_id"]

        # Wait for completion
        job = wait_for_job_completion(client, job_id)
        assert job["status"] == "completed"
        assert job["artifact_id"] is not None

        # Check artifact
        response = client.get(f"/api/v1/artifacts/{job['artifact_id']}")
        artifact = response.json()

        assert artifact["data"]["task"]["id"] == task_id
        assert "test" in artifact["data"]["stdout"]
        assert artifact["data"]["exit_code"] == 0
```

### Pytest with TestClient

```python
import pytest
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Create FastAPI TestClient with lifespan context."""
    from examples.task_execution_api import app

    with TestClient(app) as test_client:
        yield test_client


def test_create_task(client: TestClient) -> None:
    """Test creating a new task template."""
    response = client.post(
        "/api/v1/tasks",
        json={"command": "echo 'test'"}
    )
    assert response.status_code == 201
    task = response.json()

    assert "id" in task
    assert task["command"] == "echo 'test'"
    assert "created_at" in task


def test_execute_task(client: TestClient) -> None:
    """Test executing a task and retrieving results."""
    # Create task
    response = client.post(
        "/api/v1/tasks",
        json={"command": "echo 'Hello World'"}
    )
    task_id = response.json()["id"]

    # Execute
    response = client.post(f"/api/v1/tasks/{task_id}/$execute")
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Wait for completion
    import time
    time.sleep(1)

    # Get results
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    artifact = client.get(f"/api/v1/artifacts/{job['artifact_id']}").json()

    assert "Hello World" in artifact["data"]["stdout"]
    assert artifact["data"]["exit_code"] == 0
```

---

## Production Deployment

### Concurrency Control

Limit concurrent task executions to prevent resource exhaustion:

```python
app = (
    ServiceBuilder(info=ServiceInfo(display_name="Task Service"))
    .with_artifacts(hierarchy=TASK_HIERARCHY)
    .with_jobs(max_concurrency=5)  # Max 5 tasks running simultaneously
    .with_tasks()
    .build()
)
```

**Recommendations:**
- **CPU-bound tasks**: Set to number of CPU cores (e.g., 4-8)
- **I/O-bound tasks**: Higher limits OK (10-20)
- **Memory-intensive**: Lower limits to prevent OOM (2-5)
- **Long-running**: Consider lower limits (3-5)

### Database Configuration

Use persistent database for production:

```python
app = (
    ServiceBuilder(info=ServiceInfo(display_name="Task Service"))
    .with_database("/data/tasks.db")  # Persistent storage
    .with_artifacts(hierarchy=TASK_HIERARCHY)
    .with_jobs(max_concurrency=5)
    .with_tasks()
    .build()
)
```

**Best Practices:**
- Mount `/data` volume in Docker/Kubernetes
- Regular backups of task templates and artifacts
- Monitor database size (artifacts can grow)

### Task Retention

Implement cleanup for old execution artifacts:

```python
from datetime import datetime, timedelta
from chapkit.api import ServiceBuilder

async def cleanup_old_artifacts(app):
    """Remove artifacts older than 30 days."""
    artifact_manager = app.state.artifact_manager

    cutoff_date = datetime.utcnow() - timedelta(days=30)

    # Implementation depends on your retention policy
    # Consider using artifact metadata or timestamps
    pass

app = (
    ServiceBuilder(info=info)
    .with_artifacts(hierarchy=TASK_HIERARCHY)
    .with_jobs(max_concurrency=5)
    .with_tasks()
    .on_startup(cleanup_old_artifacts)  # Run on startup
    .build()
)
```

### Monitoring

Track task execution metrics:

```python
from prometheus_client import Counter, Histogram

task_executions = Counter(
    'task_executions_total',
    'Total task executions',
    ['status']
)

task_duration = Histogram(
    'task_duration_seconds',
    'Task execution duration'
)

# Combine with monitoring feature
app = (
    ServiceBuilder(info=info)
    .with_monitoring()  # Prometheus metrics at /metrics
    .with_artifacts(hierarchy=TASK_HIERARCHY)
    .with_jobs(max_concurrency=5)
    .with_tasks()
    .build()
)
```

### Security Considerations

**Command Injection Prevention:**

Tasks execute arbitrary shell commands. Implement access controls:

```python
from chapkit.core.api.crud import CrudPermissions

# Restrict task creation/modification
task_permissions = CrudPermissions(
    create=False,    # Disable runtime task creation
    read=True,
    update=False,    # Disable runtime updates
    delete=False,    # Disable deletion
)

# Apply at router level (requires custom router setup)
```

**Recommendations:**
- Pre-seed tasks at startup (read-only templates)
- Use authentication (`.with_auth()`)
- Validate commands before creating tasks
- Run service with limited OS user permissions
- Use container security (no privileged mode)
- Monitor execution logs for suspicious commands

### Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Copy application
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -e .

# Create non-root user
RUN useradd -m -u 1000 taskuser && \
    chown -R taskuser:taskuser /app

USER taskuser

# Run service
CMD ["fastapi", "run", "examples/task_execution_api.py", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  task-service:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - task-data:/data
    environment:
      - DATABASE_URL=/data/tasks.db
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G

volumes:
  task-data:
```

---

## Troubleshooting

### Job Status is "completed" but Command Failed

**Problem:** Job shows `status: completed` but command actually failed.

**Cause:** Job execution succeeded (subprocess ran), but command returned non-zero exit code.

**Solution:** Check `exit_code` in artifact:

```bash
curl http://localhost:8000/api/v1/jobs/$JOB_ID | jq '.artifact_id' | \
  xargs -I {} curl http://localhost:8000/api/v1/artifacts/{} | \
  jq '.data.exit_code'

# exit_code == 0: command succeeded
# exit_code != 0: command failed
```

### "Task execution requires artifacts" Error

**Problem:** `ValueError: Task execution requires artifacts`

**Solution:** Call `.with_artifacts()` before `.with_tasks()`:

```python
# Wrong order
.with_tasks()
.with_artifacts(hierarchy=TASK_HIERARCHY)  # Too late!

# Correct order
.with_artifacts(hierarchy=TASK_HIERARCHY)
.with_tasks()
```

### "Task execution requires a scheduler" Error

**Problem:** `ValueError: Task execution requires a scheduler`

**Solution:** Call `.with_jobs()` before `.with_tasks()`:

```python
# Wrong order
.with_tasks()
.with_jobs()  # Too late!

# Correct order
.with_jobs(max_concurrency=5)
.with_tasks()
```

### Jobs Not Executing (Stuck in "pending")

**Problem:** Jobs remain in `pending` state indefinitely.

**Causes:**
1. Reached `max_concurrency` limit
2. Scheduler not started properly
3. Long-running jobs blocking queue

**Solution:**
```bash
# Check running jobs
curl http://localhost:8000/api/v1/jobs?status_filter=running | jq 'length'

# If at max_concurrency, wait for completion or increase limit
# Restart service to reset scheduler if needed
```

### Artifact Not Created

**Problem:** `Job.artifact_id` is `null` after completion.

**Cause:** Job failed during execution (before artifact creation).

**Solution:** Check job error:

```bash
curl http://localhost:8000/api/v1/jobs/$JOB_ID | jq '.error'
```

### Command Not Found in Container

**Problem:** Task works locally but fails in Docker with "command not found".

**Cause:** Command not installed in container image.

**Solution:** Install required tools in Dockerfile:

```dockerfile
# Install common utilities
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    python3 \
    && rm -rf /var/lib/apt/lists/*
```

---

## Next Steps

- **Job Monitoring:** Use `.with_jobs()` SSE streaming for real-time task progress
- **ML Workflows:** Combine with `.with_ml()` for ML training tasks
- **Authentication:** Secure with `.with_auth()` for production
- **Monitoring:** Track execution metrics with `.with_monitoring()`

For more examples:
- `examples/task_execution_api.py` - Complete task execution service
- `tests/test_example_task_execution_api.py` - Comprehensive test suite
- `docs/guides/job-scheduler.md` - Job scheduler and SSE streaming
