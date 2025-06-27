from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from guard_agent.buffer import EventBuffer
from guard_agent.models import AgentConfig, SecurityEvent, SecurityMetric


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
def mock_session() -> AsyncMock:
    """Create a mock aiohttp session."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"status": "ok"})
    mock_response.text = AsyncMock(return_value="OK")

    # Create a proper context manager
    class MockContextManager:
        def __init__(self, response):
            self.response = response

        async def __aenter__(self):
            return self.response

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_session = AsyncMock()
    mock_session.post = MagicMock(return_value=MockContextManager(mock_response))
    mock_session.get = MagicMock(return_value=MockContextManager(mock_response))
    mock_session.closed = False
    mock_session.close = AsyncMock()

    return mock_session


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
