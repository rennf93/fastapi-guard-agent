from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

# Monkey-patch the guard library to include AgentConfig import
# This is needed because the guard library's SecurityConfig.to_agent_config()
# method references AgentConfig without importing it
import guard.models
import pytest

from guard_agent.buffer import EventBuffer
from guard_agent.models import AgentConfig, SecurityEvent, SecurityMetric

setattr(guard.models, "AgentConfig", AgentConfig)  # noqa: B010


@pytest.fixture
def agent_config() -> AgentConfig:
    """Create a test agent configuration."""
    return AgentConfig(
        api_key="test-api-key",
        endpoint="http://localhost:8000",
        project_id="test-project",
        buffer_size=10,
        flush_interval=1,
        timeout=5,
        retry_attempts=1,
    )


@pytest.fixture
def mock_redis_handler() -> AsyncMock:
    """Create a mock Redis handler."""
    mock = AsyncMock()
    mock.get_key = AsyncMock(return_value=None)
    mock.set_key = AsyncMock(return_value=True)
    mock.delete_key = AsyncMock(return_value=True)
    mock.keys = AsyncMock(return_value=[])
    mock.initialize = AsyncMock()
    return mock


@pytest.fixture
def mock_transport() -> AsyncMock:
    """Create a mock HTTP transport."""
    mock = AsyncMock()
    mock.initialize = AsyncMock()
    mock.close = AsyncMock()
    mock.send_events = AsyncMock(return_value=True)
    mock.send_metrics = AsyncMock(return_value=True)
    mock.fetch_dynamic_rules = AsyncMock(return_value=None)
    mock.send_status = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_client() -> AsyncMock:
    """Create a mock httpx client."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={"status": "ok"})
    mock_response.text = "OK"
    mock_response.headers = {}
    mock_response.url = "http://localhost:8000/test"

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.is_closed = False
    mock_client.aclose = AsyncMock()

    return mock_client


@pytest.fixture
def buffer(agent_config: AgentConfig) -> EventBuffer:
    """Create a test EventBuffer instance."""
    return EventBuffer(config=agent_config)


@pytest.fixture
def security_event() -> SecurityEvent:
    """Create a sample security event."""
    return SecurityEvent(
        timestamp=datetime.now(timezone.utc),
        event_type="ip_banned",
        ip_address="127.0.0.1",
        action_taken="block",
        reason="test",
    )


@pytest.fixture
def security_metric() -> SecurityMetric:
    """Create a sample security metric."""
    return SecurityMetric(
        timestamp=datetime.now(timezone.utc),
        metric_type="request_count",
        value=1.0,
    )
