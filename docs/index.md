---
title: FastAPI Guard Agent - Enterprise Security Intelligence for FastAPI Applications
description: Enterprise-grade telemetry and monitoring solution for FastAPI Guard. Provides real-time security event collection, performance monitoring, and dynamic policy management through a centralized platform.
keywords: fastapi, security, middleware, telemetry, monitoring, enterprise, cloud, saas, compliance, threat intelligence
---

# FastAPI Guard Agent

<p align="center">
    <a href="https://rennf93.github.io/fastapi-guard-agent/latest/">
        <img src="https://rennf93.github.io/fastapi-guard-agent/latest/assets/big_logo.svg" alt="FastAPI Guard Agent">
    </a>
</p>

<p align="center">
    <strong>FastAPI Guard Agent is a sophisticated telemetry and monitoring solution designed to provide comprehensive security intelligence for FastAPI applications. Built as a companion to FastAPI Guard, it enables real-time collection of security events, performance metrics, and operational telemetry, facilitating centralized security operations, compliance reporting, and dynamic threat response through an enterprise-grade management platform.</strong>
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

The FastAPI Guard Agent represents a critical component in modern application security architecture. As organizations increasingly adopt microservices and API-driven architectures, the need for sophisticated security telemetry has become paramount. This agent bridges the gap between application-level security enforcement and enterprise security operations, providing real-time visibility into security events, performance anomalies, and threat patterns across your FastAPI infrastructure.

___

## Quick Start

The FastAPI Guard Agent is engineered for seamless integration with your existing security infrastructure. The following example demonstrates the standard deployment pattern:

```python
from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware

app = FastAPI()

# Configure FastAPI Guard with built-in agent support
config = SecurityConfig(
    # Basic security settings
    auto_ban_threshold=5,
    auto_ban_duration=300,

    # Enable agent for telemetry
    enable_agent=True,
    agent_api_key="YOUR_API_KEY",
    agent_project_id="YOUR_PROJECT_ID",
    agent_endpoint="https://api.fastapi-guard.com",

    # Agent configuration
    agent_buffer_size=100,
    agent_flush_interval=30,
    agent_enable_events=True,
    agent_enable_metrics=True,

    # Enable dynamic rules from SaaS
    enable_dynamic_rules=True,
    dynamic_rule_interval=300,
)

# Add security middleware - events are sent automatically
middleware = SecurityMiddleware(app, config=config)

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

___

## Core Capabilities

### Security Intelligence
-   **Automated Event Collection**: Captures comprehensive security events including authentication failures, authorization violations, rate limit breaches, and suspicious request patterns without manual instrumentation
-   **Real-Time Threat Detection**: Provides immediate visibility into security incidents with sub-second event propagation to the management platform
-   **Behavioral Analytics**: Tracks request patterns and user behavior to identify anomalies and potential security threats

### Enterprise Architecture
-   **Zero-Impact Performance**: Leverages asynchronous I/O and intelligent buffering to ensure telemetry collection adds negligible overhead to application performance
-   **Fault-Tolerant Design**: Implements circuit breakers, exponential backoff with jitter, and intelligent retry mechanisms to maintain operation during network disruptions
-   **Multi-Tier Buffering**: Combines in-memory and persistent Redis buffering to guarantee zero data loss during outages or maintenance windows

### Operational Excellence
-   **Dynamic Policy Management**: Supports real-time security policy updates without application restart, enabling immediate threat response
-   **Protocol-Based Extensibility**: Provides clean abstractions for custom transport implementations, storage backends, and data processors
-   **Comprehensive Observability**: Captures granular metrics including response times, error rates, and resource utilization for complete operational visibility

### Data Governance
-   **Privacy-First Design**: Implements configurable data redaction for sensitive headers and payload truncation to meet compliance requirements
-   **Intelligent Rate Limiting**: Prevents API exhaustion through client-side rate limiting with adaptive backpressure
-   **Health Monitoring**: Continuous self-diagnostics with automatic health reporting and degradation detection

___

## Installation

The FastAPI Guard Agent supports standard Python package management workflows:

```bash
pip install fastapi-guard-agent
```

### System Requirements
- Python 3.10 or higher (3.11+ recommended for optimal performance)
- Compatible with all FastAPI versions
- Optional Redis 6.0+ for persistent buffering

___

## Implementation Patterns

### Primary Integration Pattern

The recommended approach leverages FastAPI Guard's built-in agent support for automatic telemetry collection:

```python
from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware

app = FastAPI()

config = SecurityConfig(
    # Enable agent
    enable_agent=True,
    agent_api_key="your-api-key",
    agent_project_id="your-project-id",

    # Other security settings
    enable_rate_limiting=True,
    rate_limit=100,
    rate_limit_window=60,
)

middleware = SecurityMiddleware(app, config=config)

# Agent automatically initialized with comprehensive event collection
```

### Advanced Usage Pattern

For specialized use cases requiring direct agent control, such as custom event handling or integration with non-FastAPI Guard systems:

```python
from fastapi import FastAPI
from guard_agent import guard_agent, AgentConfig, SecurityEvent
from guard_agent.utils import get_current_timestamp

app = FastAPI()

# Configure agent directly
config = AgentConfig(
    api_key="your-api-key",
    project_id="your-project-id",
    buffer_size=100,
    flush_interval=30,
)

agent = guard_agent(config)

@app.on_event("startup")
async def startup_event():
    await agent.start()

@app.on_event("shutdown")
async def shutdown_event():
    await agent.stop()

@app.post("/report-event")
async def report_event():
    # Manually send an event
    event = SecurityEvent(
        timestamp=get_current_timestamp(),
        event_type="custom_rule_triggered",
        ip_address="192.168.1.100",
        action_taken="logged",
        reason="Manual event",
        endpoint="/report-event",
        method="POST",
    )
    await agent.send_event(event)
    return {"status": "event sent"}
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
