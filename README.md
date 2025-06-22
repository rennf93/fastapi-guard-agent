# FastAPI Guard Agent

Telemetry and monitoring agent for [FastAPI Guard](https://github.com/rennf93/fastapi-guard) security middleware.

This library enables real-time monitoring, analytics, and dynamic rule management for FastAPI Guard through a SaaS platform.

## Features

- **Real-time Telemetry**: Security events and metrics streaming
- **Dynamic Rules**: Remote configuration and rule updates
- **Buffer Management**: Efficient batching with Redis persistence
- **Reliability**: Circuit breaker, retry logic, and rate limiting
- **Async Support**: Full async/await compatibility
- **Redis Integration**: Optional Redis support for distributed environments

## Installation

```bash
pip install fastapi-guard-agent

# With Redis support
pip install fastapi-guard-agent[redis]
```

## Quick Start

### Basic Usage

```python
from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware
from guard_agent import AgentConfig, guard_agent

# Configure the agent
agent_config = AgentConfig(
    api_key="your-api-key-here",
    project_id="your-project-id",
    endpoint="https://api.fastapi-guard.com"
)

# Start the agent
agent = guard_agent(agent_config)
await agent.start()

# Send events manually
from guard_agent import SecurityEvent, get_current_timestamp

event = SecurityEvent(
    timestamp=get_current_timestamp(),
    event_type="ip_banned",
    ip_address="192.168.1.100",
    action_taken="banned",
    reason="Suspicious activity detected"
)

await agent.send_event(event)
```

### Integration with FastAPI Guard

The agent is designed to integrate seamlessly with FastAPI Guard:

```python
from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware
from guard_agent import AgentConfig, guard_agent

app = FastAPI()

# Configure agent
agent_config = AgentConfig(
    api_key="your-api-key",
    project_id="your-project",
    buffer_size=50,
    flush_interval=30
)

# Configure security
security_config = SecurityConfig(
    rate_limit=100,
    auto_ban_threshold=10,
    # Agent integration will be added in future versions
)

# Add security middleware
app.add_middleware(SecurityMiddleware, config=security_config)

# Start agent (typically in startup event)
@app.on_event("startup")
async def startup_event():
    agent = guard_agent(agent_config)
    await agent.start()

@app.on_event("shutdown")
async def shutdown_event():
    agent = guard_agent(agent_config)
    await agent.stop()
```

## Configuration

### AgentConfig Options

```python
from guard_agent import AgentConfig

config = AgentConfig(
    # Required
    api_key="your-api-key",

    # Optional
    endpoint="https://api.fastapi-guard.com",  # SaaS endpoint
    project_id="your-project-id",             # Project identifier

    # Buffering
    buffer_size=100,                          # Events before auto-flush
    flush_interval=30,                        # Seconds between flushes

    # Features
    enable_events=True,                       # Send security events
    enable_metrics=True,                      # Send performance metrics

    # HTTP Settings
    timeout=30,                              # Request timeout
    retry_attempts=3,                        # Retry failed requests
    backoff_factor=1.0,                      # Exponential backoff

    # Privacy
    sensitive_headers=["authorization"],      # Headers to redact
    max_payload_size=1024,                   # Max payload size to log
)
```

## Event Types

The agent supports various security event types:

- `ip_banned` - IP address was banned
- `rate_limited` - Request was rate limited
- `suspicious_request` - Suspicious activity detected
- `cloud_blocked` - Cloud provider IP blocked
- `country_blocked` - Geographic restriction applied
- `penetration_attempt` - Attack pattern detected
- `behavioral_violation` - Behavioral rule triggered
- `user_agent_blocked` - User agent restriction
- `custom_rule_triggered` - Custom security rule

## Metrics

Performance and usage metrics:

- `request_count` - Total requests processed
- `response_time` - Average response times
- `error_rate` - Error rates by endpoint
- `bandwidth_usage` - Data transfer metrics
- `threat_level` - Security threat levels
- `block_rate` - Blocking/filtering rates
- `cache_hit_rate` - Cache performance

## Redis Integration

For distributed environments:

```python
from guard_agent import guard_agent, AgentConfig

config = AgentConfig(api_key="your-key")
agent = guard_agent(config)

# Initialize with Redis (same protocol as FastAPI Guard)
await agent.initialize_redis(your_redis_handler)
await agent.start()
```

## Development

### Requirements

- Python 3.10+
- aiohttp
- pydantic
- fastapi (for integration)
- redis (optional)

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
ruff check guard_agent/
mypy guard_agent/
```

## Architecture

The agent follows the same patterns as FastAPI Guard:

- **Singleton Pattern**: One agent instance per application
- **Protocol-Based Design**: Clean interfaces for extensibility
- **Redis Integration**: Compatible with existing Redis infrastructure
- **Async-First**: Built for high-performance async applications

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code quality passes
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Links

- [FastAPI Guard](https://github.com/rennf93/fastapi-guard)
- [Documentation](https://fastapi-guard.readthedocs.io/)
- [PyPI Package](https://pypi.org/project/fastapi-guard-agent/)
