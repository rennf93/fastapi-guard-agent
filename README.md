<p align="center">
    <a href="https://rennf93.github.io/fastapi-guard-agent/latest/">
        <img src="https://rennf93.github.io/fastapi-guard-agent/latest/assets/big_logo.svg" alt="FastAPI Guard Agent">
    </a>
</p>

---

<p align="center">
    <strong>fastapi-guard-agent is a reporting agent for FastAPI Guard. It collects and sends metrics and events from FastAPI Guard to your SaaS backend.</strong>
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

---

Documentation
=============

🎮 **[Join our Discord Community](https://discord.gg/ZW7ZJbjMkK)** - Connect with other developers!

📚 **[Documentation](https://rennf93.github.io/fastapi-guard-agent)** - Full technical documentation and deep dive into its inner workings.

---

Features
--------

-   **Seamless Integration**: Works out-of-the-box with `fastapi-guard` to collect security events and metrics.
-   **Asynchronous by Design**: Built on `asyncio` to ensure non-blocking operations and high performance.
-   **Resilient Data Transport**: Features a robust HTTP transport layer with automatic retries, exponential backoff, and a circuit breaker pattern for reliable data delivery.
-   **Efficient Buffering**: Events and metrics are buffered in memory and can be persisted to Redis for durability, preventing data loss on application restarts.
-   **Dynamic Configuration**: Can fetch dynamic security rules from the FastAPI Guard SaaS backend, allowing you to update security policies on the fly without redeploying your application.
-   **Extensible**: Uses a protocol-based design, allowing for custom implementations of components like the transport layer or Redis handler.
-   **Comprehensive Telemetry**: Collects detailed `SecurityEvent` and `SecurityMetric` data, providing insights into your application's security posture and performance.

---

Installation
------------

To install `fastapi-guard-agent`, use pip:

```bash
pip install fastapi-guard-agent
```

---

Usage
-----------

Basic Setup
-----------

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

In this example:
1.  We create an `AgentConfig` with our credentials.
2.  We create a simple handler that constructs a `SecurityEvent` and sends it to the agent using `agent.send_event()`.
3.  We tell `fastapi-guard` to use this handler for a custom protection key.
4.  We use `@guard.protect()` on an endpoint.
5.  We use FastAPI's `startup` and `shutdown` events to manage the agent's lifecycle.

Now, when a request is made to the `/` endpoint, `fastapi-guard` will invoke our handler, which in turn sends a security event to the agent. The agent will buffer it and send it to the backend.

---

Detailed Configuration Options
------------------------------

The `fastapi-guard-agent` is configured using the `AgentConfig` pydantic model. You create an instance of this class and pass it to the `guard_agent` factory function to initialize the agent.

```python
from guard_agent.client import guard_agent
from guard_agent.models import AgentConfig

config = AgentConfig(
    api_key="YOUR_API_KEY",
    project_id="YOUR_PROJECT_ID",
)

agent = guard_agent(config)
```

### `AgentConfig` Attributes

-   **`api_key: str`**: **Required**. Your API key for the FastAPI Guard SaaS platform.
-   **`endpoint: str`**: The API endpoint for the SaaS platform.
    -   Default: `https://api.fastapi-guard.com`
-   **`project_id: str | None`**: Your project ID. This is used to associate data with the correct project in the backend.
    -   Default: `None`
-   **`buffer_size: int`**: The maximum number of events and metrics to hold in the in-memory buffer before they are flushed.
    -   Default: `100`
-   **`flush_interval: int`**: The interval in seconds at which the buffer is automatically flushed, sending its contents to the backend.
    -   Default: `30`
-   **`enable_metrics: bool`**: A global switch to enable or disable sending all performance metrics.
    -   Default: `True`
-   **`enable_events: bool`**: A global switch to enable or disable sending all security events.
    -   Default: `True`
-   **`retry_attempts: int`**: The number of times the agent will try to resend data if a request fails.
    -   Default: `3`
-   **`timeout: int`**: The total timeout in seconds for a single HTTP request to the backend.
    -   Default: `30`
-   **`backoff_factor: float`**: The factor used to calculate the delay between retry attempts (exponential backoff). The delay is calculated as `backoff_factor * (2 ** (attempt - 1))`.
    -   Default: `1.0`
-   **`sensitive_headers: list[str]`**: A list of HTTP header names (case-insensitive) that will be redacted (replaced with `[REDACTED]`) before being sent.
    -   Default: `["authorization", "cookie", "x-api-key"]`
-   **`max_payload_size: int`**: The maximum size in bytes for a request or response payload that is included in a security event. Payloads larger than this will be truncated.
    -   Default: `1024`

---

Contributing
------------

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

---

License
-------

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

Author
------

Renzo Franceschini - [rennf93@users.noreply.github.com](mailto:rennf93@users.noreply.github.com)

---

Acknowledgements
----------------

- [FastAPI](https://fastapi.tiangolo.com/)
- [Redis](https://redis.io/)
- [httpx](https://www.python-httpx.org/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)