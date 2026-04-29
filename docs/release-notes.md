Release Notes
=============

___

v2.4.0 (2026-04-29)
-------------------

Per-event idempotency keys, configurable overflow policy, and framework-version reporting (v2.4.0)
--------------------------------------------------------------------------------------------------

### Added

- **`SecurityEvent.idempotency_key: UUID`** — every emitted event now carries a stable per-event identifier (default `uuid4()` via `default_factory`). Combined with the existing batch-stable `batch_id`, this lets the SaaS dedup at the event level when an ACK is lost mid-batch and the batch is retried. The field is named `idempotency_key`, not `event_id`, to avoid collision with the SaaS API's existing `event_id` (the prefixed external id, e.g. `evt_abc123`). Backward-compatible: callers that don't set the field automatically get a generated one.
- **`AgentConfig.guard_version: str | None`** — new optional config field set by the framework adapter (e.g. fastapi-guard middleware) at agent init time, identifying the wrapper package's version. Default `None` for callers that construct `AgentConfig` directly without going through a framework wrapper. Framework adapters should set `config.guard_version = framework_package.__version__` immediately before passing the config to `GuardAgentHandler`.
- **`EventBatch.guard_version: str | None`** — propagated through the wire payload on both the plaintext (`/api/v1/events`, `/api/v1/metrics`) and encrypted (`/api/v1/events/encrypted`) ingestion paths. Sourced from `AgentConfig.guard_version`. The SaaS persists this on the project record so analytics can attribute telemetry to the wrapper version, not just the agent version. Without this field the SaaS could only see `agent_version` (guard-agent's own version) and had no way to know which middleware version the customer was running.
- **`encryption._default_json_handler`** now serializes `UUID` values to their string form alongside the existing `datetime` → `isoformat()` branch. Required for the encrypted-payload path to handle events carrying the new `idempotency_key`.
- **`AgentConfig.buffer_overflow_policy: Literal["drop", "block", "raise"] = "drop"`** — operators can now choose how the in-memory event/metric buffer behaves at capacity:
  - `drop` (default) — silent eviction of the oldest entry; preserves prior behavior verbatim. Production-safe for high-throughput; loses events when the SaaS is unreachable.
  - `block` — backpressures the caller until a flush frees space. Appropriate when event integrity is critical. Use only when `start_auto_flush` is wired or a flush callback is in place; otherwise `clear_buffer` is the manual escape hatch.
  - `raise` — `BufferFullError` propagates to the caller. Appropriate for tests or strict environments where dropping events is unacceptable.
- **`BufferFullError(GuardAgentError)`** exception class added in `guard_agent.exceptions` and re-exported from the top-level `guard_agent` module.

### Fixed

- **`HTTPTransport._make_request` was logging the wrong URL on POST failures.** When encryption was enabled, the actual request hit `/api/v1/events/encrypted` but the error log printed the unencrypted endpoint string (`url = f"{endpoint}{plain_path}"`). Operators chasing down 503s and decrypt errors saw `POST .../api/v1/events` in their logs even though the wire request went to `/api/v1/events/encrypted`. Fix: compute the actual posted URL (encrypted vs plain) up-front and pass that to `_log_request_error`. No behavior change beyond log accuracy.

### Compatibility

- Default behavior unchanged for callers that don't opt into either feature: `idempotency_key` has a `default_factory`, and `buffer_overflow_policy` defaults to `"drop"` (which preserves prior eviction semantics including the silent-overflow counter and warning-every-100th log).
- SaaS-side coordination: this release is paired with the SaaS dedup work that ships the `idempotency_key` column on `security_events`, the unique constraint, and the `pg_insert ... on_conflict_do_nothing` ingest path. SaaS deployments that don't yet recognize the field treat it as an unknown column and silently drop the bytes — no behavior change to those callers.

___

v2.2.0 (2026-04-25)
-------------------

TITLE (v2.2.0)
------------

CONTENT

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
