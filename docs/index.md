---
title: FastAPI Guard Agent - Reporting Agent for FastAPI Guard
description: Reporting Agent for FastAPI Guard. Collects and sends metrics and events from FastAPI Guard to your SaaS backend.
keywords: fastapi, security, middleware, python, metrics, events, telemetry, saas, reporting
---

# FastAPI Guard Agent

<p align="center">
    <a href="https://rennf93.github.io/fastapi-guard-agent/latest/">
        <img src="https://rennf93.github.io/fastapi-guard-agent/latest/assets/big_logo.svg" alt="FastAPI Guard Agent">
    </a>
</p>

<p align="center">
    <strong>fastapi-guard-agent is a companion reporting agent for FastAPI Guard. It seamlessly collects security events, performance metrics, and telemetry data from FastAPI Guard and transmits them to your SaaS backend for centralized monitoring, analysis, and dynamic rule management.</strong>
</p>

<p align="center">
    <a href="https://badge.fury.io/py/fastapi-guard-agent">
        <img src="https://badge.fury.io/py/fastapi-guard-agent.svg?cache=none&icon=si%3Apython&icon_color=%23008cb4" alt="PyPiVersion">
    </a>
    <a href="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/release.yml">
        <img src="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/release.yml/badge.svg" alt="Release">
    </a>
    <a href="https://opensource.org/licenses/MIT">
        <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
    </a>
    <a href="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/ci.yml">
        <img src="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/ci.yml/badge.svg" alt="CI">
    </a>
    <a href="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/code-ql.yml">
        <img src="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/code-ql.yml/badge.svg" alt="CodeQL">
    </a>
</p>

<p align="center">
    <a href="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/pages/pages-build-deployment">
        <img src="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/pages/pages-build-deployment/badge.svg?branch=gh-pages" alt="PagesBuildDeployment">
    </a>
    <a href="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/docs.yml">
        <img src="https://github.com/rennf93/fastapi-guard-agent/actions/workflows/docs.yml/badge.svg" alt="DocsUpdate">
    </a>
    <img src="https://img.shields.io/github/last-commit/rennf93/fastapi-guard-agent?style=flat&amp;logo=git&amp;logoColor=white&amp;color=0080ff" alt="last-commit">
</p>

<p align="center">
    <img src="https://img.shields.io/badge/Python-3776AB.svg?style=flat&amp;logo=Python&amp;logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-009688.svg?style=flat&amp;logo=FastAPI&amp;logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/Redis-FF4438.svg?style=flat&amp;logo=Redis&amp;logoColor=white" alt="Redis">
    <a href="https://pepy.tech/project/fastapi-guard-agent">
        <img src="https://pepy.tech/badge/fastapi-guard-agent" alt="Downloads">
    </a>
</p>

`fastapi-guard-agent` is a companion agent for the `fastapi-guard` security library. It's designed to seamlessly integrate with your FastAPI application and `fastapi-guard` to provide powerful, real-time security monitoring and threat intelligence by collecting security events, performance metrics, and other telemetry and sending them to your SaaS backend.

___

## Quick Start

Here's a quick example of how to integrate `fastapi-guard-agent` into a FastAPI application.

First, you need to configure the agent. The agent is a singleton, and you can initialize it in your application's startup event.

```python
# main.py
import asyncio
from fastapi import FastAPI, Request
from fastapi_guard.fastapi_guard import Guard
from guard_agent.client import guard_agent
from guard_agent.models import AgentConfig, SecurityEvent
from guard_agent.utils import get_current_timestamp

app = FastAPI()

# 1. Configure the Guard Agent
agent_config = AgentConfig(
    api_key="YOUR_API_KEY",
    project_id="YOUR_PROJECT_ID",
    # Optional: fine-tune buffering and other settings
    buffer_size=500,
    flush_interval=60,
)
agent = guard_agent(agent_config)

# 2. Define a custom handler to send data to the agent
class AgentSecurityEventHandler:
    async def handle(self, request: Request, exc: Exception):
        # This is a simplified example.
        # You would create more specific events based on the exception.
        event = SecurityEvent(
            timestamp=get_current_timestamp(),
            event_type="suspicious_request",
            ip_address=request.client.host,
            endpoint=request.url.path,
            method=request.method,
            action_taken="log",
            reason=str(exc),
        )
        await agent.send_event(event)
        # You can also re-raise the exception or return a response
        # raise exc

# 3. Configure fastapi-guard to use your handler
guard = Guard(handlers={"suspicious_request": AgentSecurityEventHandler()})

# 4. Use the guard in your endpoints
@app.get("/")
@guard.protect("suspicious_request")
async def root():
    return {"message": "Hello World"}

# 5. Start and stop the agent with FastAPI's lifespan events
@app.on_event("startup")
async def startup_event():
    # Optional: If you use Redis for buffer persistence
    # from redis.asyncio import Redis
    # from fastapi_guard.redis_handler import RedisHandler
    # redis_handler = RedisHandler(redis=Redis.from_url("redis://localhost"))
    # await agent.initialize_redis(redis_handler)
    await agent.start()

@app.on_event("shutdown")
async def shutdown_event():
    await agent.stop()
```

