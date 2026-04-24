"""Integration smoke tests for the Tornado adapter (tornadoapi-guard).

Placeholder module. The ``tornadoapi-guard`` package is not yet published to
PyPI (only a yanked 0.0.1 exists as of guard-agent 2.1.0). Once the adapter
ships a 1.0.0+ release, add ``tornadoapi-guard>=1.0.0`` to the dev extras in
``pyproject.toml`` and replace these skipped tests with real coverage mirroring
``test_adapter_fastapi``: config roundtrip + request roundtrip.
"""

import pytest

pytestmark = pytest.mark.skip(
    reason="tornadoapi-guard is not yet published to PyPI; "
    "re-enable once a 1.0.0+ release ships."
)


class TestTornadoAdapterIntegration:
    """Agent wiring via tornadoapi-guard (Tornado adapter) — pending publish."""

    def test_security_config_produces_agent_config(self) -> None:
        raise AssertionError("Unreachable — module-level skip.")

    def test_app_with_agent_enabled_serves_requests(self) -> None:
        raise AssertionError("Unreachable — module-level skip.")
