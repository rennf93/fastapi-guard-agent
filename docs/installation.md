# Installation

This guide will help you install and set up `fastapi-guard-agent` in your FastAPI application.

## Requirements

### Python Version

`fastapi-guard-agent` requires **Python 3.8 or higher**. We recommend using Python 3.9+ for the best experience.

You can check your Python version with:

```bash
python --version
```

### Dependencies

The agent has the following core dependencies that will be automatically installed:

- **`fastapi`** - FastAPI framework (any version)
- **`pydantic`** ≥ 2.0 - Data validation and serialization
- **`httpx`** - Async HTTP client for transport (FastAPI compatible)
- **`redis`** ≥ 4.0.0 - Redis client for buffering (optional but recommended)

### Optional Dependencies

- **Redis server** - For persistent event buffering (highly recommended for production)
- **`uvicorn`** or another ASGI server - To run your FastAPI application

## Installation Methods

### Using pip (Recommended)

Install the latest stable version from PyPI:

```bash
pip install fastapi-guard-agent
```

### Using pip with specific version

If you need a specific version:

```bash
pip install fastapi-guard-agent==0.1.1
```

### Using Poetry

If you're using Poetry for dependency management:

```bash
poetry add fastapi-guard-agent
```

### Using pip-tools

Add to your `requirements.in`:

```text
fastapi-guard-agent
```

Then compile and install:

```bash
pip-compile requirements.in
pip install -r requirements.txt
```

### Development Installation

If you want to contribute or install from source:

```bash
git clone https://github.com/rennf93/fastapi-guard-agent.git
cd fastapi-guard-agent
pip install -e .
```

### Docker Installation

You can also use the agent in a Docker environment. Add it to your `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Install the agent
RUN pip install fastapi-guard-agent

# Copy your application
COPY . /app
WORKDIR /app

# Install your app dependencies
RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Verification

After installation, verify that the agent is correctly installed:

### 1. Import Test

```python
# test_installation.py
try:
    from guard_agent import __version__
    from guard_agent.client import guard_agent
    from guard_agent.models import AgentConfig
    print(f"✅ FastAPI Guard Agent {__version__} installed successfully!")
except ImportError as e:
    print(f"❌ Installation failed: {e}")
```

Run the test:

```bash
python test_installation.py
```

### 2. Basic Configuration Test

```python
# test_config.py
from guard_agent.client import guard_agent
from guard_agent.models import AgentConfig

try:
    config = AgentConfig(
        api_key="test-key",
        project_id="test-project"
    )
    agent = guard_agent(config)
    print("✅ Agent configuration successful!")
except Exception as e:
    print(f"❌ Configuration failed: {e}")
```

### 3. Redis Connection Test (Optional)

If you're planning to use Redis for buffering:

```python
# test_redis.py
import asyncio
from redis.asyncio import Redis

async def test_redis():
    try:
        redis = Redis.from_url("redis://localhost:6379")
        await redis.ping()
        print("✅ Redis connection successful!")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
    finally:
        await redis.close()

if __name__ == "__main__":
    asyncio.run(test_redis())
```

## Configuration Verification

Create a minimal configuration to ensure everything works:

```python
# minimal_test.py
import asyncio
from guard_agent.client import guard_agent
from guard_agent.models import AgentConfig

async def test_agent():
    config = AgentConfig(
        api_key="your-test-api-key",
        project_id="your-test-project",
        endpoint="https://api.fastapi-guard.com"  # or your custom endpoint
    )

    agent = guard_agent(config)

    # Test agent lifecycle
    try:
        await agent.start()
        print("✅ Agent started successfully!")

        # Check agent status
        status = await agent.get_status()
        print(f"✅ Agent status: {status.status}")

    except Exception as e:
        print(f"❌ Agent test failed: {e}")
    finally:
        await agent.stop()
        print("✅ Agent stopped successfully!")

if __name__ == "__main__":
    asyncio.run(test_agent())
```

## Common Issues and Solutions

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'guard_agent'`

**Solutions**:
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

### Redis Connection Issues

**Problem**: `ConnectionError: Error connecting to Redis`

**Solutions**:
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

### HTTP Transport Issues

**Problem**: `httpx.HTTPError` or connection timeouts

**Solutions**:
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

### Permission Issues

**Problem**: `PermissionError` during installation

**Solutions**:
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

## Next Steps

Once you have successfully installed `fastapi-guard-agent`, you can:

1. **[Get Started](tutorial/getting-started.md)** - Follow our quick start guide
2. **[Configure the Agent](tutorial/configuration.md)** - Learn about configuration options
3. **[Integrate with FastAPI Guard](tutorial/integration.md)** - Full integration guide
4. **[Explore Examples](examples/index.md)** - See real-world usage examples

## Getting Help

If you encounter issues not covered here:

1. Check our [Troubleshooting Guide](guides/troubleshooting.md)
2. Search existing [GitHub Issues](https://github.com/rennf93/fastapi-guard-agent/issues)
3. Create a new issue with:
   - Your Python version (`python --version`)
   - Package version (`pip show fastapi-guard-agent`)
   - Error message and full traceback
   - Your configuration (with sensitive data removed)

## System Requirements Summary

| Component | Requirement |
|-----------|-------------|
| Python | 3.8+ (3.9+ recommended) |
| Memory | 64MB+ available RAM |
| Network | HTTPS outbound access |
| Storage | 10MB+ disk space |
| Redis | Optional but recommended for production |