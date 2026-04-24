# FastAPI Adapter — `fastapi-guard`

Guard Agent integrates with FastAPI through the [`fastapi-guard`](https://pypi.org/project/fastapi-guard/) middleware. Because FastAPI is async, the agent's background flush loop needs to be started and stopped from within the app's event loop — this is done via a FastAPI `lifespan` context manager.

## Install

```bash
uv add fastapi-guard guard-agent
```

Alternatives:

```bash
poetry add fastapi-guard guard-agent
```

```bash
pip install fastapi-guard guard-agent
```

## Minimal example

The canonical pattern below mirrors `guard-core-app/examples/app.py`. Key points:

1. Build a `SecurityConfig` with the `agent_*` fields wired to your credentials.
2. Build an explicit `AgentConfig` (same credentials — the `guard_agent()` factory is a singleton, so creating one here gives you a reference for `await agent.start()` / `await agent.stop()`).
3. Wrap both in a `lifespan` async context manager.
4. Attach `SecurityMiddleware` and (optionally) the `SecurityDecorator` to `app.state`.

```python
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from guard import SecurityConfig, SecurityDecorator, SecurityMiddleware
from guard_agent import AgentConfig, guard_agent

api_key = os.environ.get("GUARD_API_KEY", "")
project_id = os.environ.get("GUARD_PROJECT_ID", "")
core_url = os.environ.get("GUARD_CORE_URL", "https://api.guard-core.com")

security_config = SecurityConfig(
    # Security settings
    auto_ban_threshold=5,
    auto_ban_duration=300,
    enable_rate_limiting=True,
    rate_limit=100,
    rate_limit_window=60,

    # Agent telemetry
    enable_agent=bool(api_key),
    agent_api_key=api_key,
    agent_endpoint=core_url,
    agent_project_id=project_id,
    agent_buffer_size=5000,
    agent_flush_interval=2,
    agent_enable_events=True,
    agent_enable_metrics=True,

    # Dynamic rules from the dashboard
    enable_dynamic_rules=bool(api_key),
    dynamic_rule_interval=60,
)

agent_config = AgentConfig(
    api_key=api_key,
    endpoint=core_url,
    project_id=project_id,
    buffer_size=5000,
    flush_interval=2,
)

agent = guard_agent(agent_config) if api_key else None
guard = SecurityDecorator(security_config)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    if agent:
        await agent.start()
    yield
    if agent:
        await agent.stop()


app = FastAPI(title="Example App", lifespan=lifespan)
app.add_middleware(SecurityMiddleware, config=security_config)
SecurityMiddleware.configure_cors(app, security_config)
app.state.guard_decorator = guard


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello, Guard!"}
```

## Why `lifespan` is required

`SecurityMiddleware` creates the `GuardAgentHandler` eagerly when `config.enable_agent=True`, but it does **not** start the handler's async flush loop on its own. Without `await agent.start()` running inside the FastAPI event loop, events buffer indefinitely and never flush to the dashboard. The `lifespan` context manager is the correct place to drive this lifecycle.

If you skip the explicit `AgentConfig` and only wire credentials through `SecurityConfig`, the middleware still creates a handler (via `SecurityConfig.to_agent_config()` internally). You can still drive its lifecycle from `lifespan` by retrieving the handler from the middleware after install, but the explicit pattern above is clearer and matches the canonical example in `guard-core-app/examples/`.

## Dashboard & Playground

- Obtain your API key and project ID at [**app.guard-core.com**](https://app.guard-core.com).
- Try the full stack without installing anything at [**playground.guard-core.com**](https://playground.guard-core.com).

## Related

- [`fastapi-guard` on GitHub](https://github.com/rennf93/fastapi-guard)
- [`fastapi-guard` documentation](https://rennf93.github.io/fastapi-guard/)
- [Canonical full example](https://github.com/rennf93/guard-core-app/blob/master/examples/app.py) in `guard-core-app`
