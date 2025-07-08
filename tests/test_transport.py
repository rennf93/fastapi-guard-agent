import asyncio
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from guard_agent.models import AgentConfig, AgentStatus, SecurityEvent, SecurityMetric
from guard_agent.transport import HTTPTransport


class TestHTTPTransport:
    """Tests for HTTPTransport class."""

    @pytest.mark.asyncio
    async def test_initialization(self, agent_config: AgentConfig) -> None:
        """Test transport initialization."""
        transport = HTTPTransport(agent_config)

        with patch("httpx.AsyncClient") as mock_client:
            await transport.initialize()

            # Verify client was created
            mock_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialization_failure(self, agent_config: AgentConfig) -> None:
        """Test transport initialization failure."""
        transport = HTTPTransport(agent_config)

        with patch("httpx.AsyncClient", side_effect=Exception("Test Init Error")):
            with pytest.raises(Exception, match="Test Init Error"):
                await transport.initialize()

    @pytest.mark.asyncio
    async def test_send_events_success(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test successful event sending."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        events = [
            SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="ip_banned",
                ip_address="192.168.1.1",
                action_taken="banned",
                reason="test",
            )
        ]

        result = await transport.send_events(events)

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_events_failure(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test event sending failure handling."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        # Configure mock for failure response
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client.post.return_value = mock_response

        events = [
            SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="ip_banned",
                ip_address="192.168.1.1",
                action_taken="banned",
                reason="test",
            )
        ]

        result = await transport.send_events(events)

        assert result is False

    @pytest.mark.asyncio
    async def test_send_events_exception_during_send(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test send_events when an exception occurs during the send process."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        with patch.object(
            transport,
            "_send_with_retry",
            side_effect=Exception("Test Send Events Exception"),
        ):
            events = [
                SecurityEvent(
                    timestamp=datetime.now(timezone.utc),
                    event_type="ip_banned",
                    ip_address="192.168.1.1",
                    action_taken="banned",
                    reason="test",
                )
            ]

            result = await transport.send_events(events)
            assert result is False
            assert transport.requests_failed == 1

    @pytest.mark.asyncio
    async def test_send_metrics_exception_during_send(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test send_metrics when an exception occurs during the send process."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        with patch.object(
            transport,
            "_send_with_retry",
            side_effect=Exception("Test Send Metrics Exception"),
        ):
            metrics = [
                SecurityMetric(
                    timestamp=datetime.now(timezone.utc),
                    metric_type="request_count",
                    value=1.0,
                )
            ]

            result = await transport.send_metrics(metrics)
            assert result is False
            assert transport.requests_failed == 1

    @pytest.mark.asyncio
    async def test_rate_limiting(self, agent_config: AgentConfig) -> None:
        """Test rate limiting functionality."""
        transport = HTTPTransport(agent_config)

        # Verify rate limiter is working
        assert transport.rate_limiter.max_calls == 100
        assert transport.rate_limiter.time_window == 60.0

    @pytest.mark.asyncio
    async def test_circuit_breaker(self, agent_config: AgentConfig) -> None:
        """Test circuit breaker functionality."""
        transport = HTTPTransport(agent_config)

        # Verify circuit breaker is configured
        assert transport.circuit_breaker.failure_threshold == 5
        assert transport.circuit_breaker.recovery_timeout == 60.0

    @pytest.mark.asyncio
    async def test_retry_logic(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test retry logic for failed requests."""
        agent_config.retry_attempts = 2
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        # Configure mock for retry logic - first call fails, second succeeds
        call_count = 0

        def create_mock_response(*args: Any, **kwargs: Any) -> AsyncMock:
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock()
            if call_count == 1:
                # First call fails
                mock_response.status_code = 500
                mock_response.text = "Server Error"
            else:
                # Second call succeeds
                mock_response.status_code = 200
                mock_response.json = MagicMock(return_value={"status": "ok"})
            return mock_response

        mock_client.post.side_effect = create_mock_response

        events = [
            SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="ip_banned",
                ip_address="192.168.1.1",
                action_taken="banned",
                reason="test",
            )
        ]

        with patch("asyncio.sleep"):  # Skip actual sleep delays
            result = await transport.send_events(events)

        assert result is True
        assert call_count == 2  # One retry

    @pytest.mark.asyncio
    async def test_send_with_retry_all_attempts_fail(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test _send_with_retry when all retry attempts fail."""
        agent_config.retry_attempts = 2
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        mock_client.post.side_effect = httpx.HTTPError("Simulated Network Error")

        events = [
            SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="ip_banned",
                ip_address="192.168.1.1",
                action_taken="banned",
                reason="test",
            )
        ]

        with patch("asyncio.sleep"):
            result = await transport.send_events(events)

        assert result is False
        assert transport.requests_failed == 1
        assert mock_client.post.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_send_with_retry_make_request_returns_false(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """
        Test _send_with_retry when _make_request returns False (e.g., client error).
        """
        agent_config.retry_attempts = 0  # No retries
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        with patch.object(
            transport, "_make_request", return_value=False
        ) as mock_make_request:
            events = [
                SecurityEvent(
                    timestamp=datetime.now(timezone.utc),
                    event_type="ip_banned",
                    ip_address="192.168.1.1",
                    action_taken="banned",
                    reason="test",
                )
            ]
            result = await transport.send_events(events)

            assert result is False
            assert transport.requests_failed == 1
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_with_retry_make_request_returns_none(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test _get_with_retry when _make_request returns None (e.g., no rules)."""
        agent_config.retry_attempts = 0  # No retries
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        with patch.object(
            transport, "_make_request", return_value=None
        ) as mock_make_request:
            rules = await transport.fetch_dynamic_rules()

            assert rules is None
            assert transport.requests_failed == 1
            mock_make_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_session_init_fails(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _make_request when session initialization fails."""
        transport = HTTPTransport(agent_config)
        transport._client = None

        with patch.object(
            transport, "initialize", side_effect=Exception("Init Failed")
        ):
            with pytest.raises(Exception, match="Init Failed"):
                await transport._make_request("POST", "/test", {"key": "value"})

    @pytest.mark.asyncio
    async def test_fetch_dynamic_rules(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test fetching dynamic rules."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        # Configure mock for dynamic rules response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "rule_id": "test-rule-123",
                "version": 1,
                "timestamp": "2025-01-08T10:00:00Z",
                "ip_blacklist": ["192.168.1.1"],
                "ttl": 300,
            }
        )
        mock_client.get.return_value = mock_response

        rules = await transport.fetch_dynamic_rules()

        assert rules is not None
        assert rules.rule_id == "test-rule-123"
        assert rules.version == 1
        assert "192.168.1.1" in rules.ip_blacklist

    @pytest.mark.asyncio
    async def test_fetch_dynamic_rules_failure(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test fetching dynamic rules failure."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client
        mock_client.get.side_effect = Exception("Test Fetch Rules Exception")

        rules = await transport.fetch_dynamic_rules()
        assert rules is None

    @pytest.mark.asyncio
    async def test_send_status(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test sending agent status."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        # Configure mock for status response
        mock_response = AsyncMock()
        mock_response.status_code = 201
        mock_client.post.return_value = mock_response

        status = AgentStatus(
            timestamp=datetime.now(timezone.utc),
            status="healthy",
            uptime=3600.0,
            events_sent=100,
            events_failed=0,
            buffer_size=5,
        )

        result = await transport.send_status(status)

        assert result is True

    @pytest.mark.asyncio
    async def test_authentication_header(self, agent_config: AgentConfig) -> None:
        """Test that authentication headers are properly set."""
        transport = HTTPTransport(agent_config)

        with patch("httpx.AsyncClient") as mock_client_class:
            await transport.initialize()

            # Check that session was created with auth header
            call_args = mock_client_class.call_args
            headers = call_args[1]["headers"]

            assert "Authorization" in headers
            assert headers["Authorization"] == f"Bearer {agent_config.api_key}"

    def test_get_stats(self, agent_config: AgentConfig) -> None:
        """Test getting transport statistics."""
        transport = HTTPTransport(agent_config)

        stats = transport.get_stats()

        assert isinstance(stats, dict)
        assert "requests_sent" in stats
        assert "requests_failed" in stats
        assert "bytes_sent" in stats
        assert "circuit_breaker_state" in stats

    @pytest.mark.asyncio
    async def test_close(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test transport cleanup."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        await transport.close()

        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test that initialize does nothing if already initialized."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client  # Simulate already initialized client

        with patch("httpx.AsyncClient") as mock_client_class:
            await transport.initialize()
            mock_client_class.assert_not_called()  # Should not create a new client

    @pytest.mark.asyncio
    async def test_send_events_empty_list(self, agent_config: AgentConfig) -> None:
        """Test send_events with an empty list."""
        transport = HTTPTransport(agent_config)
        result = await transport.send_events([])
        assert result is True  # Should return True for empty list

    @pytest.mark.asyncio
    async def test_send_metrics_empty_list(self, agent_config: AgentConfig) -> None:
        """Test send_metrics with an empty list."""
        transport = HTTPTransport(agent_config)
        result = await transport.send_metrics([])
        assert result is True  # Should return True for empty list

    @pytest.mark.asyncio
    async def test_get_with_retry_rate_limited(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test _get_with_retry when rate limited."""
        agent_config.retry_attempts = 1
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        with patch.object(transport.rate_limiter, "acquire", side_effect=[False, True]):
            with patch("asyncio.sleep"):
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(return_value={"status": "ok"})
                mock_client.get.return_value = mock_response

                rules = await transport.fetch_dynamic_rules()
                assert rules is not None
                assert transport.requests_sent == 1

    @pytest.mark.asyncio
    async def test_make_request_client_none_after_initialize(
        self, agent_config: AgentConfig
    ) -> None:
        """
        Test _make_request when client is None initially, but initialized successfully.
        """
        transport = HTTPTransport(agent_config)
        transport._client = None  # Ensure client is None

        with patch.object(
            transport, "initialize", wraps=transport.initialize
        ) as mock_initialize:
            with patch("httpx.AsyncClient.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(return_value={"status": "ok"})
                mock_post.return_value = mock_response

                result = await transport._make_request(
                    "POST", "/test", {"key": "value"}
                )
                assert result == {"status": "ok"}
                mock_initialize.assert_called_once()
                mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_with_retry_rate_limited(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test _send_with_retry when rate limited."""
        agent_config.retry_attempts = 1
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        with patch.object(transport.rate_limiter, "acquire", side_effect=[False, True]):
            with patch("asyncio.sleep"):
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(return_value={"status": "ok"})
                mock_client.post.return_value = mock_response

                events = [
                    SecurityEvent(
                        timestamp=datetime.now(timezone.utc),
                        event_type="ip_banned",
                        ip_address="192.168.1.1",
                        action_taken="banned",
                        reason="test",
                    )
                ]
                result = await transport.send_events(events)
                assert result is True
                assert transport.requests_sent == 1

    @pytest.mark.asyncio
    async def test_send_with_retry_circuit_breaker_open(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test _send_with_retry when circuit breaker is open."""
        agent_config.retry_attempts = 0
        transport = HTTPTransport(agent_config)
        transport._client = mock_client
        transport.circuit_breaker.state = "OPEN"

        events = [
            SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="ip_banned",
                ip_address="192.168.1.1",
                action_taken="banned",
                reason="test",
            )
        ]
        result = await transport.send_events(events)
        assert result is False
        assert transport.requests_failed == 1

    @pytest.mark.asyncio
    async def test_make_request_client_none(self, agent_config: AgentConfig) -> None:
        """Test _make_request when client is None initially."""
        transport = HTTPTransport(agent_config)
        transport._client = None  # Ensure client is None

        with patch.object(
            transport, "initialize", wraps=transport.initialize
        ) as mock_initialize:
            with patch("httpx.AsyncClient.post") as mock_post:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(return_value={"status": "ok"})
                mock_post.return_value = mock_response

                result = await transport._make_request(
                    "POST", "/test", {"key": "value"}
                )
                assert result == {"status": "ok"}
                mock_initialize.assert_called_once()
                mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_client_error(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test _make_request with httpx.HTTPError."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client
        mock_client.post.side_effect = httpx.HTTPError("Test Client Error")

        with pytest.raises(httpx.HTTPError):
            await transport._make_request("POST", "/test", {"key": "value"})

    @pytest.mark.asyncio
    async def test_make_request_timeout_error(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test _make_request with asyncio.TimeoutError."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client
        mock_client.post.side_effect = asyncio.TimeoutError("Test Timeout Error")

        with pytest.raises(asyncio.TimeoutError):
            await transport._make_request("POST", "/test", {"key": "value"})

    @pytest.mark.asyncio
    async def test_make_request_generic_exception(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test _make_request with a generic Exception."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client
        mock_client.post.side_effect = Exception("Generic Error")

        with pytest.raises(Exception, match="Generic Error"):
            await transport._make_request("POST", "/test", {"key": "value"})

    @pytest.mark.asyncio
    async def test_make_request_unsupported_method(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _make_request with an unsupported HTTP method."""
        transport = HTTPTransport(agent_config)
        with pytest.raises(ValueError, match="Unsupported method: PUT"):
            await transport._make_request("PUT", "/test", {"key": "value"})

    @pytest.mark.asyncio
    async def test_handle_response_200_non_json(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _handle_response with 200 status and non-JSON content."""
        transport = HTTPTransport(agent_config)
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(side_effect=Exception("Not JSON"))
        mock_response.url = "http://test.com"

        result = await transport._handle_response(mock_response)
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_response_200_non_dict_json(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _handle_response with 200 status and valid JSON that's not a dict."""
        transport = HTTPTransport(agent_config)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.url = "http://test.com"

        # Test with JSON array
        mock_response.json = MagicMock(return_value=["item1", "item2", "item3"])
        result = await transport._handle_response(mock_response)
        assert result is True

        # Test with JSON string
        mock_response.json = MagicMock(return_value="just a string")
        result = await transport._handle_response(mock_response)
        assert result is True

        # Test with JSON number
        mock_response.json = MagicMock(return_value=123)
        result = await transport._handle_response(mock_response)
        assert result is True

        # Test with JSON boolean
        mock_response.json = MagicMock(return_value=True)
        result = await transport._handle_response(mock_response)
        assert result is True

        # Test with JSON null
        mock_response.json = MagicMock(return_value=None)
        result = await transport._handle_response(mock_response)
        assert result is True

    @pytest.mark.asyncio
    async def test_handle_response_429_rate_limited(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _handle_response with 429 status (Rate Limited)."""
        transport = HTTPTransport(agent_config)
        mock_response = AsyncMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}
        mock_response.url = "http://test.com"

        with pytest.raises(Exception, match="Rate limited by server, retry after 120s"):
            await transport._handle_response(mock_response)

    @pytest.mark.asyncio
    async def test_handle_response_401_unauthorized(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _handle_response with 401 status (Unauthorized)."""
        transport = HTTPTransport(agent_config)
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_response.url = "http://test.com"

        with pytest.raises(Exception, match="Authentication failed: 401"):
            await transport._handle_response(mock_response)

    @pytest.mark.asyncio
    async def test_handle_response_403_forbidden(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _handle_response with 403 status (Forbidden)."""
        transport = HTTPTransport(agent_config)
        mock_response = AsyncMock()
        mock_response.status_code = 403
        mock_response.url = "http://test.com"

        with pytest.raises(Exception, match="Authentication failed: 403"):
            await transport._handle_response(mock_response)

    @pytest.mark.asyncio
    async def test_handle_response_500_server_error(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _handle_response with 500 status (Server Error)."""
        transport = HTTPTransport(agent_config)
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.url = "http://test.com"

        with pytest.raises(Exception, match="Server error 500: Internal Server Error"):
            await transport._handle_response(mock_response)

    @pytest.mark.asyncio
    async def test_handle_response_other_client_error(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _handle_response with other client errors (e.g., 404)."""
        transport = HTTPTransport(agent_config)
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.url = "http://test.com"

        result = await transport._handle_response(mock_response)
        assert result is False

    @pytest.mark.asyncio
    async def test_close_client_closed(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test close method closes the client."""
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        await transport.close()

        mock_client.aclose.assert_called_once()

    def test_get_stats_session_closed(self, agent_config: AgentConfig) -> None:
        """Test get_stats when session is closed."""
        transport = HTTPTransport(agent_config)
        transport._client = AsyncMock()
        transport._client.is_closed = True

        stats = transport.get_stats()
        assert stats["session_closed"] is True

    def test_get_stats_session_none(self, agent_config: AgentConfig) -> None:
        """Test get_stats when session is None."""
        transport = HTTPTransport(agent_config)
        transport._client = None

        stats = transport.get_stats()
        assert stats["session_closed"] is True

    @pytest.mark.asyncio
    async def test_get_with_retry_rate_limited_fetch_rules(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """Test _get_with_retry rate limiting in fetch_dynamic_rules path."""
        agent_config.retry_attempts = 1
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        # Mock rate limiter to be rate limited on first call, then succeed
        with patch.object(
            transport.rate_limiter, "acquire", side_effect=[False, True]
        ) as mock_acquire:
            with patch.object(
                transport.rate_limiter, "get_retry_after", return_value=0.1
            ) as mock_get_retry_after:
                with patch("asyncio.sleep") as mock_sleep:
                    mock_response = AsyncMock()
                    mock_response.status_code = 200
                    mock_response.json = MagicMock(
                        return_value={
                            "rule_id": "test-rule",
                            "version": 1,
                            "timestamp": "2025-01-08T10:00:00Z",
                            "ip_blacklist": [],
                            "ttl": 300,
                        }
                    )
                    mock_client.get.return_value = mock_response

                    rules = await transport.fetch_dynamic_rules()

                    # Verify the rate limiting code was executed
                    assert (
                        mock_acquire.call_count == 2
                    )  # Called twice due to rate limiting
                    mock_get_retry_after.assert_called_once()  # Should get retry delay
                    mock_sleep.assert_called_once_with(
                        0.1
                    )  # Should sleep for retry delay

                    # Verify the request eventually succeeded
                    assert rules is not None
                    assert rules.rule_id == "test-rule"

    @pytest.mark.asyncio
    async def test_make_request_client_remains_none_after_initialize(
        self, agent_config: AgentConfig
    ) -> None:
        """Test _make_request when client remains None even after initialize."""
        transport = HTTPTransport(agent_config)
        transport._client = None

        # Mock initialize to succeed but leave session as None
        async def mock_initialize() -> None:
            # Simulate initialize succeeding but client somehow ending up None
            pass

        with patch.object(transport, "initialize", side_effect=mock_initialize):
            with pytest.raises(Exception, match="Failed to initialize HTTP client"):
                await transport._make_request("POST", "/test", {"key": "value"})

    @pytest.mark.asyncio
    async def test_fetch_dynamic_rules_invalid_response_data(
        self, agent_config: AgentConfig, mock_client: AsyncMock
    ) -> None:
        """
        Test fetch_dynamic_rules, response data is invalid, causes parsing to fail.
        """
        transport = HTTPTransport(agent_config)
        transport._client = mock_client

        # return invalid data that will cause DynamicRules(**response_data) to fail
        # Using invalid data types that will cause Pydantic validation errors
        invalid_response_data = {
            "version": "not_an_integer",  # version expects int
            "timestamp": "invalid_datetime_format",  # timestamp expects datetime
            "ttl": "not_an_integer",  # ttl expects int
        }

        with patch.object(
            transport, "_get_with_retry", return_value=invalid_response_data
        ):
            rules = await transport.fetch_dynamic_rules()

            # Should return None due to exception in DynamicRules parsing
            assert rules is None

    @pytest.mark.asyncio
    async def test_transport_interface_compatibility(
        self, mock_transport: AsyncMock
    ) -> None:
        """
        Test that mock_transport fixture provides the expected transport interface.
        """
        # Verify all expected methods are available
        assert hasattr(mock_transport, "initialize")
        assert hasattr(mock_transport, "close")
        assert hasattr(mock_transport, "send_events")
        assert hasattr(mock_transport, "send_metrics")
        assert hasattr(mock_transport, "fetch_dynamic_rules")
        assert hasattr(mock_transport, "send_status")

        # Verify methods can be called and return expected defaults
        await mock_transport.initialize()
        await mock_transport.close()

        events_result = await mock_transport.send_events([])
        assert events_result is True

        metrics_result = await mock_transport.send_metrics([])
        assert metrics_result is True

        rules_result = await mock_transport.fetch_dynamic_rules()
        assert rules_result is None

        status_result = await mock_transport.send_status(None)
        assert status_result is True

        # Verify methods were called
        mock_transport.initialize.assert_called_once()
        mock_transport.close.assert_called_once()
        mock_transport.send_events.assert_called_once()
        mock_transport.send_metrics.assert_called_once()
        mock_transport.fetch_dynamic_rules.assert_called_once()
        mock_transport.send_status.assert_called_once()