___

## Features

-   **Seamless Integration**: Works out-of-the-box with `fastapi-guard` to collect security events and metrics.
-   **Asynchronous by Design**: Built on `asyncio` to ensure non-blocking operations and high performance.
-   **Resilient Data Transport**: Features a robust HTTP transport layer with automatic retries, exponential backoff, and a circuit breaker pattern for reliable data delivery.
-   **Efficient Buffering**: Events and metrics are buffered in memory and can be persisted to Redis for durability, preventing data loss on application restarts.
-   **Dynamic Configuration**: Can fetch dynamic security rules from the FastAPI Guard SaaS backend, allowing you to update security policies on the fly without redeploying your application.
-   **Extensible**: Uses a protocol-based design, allowing for custom implementations of components like the transport layer or Redis handler.
-   **Comprehensive Telemetry**: Collects detailed `SecurityEvent` and `SecurityMetric` data, providing insights into your application's security posture and performance.
-   **Circuit Breaker Pattern**: Implements intelligent failure handling to prevent overwhelming your backend during outages.
-   **Rate Limiting**: Built-in client-side rate limiting to ensure optimal API usage.
-   **Data Privacy**: Configurable sensitive data redaction and payload size limits.
-   **Health Monitoring**: Automatic agent health reporting and status tracking.

___

## Installation

Install `fastapi-guard-agent` using pip:

```bash
pip install fastapi-guard-agent
```

The agent requires Python 3.8+ and is compatible with all FastAPI versions.

___

## Basic Usage

### Simple Integration

The simplest way to get started is to configure the agent in your FastAPI application:

```python
from fastapi import FastAPI
from guard_agent.client import guard_agent
from guard_agent.models import AgentConfig

app = FastAPI()

# Configure the agent
config = AgentConfig(
    api_key="your-api-key",
    project_id="your-project-id",
    endpoint="https://api.fastapi-guard.com",
    buffer_size=100,
    flush_interval=30,
)

# Initialize the agent
agent = guard_agent(config)

@app.on_event("startup")
async def startup_event():
    await agent.start()

@app.on_event("shutdown")
async def shutdown_event():
    await agent.stop()
```

### With FastAPI Guard Integration

For full integration with FastAPI Guard, configure the agent to receive events:

```python
from fastapi import FastAPI, Request
from fastapi_guard import Guard
from guard_agent.client import guard_agent
from guard_agent.models import AgentConfig, SecurityEvent
from guard_agent.utils import get_current_timestamp

app = FastAPI()

# Configure agent
config = AgentConfig(
    api_key="your-api-key",
    project_id="your-project-id",
)
agent = guard_agent(config)

# Custom event handler for FastAPI Guard
async def security_event_handler(request: Request, event_type: str, reason: str):
    """Send security events to the agent"""
    event = SecurityEvent(
        timestamp=get_current_timestamp(),
        event_type=event_type,
        ip_address=request.client.host if request.client else "unknown",
        endpoint=str(request.url.path),
        method=request.method,
        action_taken="blocked",
        reason=reason,
        user_agent=request.headers.get("User-Agent"),
    )
    await agent.send_event(event)

# Configure FastAPI Guard
guard = Guard(
    config=SecurityConfig(
        # ... your security config
    ),
    event_handler=security_event_handler,
)

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    return await guard.process_request(request, call_next)

@app.on_event("startup")
async def startup_event():
    await agent.start()

@app.on_event("shutdown")
async def shutdown_event():
    await agent.stop()
```

___

## Advanced Configuration

### Redis Integration

For production deployments, enable Redis for persistent buffering:

