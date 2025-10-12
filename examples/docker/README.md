# Docker Deployment Examples

Docker Compose examples for deploying Chapkit services with authentication.

## Available Examples

### 1. Environment Variables (`docker-compose.auth-envvar.yml`)

**Use case:** Simple deployment where API keys are set via environment variables or `.env` file.

**Best for:**
- All production environments
- Quick deployments
- Environment variable based secrets management

**Start:**
```bash
cd examples/docker
cp .env.example .env
# Edit .env with real API keys
docker-compose -f docker-compose.auth-envvar.yml up
```

### 2. Docker Secrets (`docker-compose.auth-secrets.yml`)

**Use case:** Secure deployment using Docker secrets file mounted as volume.

**Best for:**
- Docker Compose deployments
- Docker Swarm
- Maximum security in containerized environments

**Start:**
```bash
cd examples/docker
mkdir -p secrets
cp secrets/api_keys.txt.example secrets/api_keys.txt
# Edit secrets/api_keys.txt with real keys
chmod 400 secrets/api_keys.txt
docker-compose -f docker-compose.auth-secrets.yml up
```

## Quick Start

### Option 1: Environment Variables (Recommended)

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env and set your API keys
vi .env

# 3. Start service
docker-compose -f docker-compose.auth-envvar.yml up

# 4. Test
curl -H "X-API-Key: YOUR_KEY_HERE" http://localhost:8000/api/v1/configs
```

### Option 2: Docker Secrets (Most Secure)

```bash
# 1. Create secrets directory
mkdir -p secrets

# 2. Copy and edit secrets file
cp secrets/api_keys.txt.example secrets/api_keys.txt
vi secrets/api_keys.txt

# 3. Secure the file
chmod 400 secrets/api_keys.txt

# 4. Start service
docker-compose -f docker-compose.auth-secrets.yml up

# 5. Test
curl -H "X-API-Key: YOUR_KEY_HERE" http://localhost:8000/api/v1/configs
```

## File Structure

```
examples/docker/
├── README.md                           # This file
├── .env.example                        # Environment variable template
├── docker-compose.auth-envvar.yml      # Environment variables deployment
├── docker-compose.auth-secrets.yml     # Docker secrets deployment
└── secrets/
    └── api_keys.txt.example            # Secrets file template
```

## Testing Deployments

### Health Check

```bash
# Should work without authentication
curl http://localhost:8000/health
```

### Authenticated Endpoint

```bash
# Replace YOUR_KEY with actual key
curl -H "X-API-Key: YOUR_KEY" http://localhost:8000/api/v1/configs
```

### View Logs

```bash
# Environment variables version
docker-compose -f docker-compose.auth-envvar.yml logs -f

# Docker secrets version
docker-compose -f docker-compose.auth-secrets.yml logs -f
```

## Security Best Practices

### ✅ DO

- **Use `.env` files** for local development
- **Use Docker secrets** for production
- **Add secrets to `.gitignore`**
- **Use `chmod 400`** for secrets files
- **Rotate keys** regularly
- **Use different keys** per environment
- **Monitor logs** for failed auth attempts

### ❌ DON'T

- **Commit `.env` or secrets files** to git
- **Use weak keys** (minimum 16 characters)
- **Reuse keys** across environments
- **Share secrets** via email/Slack
- **Leave secrets files** world-readable

## .gitignore Setup

Ensure these patterns are in your `.gitignore`:

```gitignore
# Environment files
.env
.env.*
!.env.example

# Secrets
secrets/api_keys.txt
secrets/*.txt
!secrets/*.example
```

## Docker Swarm Deployment

For Docker Swarm, use secrets management:

```bash
# Create Docker secret
echo -e "sk_prod_key1\nsk_prod_key2" | docker secret create chapkit_api_keys -

# Deploy stack
docker stack deploy -c docker-compose.auth-secrets.yml chapkit-stack

# Verify
docker service ls
docker service logs chapkit-stack_api
```

## Kubernetes Deployment

See `../../docs/authentication.md` for Kubernetes deployment with secrets.

## Troubleshooting

### "No API keys configured" Error

**Problem:** Service fails to start

**Solution:**
```bash
# For envvar version
cat .env | grep CHAPKIT_API_KEYS

# For secrets version
cat secrets/api_keys.txt
```

### "Permission Denied" Reading Secrets

**Problem:** Can't read secrets file

**Solution:**
```bash
chmod 644 secrets/api_keys.txt
```

### Authentication Fails

**Problem:** 401 Unauthorized responses

**Solution:**
1. Check container logs: `docker-compose logs api`
2. Verify key format: `sk_environment_random`
3. Check environment variables are loaded: `docker-compose config`

## Stopping Services

```bash
# Stop and remove containers
docker-compose -f docker-compose.auth-envvar.yml down

# Stop and remove with volumes
docker-compose -f docker-compose.auth-envvar.yml down -v
```

## Next Steps

- Read `../../docs/authentication.md` for comprehensive guide
- See `../auth_envvar.py` and `../auth_docker_secrets.py` for source code
- Check `../docs/auth_envvar.md` for detailed workflow
