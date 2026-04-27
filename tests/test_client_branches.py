from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guard_agent.client import GuardAgentHandler
from guard_agent.models import AgentConfig


@pytest.fixture(autouse=True)
def reset_singleton() -> Generator[None, None, None]:
    GuardAgentHandler._instance = None
    yield
    GuardAgentHandler._instance = None


@pytest.mark.asyncio
async def test_get_dynamic_rules_returns_none_when_fetch_returns_none(
    agent_config: AgentConfig,
) -> None:
    handler = GuardAgentHandler(agent_config)
    handler.transport = AsyncMock()
    handler.transport.fetch_dynamic_rules.return_value = None

    result = await handler.get_dynamic_rules()

    assert result is None
    assert handler._cached_rules is None
    assert handler.rules_fetched == 0


@pytest.mark.asyncio
async def test_flush_buffer_no_events_no_metrics(agent_config: AgentConfig) -> None:
    handler = GuardAgentHandler(agent_config)
    handler.buffer = AsyncMock()
    handler.transport = AsyncMock()
    handler.buffer.flush_events_with_keys.return_value = ([], [])
    handler.buffer.flush_metrics_with_keys.return_value = ([], [])

    await handler.flush_buffer()

    handler.transport.send_events.assert_not_called()
    handler.transport.send_metrics.assert_not_called()
    assert handler.events_sent == 0
    assert handler.metrics_sent == 0


@pytest.mark.asyncio
async def test_flush_buffer_no_events_with_metrics(agent_config: AgentConfig) -> None:
    handler = GuardAgentHandler(agent_config)
    handler.buffer = AsyncMock()
    handler.transport = AsyncMock()
    handler.buffer.flush_events_with_keys.return_value = ([], [])
    handler.buffer.flush_metrics_with_keys.return_value = ([MagicMock()], ["mk1"])
    handler.transport.send_metrics.return_value = True

    await handler.flush_buffer()

    handler.transport.send_events.assert_not_called()
    handler.transport.send_metrics.assert_called_once()
    assert handler.metrics_sent == 1


@pytest.mark.asyncio
async def test_get_status_failure_rate_below_threshold(
    agent_config: AgentConfig,
) -> None:
    handler = GuardAgentHandler(agent_config)
    handler.buffer = AsyncMock()
    handler.buffer.get_buffer_size.return_value = 1
    handler.buffer.get_stats = MagicMock(return_value={"last_flush_time": None})
    handler.transport = AsyncMock()
    handler.transport.get_stats = MagicMock(
        return_value={"circuit_breaker_state": "CLOSED"}
    )
    handler.events_failed = 1
    handler.metrics_failed = 0
    handler.events_sent = 100
    handler.metrics_sent = 100

    status = await handler.get_status()

    assert status.status == "healthy"
    assert not any("High failure rate" in e for e in status.errors)


@pytest.mark.asyncio
async def test_status_loop_running_false_after_sleep_skips_status(
    agent_config: AgentConfig,
) -> None:
    handler = GuardAgentHandler(agent_config)
    handler._running = True
    handler.transport = AsyncMock()

    call_count = 0

    async def mock_sleep(_: float) -> None:
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            handler._running = False

    with patch("guard_agent.client.asyncio.sleep", side_effect=mock_sleep):
        with patch.object(handler, "get_status", new_callable=AsyncMock) as mock_status:
            await handler._status_loop()
            mock_status.assert_not_called()


@pytest.mark.asyncio
async def test_rules_loop_running_false_after_sleep_skips_rules(
    agent_config: AgentConfig,
) -> None:
    handler = GuardAgentHandler(agent_config)
    handler._running = True

    call_count = 0

    async def mock_sleep(_: float) -> None:
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            handler._running = False

    with patch("guard_agent.client.asyncio.sleep", side_effect=mock_sleep):
        with patch.object(
            handler, "get_dynamic_rules", new_callable=AsyncMock
        ) as mock_rules:
            await handler._rules_loop()
            mock_rules.assert_not_called()


@pytest.mark.asyncio
async def test_health_check_true_when_no_attempts(agent_config: AgentConfig) -> None:
    handler = GuardAgentHandler(agent_config)
    handler._running = True
    handler.buffer = AsyncMock()
    handler.buffer.get_buffer_size = AsyncMock(return_value=1)
    handler.transport = MagicMock()
    handler.transport.get_stats = MagicMock(
        return_value={"circuit_breaker_state": "CLOSED"}
    )
    handler.events_sent = 0
    handler.metrics_sent = 0
    handler.events_failed = 0
    handler.metrics_failed = 0

    result = await handler.health_check()

    assert result is True