```python
from redis.asyncio import Redis
from guard_agent.redis_handler import RedisHandler

# Configure Redis
redis_client = Redis.from_url("redis://localhost:6379")
redis_handler = RedisHandler(redis_client)

# Initialize agent with Redis
agent = guard_agent(config)
await agent.initialize_redis(redis_handler)
```

### Custom Transport

Implement custom transport for specialized backends:

```python
from guard_agent.protocols import TransportProtocol
from guard_agent.models import SecurityEvent, SecurityMetric, AgentStatus, DynamicRules

class CustomTransport(TransportProtocol):
    async def send_events(self, events: list[SecurityEvent]) -> bool:
        # Your custom implementation
        return True

    async def send_metrics(self, metrics: list[SecurityMetric]) -> bool:
        # Your custom implementation
        return True

    async def fetch_dynamic_rules(self) -> DynamicRules | None:
        # Your custom implementation
        return None

    async def send_status(self, status: AgentStatus) -> bool:
        # Your custom implementation
        return True

# Use custom transport
agent = guard_agent(config)
agent.transport = CustomTransport()
```

___

## Data Models

### SecurityEvent

Represents security-related events in your application:

```python
from guard_agent.models import SecurityEvent
from guard_agent.utils import get_current_timestamp

event = SecurityEvent(
    timestamp=get_current_timestamp(),
    event_type="ip_banned",
    ip_address="192.168.1.100",
    country="US",
    user_agent="Mozilla/5.0...",
    action_taken="block",
    reason="Rate limit exceeded",
    endpoint="/api/v1/login",
    method="POST",
    status_code=429,
    response_time=0.125,
    metadata={"attempts": 5, "window": 60}
)

await agent.send_event(event)
```

### SecurityMetric

Represents performance and usage metrics:

```python
from guard_agent.models import SecurityMetric

metric = SecurityMetric(
    timestamp=get_current_timestamp(),
    metric_type="request_count",
    value=100.0,
    endpoint="/api/v1/users",
    tags={"method": "GET", "status": "200"}
)

await agent.send_metric(metric)
```

___

## Dynamic Rules

Fetch and apply dynamic security rules from your SaaS backend:

```python
# Fetch current rules
rules = await agent.get_dynamic_rules()

if rules:
    # Apply IP blacklist
    if client_ip in rules.ip_blacklist:
        # Block request
        pass

    # Apply rate limits
    endpoint_limit = rules.endpoint_rate_limits.get("/api/sensitive")
    if endpoint_limit:
        requests, window = endpoint_limit
        # Apply endpoint-specific rate limit
        pass

    # Check emergency mode
    if rules.emergency_mode:
        # Apply stricter security measures
        pass
```

___

## Monitoring and Health

### Agent Status

Monitor agent health and performance:

```python
status = await agent.get_status()

print(f"Status: {status.status}")  # healthy, degraded, error
print(f"Uptime: {status.uptime}s")
print(f"Events sent: {status.events_sent}")
print(f"Buffer size: {status.buffer_size}")
print(f"Errors: {status.errors}")
```

### Statistics

Get detailed agent statistics:

```python
stats = agent.get_stats()

print(f"Running: {stats['running']}")
print(f"Events sent: {stats['events_sent']}")
print(f"Transport stats: {stats['transport_stats']}")
print(f"Buffer stats: {stats['buffer_stats']}")
```

___

## Error Handling

### Circuit Breaker

The agent includes a circuit breaker to handle backend failures gracefully:

```python
# Check circuit breaker state
transport_stats = agent.transport.get_stats()
if transport_stats["circuit_breaker_state"] == "OPEN":
    print("Backend is unavailable, circuit breaker is open")
```

### Retry Logic

Failed requests are automatically retried with exponential backoff:

```python
config = AgentConfig(
    api_key="your-api-key",
    retry_attempts=3,      # Number of retries
    backoff_factor=1.5,    # Exponential backoff factor
    timeout=30,            # Request timeout
)
```

___

## Documentation

- [Introduction](agent_introduction.md)
- [Configuration](agent_configuration.md)
- [Architecture](agent_architecture.md)
- [Data Models](agent_data_models.md)
- [Dynamic Rules](agent_dynamic_rules.md)
- [Installation](installation.md)
- [First Steps](tutorial/first-steps.md)
- [API Reference](api_reference.md)

[📖 **Learn More in the Documentation**](agent_introduction.md)
