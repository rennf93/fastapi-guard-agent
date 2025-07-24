# Installation Guide

This comprehensive guide provides detailed instructions for deploying FastAPI Guard Agent across various environments and configurations.

## System Requirements

### Python Runtime

FastAPI Guard Agent requires **Python 3.10 or higher**. For optimal performance and feature compatibility, Python 3.11+ is recommended.

Verify your Python installation:

```bash
python --version
```

### Core Dependencies

The following dependencies are automatically managed during installation:

#### Required Components
- **`fastapi-guard`** - Security middleware providing the integration framework
- **`pydantic`** ≥ 2.0 - Type-safe data validation and serialization
- **`httpx`** - High-performance async HTTP client with connection pooling
- **`typing-extensions`** ≥ 4.0 - Enhanced type hints for Python 3.10 compatibility

#### Optional Components
- **`redis`** ≥ 4.0.0 - Client library for persistent buffering (production recommended)
- **Redis Server** 6.0+ - External service for high-availability deployments
- **ASGI Server** - Uvicorn, Hypercorn, or similar for application hosting

## Installation Methods

### Standard Installation

For integrated deployments with FastAPI Guard:

```bash
pip install fastapi-guard fastapi-guard-agent
```

For standalone agent deployments:

```bash
pip install fastapi-guard-agent
```

### Version-Specific Installation

Pin to a specific version for reproducible deployments:

```bash
pip install fastapi-guard-agent==0.1.1
```

### Modern Python Packaging

#### Poetry Integration

```bash
poetry add fastapi-guard-agent
```

For development dependencies:

```bash
poetry add --group dev fastapi-guard-agent
```

#### pip-tools Workflow

Define in `requirements.in`:

```text
fastapi-guard-agent>=0.1.0,<1.0.0
```

Generate locked requirements:

```bash
pip-compile requirements.in
pip-sync requirements.txt
```

### Development Installation

For contributors and advanced users requiring source access:

```bash
git clone https://github.com/rennf93/fastapi-guard-agent.git
cd fastapi-guard-agent
pip install -e ".[dev]"
```

Install pre-commit hooks for code quality:

```bash
pre-commit install
```

### Container Deployment

#### Production Dockerfile

Optimized multi-stage build for minimal image size:

```dockerfile
FROM python:3.11-slim as builder

# Build dependencies
WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt fastapi-guard-agent

FROM python:3.11-slim

# Copy installed packages
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Application setup
WORKDIR /app
COPY . .

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Installation Verification

Comprehensive validation ensures proper deployment:

### 1. Package Import Validation

Verify successful installation through systematic import testing:

```python
# test_installation.py
try:
    # Validate FastAPI Guard installation
    from guard import SecurityConfig, SecurityMiddleware
    print("✅ FastAPI Guard installation verified")

    # Validate Agent module availability
    from guard_agent import __version__
    from guard_agent.client import guard_agent
    from guard_agent.models import AgentConfig
    print(f"✅ FastAPI Guard Agent {__version__} successfully installed")
except ImportError as e:
    print(f"❌ Installation validation failed: {e}")
```

Run the test:

```bash
python test_installation.py
```

### 2. Configuration Validation Test

Validate proper integration between FastAPI Guard and the telemetry agent:

```python
# test_config.py
from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware

try:
    app = FastAPI()

    # Validate integrated configuration
    config = SecurityConfig(
        enable_agent=True,
        agent_api_key="test-key",
        agent_project_id="test-project"
    )
    middleware = SecurityMiddleware(app, config=config)
    print("✅ Security middleware with telemetry pipeline successfully configured")
except Exception as e:
    print(f"❌ Configuration validation failed: {e}")
```

### 3. Redis Connectivity Validation (Production Environments)

For production deployments utilizing Redis for persistent buffering:

```python
# test_redis.py
import asyncio
from redis.asyncio import Redis

async def validate_redis_connectivity():
    try:
        redis = Redis.from_url("redis://localhost:6379")
        await redis.ping()
        print("✅ Redis connectivity validated - persistent buffering available")
    except Exception as e:
        print(f"❌ Redis connectivity validation failed: {e}")
    finally:
        await redis.close()

if __name__ == "__main__":
    asyncio.run(validate_redis_connectivity())
```

## Configuration Verification

Create a minimal application to ensure everything works:

```python
# minimal_test.py
from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware

app = FastAPI()

# Configure FastAPI Guard with agent
config = SecurityConfig(
    # Basic security
    enable_rate_limiting=True,
    rate_limit=100,

    # Enable agent
    enable_agent=True,
    agent_api_key="your-test-api-key",
    agent_project_id="your-test-project",
    agent_endpoint="https://api.fastapi-guard.com"
)

# Add middleware - agent starts automatically
middleware = SecurityMiddleware(app, config=config)

@app.get("/")
async def root():
    return {"message": "FastAPI Guard Agent is running!"}

@app.get("/test")
async def test():
    return {"agent_enabled": config.enable_agent}

# Run with: uvicorn minimal_test:app --reload
```

## Troubleshooting Guide

### Module Import Failures

**Symptom**: `ModuleNotFoundError: No module named 'guard_agent'`

**Resolution Strategies**:
1. Ensure you're using the correct Python environment:
   ```bash
   which python
   pip list | grep fastapi-guard-agent
   ```

2. If using virtual environments, make sure it's activated:
   ```bash
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. Reinstall the package:
   ```bash
   pip uninstall fastapi-guard-agent
   pip install fastapi-guard-agent
   ```

### Redis Connectivity Issues

**Symptom**: `ConnectionError: Error connecting to Redis`

**Resolution Strategies**:
1. Ensure Redis server is running:
   ```bash
   redis-cli ping
   ```

2. Check Redis configuration in your agent config:
   ```python
   # Make sure Redis URL is correct
   redis = Redis.from_url("redis://localhost:6379/0")
   ```

3. Install Redis server if not installed:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install redis-server

   # macOS with Homebrew
   brew install redis

   # Start Redis
   redis-server
   ```

### Network Transport Failures

**Symptom**: `httpx.HTTPError` or connection timeout exceptions

**Resolution Strategies**:
1. Check your API endpoint configuration:
   ```python
   config = AgentConfig(
       endpoint="https://api.fastapi-guard.com",  # Ensure this is correct
       api_key="your-api-key"
   )
   ```

2. Verify network connectivity:
   ```bash
   curl -I https://api.fastapi-guard.com/health
   ```

3. Check firewall settings and proxy configuration if behind corporate network.

### Installation Permission Errors

**Symptom**: `PermissionError` during package installation

**Resolution Strategies**:
1. Use `--user` flag for user-level installation:
   ```bash
   pip install --user fastapi-guard-agent
   ```

2. Use virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install fastapi-guard-agent
   ```

3. On systems with permission issues, consider using `sudo` (not recommended):
   ```bash
   sudo pip install fastapi-guard-agent
   ```

## Post-Installation Guidance

Following successful installation of `fastapi-guard-agent`, proceed with:

1. **[Getting Started Guide](tutorial/getting-started.md)** - Comprehensive implementation walkthrough
2. **[Configuration Reference](tutorial/configuration.md)** - Detailed configuration parameter documentation
3. **[Integration Patterns](tutorial/integration.md)** - Advanced integration architectures
4. **[Implementation Examples](examples/index.md)** - Production-ready deployment patterns

## System Requirements Summary

| Component | Requirement |
|-----------|-------------|
| Python | 3.10+ (3.11+ recommended) |
| Memory | 64MB+ available RAM |
| Network | HTTPS outbound access |
| Storage | 10MB+ disk space |
| Redis | Optional but recommended for production |