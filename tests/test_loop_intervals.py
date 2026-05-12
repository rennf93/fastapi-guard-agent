from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from guard_agent.client import GuardAgentHandler
from guard_agent.models import AgentConfig


class TestAgentConfigIntervalFields:
    def test_dynamic_rule_interval_and_status_interval_persist(self) -> None:
        config = AgentConfig(
            api_key="test-api-key",
            dynamic_rule_interval=600,
            status_interval=900,
        )

        assert config.dynamic_rule_interval == 600
        assert config.status_interval == 900

    def test_dynamic_rule_interval_default_is_300(self) -> None:
        config = AgentConfig(api_key="test-api-key")

        assert config.dynamic_rule_interval == 300

    def test_status_interval_default_is_300(self) -> None:
        config = AgentConfig(api_key="test-api-key")

        assert config.status_interval == 300

    def test_dynamic_rule_interval_below_60_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentConfig(api_key="test-api-key", dynamic_rule_interval=30)

    def test_status_interval_below_60_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AgentConfig(api_key="test-api-key", status_interval=30)


class TestLoopHonorsConfiguredInterval:
    @pytest.mark.asyncio
    async def test_rules_loop_sleeps_for_configured_interval(self) -> None:
        config = AgentConfig(
            api_key="test-api-key",
            project_id="test-project",
            dynamic_rule_interval=777,
        )
        handler = GuardAgentHandler(config)
        handler.config = config
        handler._running = True

        sleep_calls: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)
            handler._running = False

        with (
            patch.object(handler, "get_dynamic_rules", new_callable=AsyncMock),
            patch("guard_agent.client.asyncio.sleep", side_effect=fake_sleep),
        ):
            await handler._rules_loop()

        assert sleep_calls == [777]

    @pytest.mark.asyncio
    async def test_status_loop_sleeps_for_configured_interval(self) -> None:
        config = AgentConfig(
            api_key="test-api-key",
            project_id="test-project",
            status_interval=888,
        )
        handler = GuardAgentHandler(config)
        handler.config = config
        handler.transport = AsyncMock()
        handler._running = True

        sleep_calls: list[float] = []

        async def fake_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)
            handler._running = False

        with (
            patch.object(handler, "get_status", new_callable=AsyncMock),
            patch("guard_agent.client.asyncio.sleep", side_effect=fake_sleep),
        ):
            await handler._status_loop()

        assert sleep_calls == [888]
