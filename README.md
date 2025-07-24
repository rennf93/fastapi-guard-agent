<p align="center">
    <a href="https://rennf93.github.io/fastapi-guard-agent/latest/">
        <img src="https://rennf93.github.io/fastapi-guard-agent/latest/assets/big_logo.svg" alt="FastAPI Guard Agent">
    </a>
</p>

---

<p align="center">
    <strong>FastAPI Guard Agent is an enterprise-grade telemetry and monitoring solution that seamlessly integrates with FastAPI Guard to provide centralized security intelligence. The agent automatically collects security events, performance metrics, and enables real-time security policy updates through a cloud-based management platform.</strong>
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

🌐 **[Website](https://fastapi-guard.com)** - Check out the website!

🎮 **[Join our Discord Community](https://discord.gg/ZW7ZJbjMkK)** - Connect with other developers!

📚 **[Documentation](https://rennf93.github.io/fastapi-guard-agent)** - Full technical documentation and deep dive into its inner workings.

---

Key Features
------------

-   **Automatic Integration**: Seamlessly integrates with FastAPI Guard through a unified configuration interface, requiring minimal setup for comprehensive security monitoring.
-   **High-Performance Architecture**: Built on asynchronous I/O principles to ensure zero performance impact on your application while maintaining real-time data collection capabilities.
-   **Enterprise-Grade Reliability**: Implements industry-standard resilience patterns including circuit breakers, exponential backoff with jitter, and intelligent retry mechanisms to guarantee data delivery.
-   **Intelligent Data Management**: Features multi-tier buffering with in-memory and optional Redis persistence, ensuring zero data loss during network interruptions or application restarts.
-   **Real-Time Security Updates**: Supports dynamic security policy updates from the centralized management platform, enabling immediate threat response without service interruption.
-   **Extensible Architecture**: Designed with protocol-based abstractions, allowing seamless integration with custom transport layers, storage backends, and monitoring systems.
-   **Comprehensive Security Intelligence**: Captures granular security events and performance metrics, providing actionable insights for security operations and compliance requirements.

---

Installation
------------

To install `fastapi-guard-agent`, use pip:

```bash
pip install fastapi-guard-agent
```

---

Getting Started
---------------

Basic Integration
-----------------

The FastAPI Guard Agent is designed for effortless integration with your existing FastAPI Guard security setup. The following example demonstrates the recommended configuration approach:

```python
from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware

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

app = FastAPI()

# Add security middleware - events are sent automatically
middleware = SecurityMiddleware(app, config=config)

@app.get("/")
async def root():
    return {"message": "Hello World"}
```

With this configuration, the agent automatically:
- Captures all security violations including IP bans, rate limit breaches, and suspicious request patterns
- Collects performance telemetry for security operations monitoring
- Synchronizes security policies from the centralized management platform
- Implements intelligent buffering for optimal network utilization
- Provides fault-tolerant operation with automatic recovery mechanisms

---

Advanced Configuration
----------------------

For advanced use cases requiring direct agent control, the FastAPI Guard Agent can be configured using the `AgentConfig` model. This approach is typically used for custom event handling or standalone deployments:

```python
from guard_agent.client import guard_agent
from guard_agent.models import AgentConfig

config = AgentConfig(
    api_key="YOUR_API_KEY",
    project_id="YOUR_PROJECT_ID",
)

agent = guard_agent(config)
```

### Configuration Parameters

#### Authentication & Identification
-   **`api_key: str`** (Required): Authentication key for the FastAPI Guard management platform
-   **`project_id: str | None`**: Unique project identifier for data segregation and multi-tenancy support

#### Network Configuration
-   **`endpoint: str`**: Management platform API endpoint (Default: `https://api.fastapi-guard.com`)
-   **`timeout: int`**: HTTP request timeout in seconds (Default: `30`)
-   **`retry_attempts: int`**: Maximum retry attempts for failed requests (Default: `3`)
-   **`backoff_factor: float`**: Exponential backoff multiplier for retry delays (Default: `1.0`)

#### Data Management
-   **`buffer_size: int`**: Maximum events in memory buffer before automatic flush (Default: `100`)
-   **`flush_interval: int`**: Automatic buffer flush interval in seconds (Default: `30`)
-   **`max_payload_size: int`**: Maximum payload size in bytes before truncation (Default: `1024`)

#### Feature Control
-   **`enable_metrics: bool`**: Enable performance metrics collection (Default: `True`)
-   **`enable_events: bool`**: Enable security event collection (Default: `True`)

#### Security & Privacy
-   **`sensitive_headers: list[str]`**: HTTP headers to redact from collected data (Default: `["authorization", "cookie", "x-api-key"]`)

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