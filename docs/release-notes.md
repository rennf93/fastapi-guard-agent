Release Notes
=============

___

v2.1.0 (2026-04-24)
-------------------

Multi-Adapter Coverage (v2.1.0)
-------------------------------
- Added per-adapter integration smoke tests: `tests/test_adapter_fastapi.py`, `test_adapter_flask.py`, `test_adapter_django.py`. Each verifies `SecurityConfig.to_agent_config()` roundtrip and request delivery through the adapter's middleware with `enable_agent=True`.
- Added per-adapter documentation pages under `docs/adapters/`: FastAPI, Flask, Django, Tornado. Each page covers install, minimal example, and agent wiring specific to that framework.
- `mkdocs.yml` navigation updated with a new top-level **Adapters** section.

Dependency Changes (v2.1.0)
---------------------------
- Added `django`, `djapi-guard>=2.0.0`, `flask`, `flaskapi-guard>=2.0.0`, `tornado` to `[project.optional-dependencies].dev` so the test suite can exercise every adapter.
- `tornadoapi-guard` is not yet included in dev extras — it has not been published to PyPI (only a yanked 0.0.1 exists). Integration tests for Tornado are stubbed with `pytest.mark.skip` in `tests/test_adapter_tornado.py`. Re-enable once the adapter ships a 1.0.0+ release.

___

v2.0.0 (2026-04-24)
-------------------

Package Rename (v2.0.0)
-----------------------
- **Renamed on PyPI**: `fastapi-guard-agent` → `guard-agent`. The Python import path (`from guard_agent import ...`) is unchanged — no code changes are required in consuming applications.
- Repositioned as a framework-agnostic telemetry agent serving `fastapi-guard`, `flaskapi-guard`, `djangoapi-guard`, and `tornadoapi-guard`.
- **Legacy name preserved**: a meta-package `fastapi-guard-agent==1.2.0` is published alongside this release, whose only dependency is `guard-agent>=2.0.0,<3.0.0`. Existing `pip install fastapi-guard-agent` invocations continue to resolve correctly and pull the renamed distribution transitively.
- Repository renamed on GitHub: `rennf93/fastapi-guard-agent` → `rennf93/guard-agent`. GitHub auto-redirects the old URLs.
- Documentation site moved to `https://rennf93.github.io/guard-agent/`.

Dependency Changes (v2.0.0)
---------------------------
- Removed `fastapi` and `fastapi-guard` from runtime dependencies — the agent is framework-agnostic and speaks HTTP to the dashboard, not to any web framework.
- Runtime deps are now: `cryptography`, `httpx`, `pydantic`, `typing-extensions`.
- `fastapi` and `fastapi-guard` remain as dev extras so the existing test suite keeps passing. Each framework adapter brings its own web framework.
- Dropped `Framework :: FastAPI` classifier; development status promoted from `Alpha` to `Beta`.

Breaking Changes (v2.0.0)
-------------------------
- **None in Python API** — `from guard_agent import ...`, `GuardAgentHandler`, `AgentConfig`, and every public symbol behave identically.
- **Distribution name change only**: scripts, Dockerfiles, and lockfiles that install `fastapi-guard-agent` directly should migrate to `guard-agent`. The shim keeps old commands working but new projects should install `guard-agent` directly.

Migration Guide (v2.0.0)
------------------------
- Existing code: no changes.
- Install commands (uv): replace `uv add fastapi-guard-agent` with `uv add guard-agent` at your leisure — both resolve to the same underlying package.
- Poetry / pip equivalents: `poetry add guard-agent` / `pip install guard-agent`.
- Lockfiles: running `uv lock`, `poetry lock`, or `pip-compile` after bumping will transparently update entries to `guard-agent`.

___

v1.1.1 (2026-03-11)
-------------------

Bug Fixes (v1.1.1)
-------------------
- Fixed misalignment on documentation headers and model parameters.
- Added support for Python 3.14.

Maintenance (v1.1.1)
--------------------
- Code alignment and cleanup.

___

v1.1.0 (2025-10-14)
-------------------

New Features (v1.1.0)
---------------------
- Added end-to-end payload encryption for secure telemetry transmission using AES-256-GCM.
- Implemented `PayloadEncryptor` class with project-specific encryption keys.
- Added encrypted endpoint support for events and metrics (`/api/v1/events/encrypted`).
- Integrated automatic datetime serialization in encrypted payloads via custom JSON handler.
- Added encryption key verification during transport initialization.

Technical Details (v1.1.0)
--------------------------
- Encryption uses AES-256-GCM with 96-bit nonces and 128-bit authentication tags.
- Pydantic models are serialized using `.model_dump(mode="json")` before encryption.
- Custom `_default_json_handler` ensures datetime objects are properly ISO-formatted.

___

v1.0.2 (2025-09-12)
-------------------

Enhancements (v1.0.2)
---------------------
- Added dynamic rule updated event type.

___

v1.0.1 (2025-08-07)
-------------------

Enhancements (v1.0.1)
------------
- Added path_excluded event type.

___

v1.0.0 (2025-07-24)
-------------------

**Official Release**

___

v0.1.1 (2025-07-09)
-------------------

Enhancements (v0.1.1)
---------------------
- Standardized Redis Protocl/Manager methods across libraries.

___

v0.1.0 (2025-07-08)
-------------------

Enhancements (v0.1.0)
---------------------
- Switched from aiohttp to httpx for HTTP client.
- Completed implementation.
- 100% test coverage.

___

v0.0.1 (2025-06-22)
-------------------

New Features (v0.0.1)
---------------------
- Initial release FastAPI Guard Agent.
