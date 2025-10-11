# API Reference

Complete reference for Chapkit's HTTP APIs.

## Overview

Chapkit services expose RESTful APIs with:

- Automatic CRUD endpoints
- Pagination support
- RFC 9457 error format
- JSON schema generation
- Operation endpoints with `$` prefix

## Common Patterns

### Resource vs Operation

- **Resource**: `/api/v1/config/{id}` - Access specific entity
- **Operation**: `/api/v1/config/$schema` - Computed/derived data
- **Collection Operation**: `/api/v1/ml/$train` - Bulk or complex action

The `$` prefix distinguishes operations from resource IDs.

### Response Formats

**Single Entity:**

```json
{
  "id": "01JB...",
  "name": "production",
  "created_at": "2025-01-11T10:00:00Z",
  "updated_at": "2025-01-11T10:00:00Z"
}
```

**Collection (unpaginated):**

```json
[
  {"id": "01JB...", "name": "config1"},
  {"id": "01JB...", "name": "config2"}
]
```

**Collection (paginated):**

```json
{
  "items": [
    {"id": "01JB...", "name": "config1"}
  ],
  "total": 100,
  "page": 1,
  "size": 20,
  "pages": 5
}
```

## Sections

### [Endpoints](endpoints.md)

Common endpoints across all services:

- Health checks
- System information
- CRUD operations
- Job management

### [Schemas](schemas.md)

Request and response schemas:

- Entity input/output
- Pagination
- Job records
- Error responses

### [Pagination](pagination.md)

Optional pagination for list endpoints:

- Query parameters
- Response format
- Navigation

### [Error Handling](error-handling.md)

RFC 9457 problem details:

- Error types
- Status codes
- Error responses

### [Operations](operations.md)

Using the `$` prefix for operations:

- Collection operations
- Entity operations
- Custom operations
- Schema generation

## Quick Reference

### Health Check

```bash
GET /api/v1/health
```

### List Resources

```bash
# Unpaginated
GET /api/v1/config

# Paginated
GET /api/v1/config?page=1&size=20
```

### Create Resource

```bash
POST /api/v1/config
Content-Type: application/json

{
  "name": "production",
  "data": {...}
}
```

### Get Resource

```bash
GET /api/v1/config/{id}
```

### Update Resource

```bash
PUT /api/v1/config/{id}
Content-Type: application/json

{
  "name": "updated",
  "data": {...}
}
```

### Delete Resource

```bash
DELETE /api/v1/config/{id}
```

### Operation

```bash
POST /api/v1/ml/$train
Content-Type: application/json

{
  "config_id": "...",
  "data": {...}
}
```

## Interactive Documentation

All Chapkit services include Swagger UI:

- Visit `/docs` for interactive API explorer
- Visit `/redoc` for ReDoc documentation
- Download OpenAPI spec from `/openapi.json`

## Next Steps

- [Endpoints](endpoints.md) - Detailed endpoint reference
- [Schemas](schemas.md) - Request/response schemas
- [Pagination](pagination.md) - Pagination guide
- [Error Handling](error-handling.md) - Error formats
- [Operations](operations.md) - Operation endpoints
