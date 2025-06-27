import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
from pytest import LogCaptureFixture

from guard_agent.buffer import EventBuffer
from guard_agent.models import AgentConfig, SecurityEvent, SecurityMetric


# Test basic functionality
class TestBufferBasic:
    """Tests for EventBuffer basic functionality."""

    @pytest.mark.asyncio
    async def test_add_event(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        await buffer.add_event(security_event)
        assert len(buffer.event_buffer) == 1
        assert buffer.events_buffered == 1
        assert await buffer.get_buffer_size() == 1

    @pytest.mark.asyncio
    async def test_add_metric(
        self, buffer: EventBuffer, security_metric: SecurityMetric
    ) -> None:
        await buffer.add_metric(security_metric)
        assert len(buffer.metric_buffer) == 1
        assert buffer.metrics_buffered == 1
        assert await buffer.get_buffer_size() == 1

    @pytest.mark.asyncio
    async def test_flush_events(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        await buffer.add_event(security_event)
        flushed_events = await buffer.flush_events()
        assert len(flushed_events) == 1
        assert flushed_events[0] == security_event
        assert len(buffer.event_buffer) == 0
        assert buffer.events_flushed == 1
        assert buffer.last_flush_time is not None

    @pytest.mark.asyncio
    async def test_flush_metrics(
        self, buffer: EventBuffer, security_metric: SecurityMetric
    ) -> None:
        await buffer.add_metric(security_metric)
        flushed_metrics = await buffer.flush_metrics()
        assert len(flushed_metrics) == 1
        assert flushed_metrics[0] == security_metric
        assert len(buffer.metric_buffer) == 0
        assert buffer.metrics_flushed == 1
        assert buffer.last_flush_time is not None

    @pytest.mark.asyncio
    async def test_clear_buffer(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        security_metric: SecurityMetric,
    ) -> None:
        await buffer.add_event(security_event)
        await buffer.add_metric(security_metric)
        assert await buffer.get_buffer_size() == 2
        await buffer.clear_buffer()
        assert await buffer.get_buffer_size() == 0
        assert len(buffer.event_buffer) == 0
        assert len(buffer.metric_buffer) == 0


# Test Redis integration
class TestBufferRedisIntegration:
    """Tests for EventBuffer Redis integration."""

    @pytest.mark.asyncio
    async def test_initialize_redis(
        self, buffer: EventBuffer, mock_redis_handler: AsyncMock
    ) -> None:
        with patch.object(
            buffer, "_load_from_redis", new_callable=AsyncMock
        ) as mock_load:
            await buffer.initialize_redis(mock_redis_handler)
            assert buffer.redis_handler is mock_redis_handler
            mock_load.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_event_with_redis(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        with patch.object(
            buffer, "_persist_event_to_redis", new_callable=AsyncMock
        ) as mock_persist:
            await buffer.add_event(security_event)
            mock_persist.assert_awaited_once_with(security_event)

    @pytest.mark.asyncio
    async def test_add_metric_with_redis(
        self,
        buffer: EventBuffer,
        security_metric: SecurityMetric,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        with patch.object(
            buffer, "_persist_metric_to_redis", new_callable=AsyncMock
        ) as mock_persist:
            await buffer.add_metric(security_metric)
            mock_persist.assert_awaited_once_with(security_metric)

    @pytest.mark.asyncio
    async def test_flush_events_with_redis(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.add_event(security_event)
        with patch.object(
            buffer, "_clear_events_from_redis", new_callable=AsyncMock
        ) as mock_clear:
            await buffer.flush_events()
            mock_clear.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_flush_metrics_with_redis(
        self,
        buffer: EventBuffer,
        security_metric: SecurityMetric,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.add_metric(security_metric)
        with patch.object(
            buffer, "_clear_metrics_from_redis", new_callable=AsyncMock
        ) as mock_clear:
            await buffer.flush_metrics()
            mock_clear.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_clear_buffer_with_redis(
        self, buffer: EventBuffer, mock_redis_handler: AsyncMock
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        with patch.object(
            buffer, "_clear_redis_buffers", new_callable=AsyncMock
        ) as mock_clear:
            await buffer.clear_buffer()
            mock_clear.assert_awaited_once()


# Test auto-flush
class TestBufferAutoFlush:
    """Tests for EventBuffer auto-flush functionality."""

    @pytest.mark.asyncio
    async def test_start_stop_auto_flush(self, buffer: EventBuffer) -> None:
        await buffer.start_auto_flush()
        assert buffer._running
        assert buffer._flush_task is not None
        assert not buffer._flush_task.done()

        # Calling start again should do nothing
        task = buffer._flush_task
        await buffer.start_auto_flush()
        assert buffer._flush_task is task

        await buffer.stop_auto_flush()
        assert not buffer._running
        assert buffer._flush_task.cancelled()

    @pytest.mark.asyncio
    async def test_auto_flush_loop(
        self, buffer: EventBuffer, agent_config: AgentConfig
    ) -> None:
        agent_config.flush_interval = 0.1
        buffer = EventBuffer(agent_config)
        with patch.object(
            buffer, "_flush_if_needed", new_callable=AsyncMock
        ) as mock_flush:
            await buffer.start_auto_flush()
            await asyncio.sleep(0.15)
            await buffer.stop_auto_flush()
            mock_flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_auto_flush_loop_cancel(self, buffer: EventBuffer) -> None:
        await buffer.start_auto_flush()
        await buffer.stop_auto_flush()
        assert buffer._flush_task.cancelled()

    @pytest.mark.asyncio
    async def test_auto_flush_loop_exception(
        self, buffer: EventBuffer, caplog: LogCaptureFixture
    ) -> None:
        buffer.config.flush_interval = 0.1
        with patch.object(
            buffer, "_flush_if_needed", side_effect=Exception("Test Error")
        ):
            await buffer.start_auto_flush()
            await asyncio.sleep(0.15)
            await buffer.stop_auto_flush()
            assert "Error in auto flush loop: Test Error" in caplog.text


# Test _flush_if_needed
class TestBufferFlushIfNeeded:
    """Tests for EventBuffer _flush_if_needed method."""

    @pytest.mark.asyncio
    async def test_flush_if_needed_by_size(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        buffer.config.buffer_size = 10
        for _ in range(8):
            await buffer.add_event(security_event)

        with patch.object(buffer.logger, "debug") as mock_debug:
            await buffer._flush_if_needed()
            mock_debug.assert_called_with("Triggering buffer flush - size: 8")

    @pytest.mark.asyncio
    async def test_flush_if_needed_by_time(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        buffer.config.flush_interval = 1
        buffer.last_flush_time = time.time() - 2
        await buffer.add_event(security_event)

        with patch.object(buffer.logger, "debug") as mock_debug:
            await buffer._flush_if_needed()
            mock_debug.assert_called_with("Triggering buffer flush - size: 1")

    @pytest.mark.asyncio
    async def test_flush_if_needed_not_needed(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        buffer.config.flush_interval = 10
        buffer.last_flush_time = time.time()
        await buffer.add_event(security_event)

        with patch.object(buffer.logger, "debug") as mock_debug:
            await buffer._flush_if_needed()
            mock_debug.assert_not_called()


# Test Redis persistence methods
class TestBufferRedisPersistence:
    """Tests for EventBuffer Redis persistence methods."""

    @pytest.mark.asyncio
    async def test_persist_event_to_redis(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._persist_event_to_redis(security_event)
        mock_redis_handler.set_key.assert_awaited_once()
        args, kwargs = mock_redis_handler.set_key.call_args
        assert args[0] == "agent_events"
        assert args[1].startswith("event_")
        assert "ip_banned" in args[2]

    @pytest.mark.asyncio
    async def test_persist_metric_to_redis(
        self,
        buffer: EventBuffer,
        security_metric: SecurityMetric,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._persist_metric_to_redis(security_metric)
        mock_redis_handler.set_key.assert_awaited_once()
        args, kwargs = mock_redis_handler.set_key.call_args
        assert args[0] == "agent_metrics"
        assert args[1].startswith("metric_")
        assert "request_count" in args[2]

    @pytest.mark.asyncio
    async def test_persist_to_redis_no_handler(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        security_metric: SecurityMetric,
    ) -> None:
        # No redis handler, should not raise error
        await buffer._persist_event_to_redis(security_event)
        await buffer._persist_metric_to_redis(security_metric)

    @pytest.mark.asyncio
    async def test_persist_event_to_redis_exception(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.set_key.side_effect = Exception("Redis Error")
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._persist_event_to_redis(security_event)
        assert "Failed to persist event to Redis: Redis Error" in caplog.text

    @pytest.mark.asyncio
    async def test_persist_metric_to_redis_exception(
        self,
        buffer: EventBuffer,
        security_metric: SecurityMetric,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.set_key.side_effect = Exception("Redis Error")
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._persist_metric_to_redis(security_metric)
        assert "Failed to persist metric to Redis: Redis Error" in caplog.text


# Test loading from Redis
class TestBufferLoadFromRedis:
    """Tests for EventBuffer loading from Redis."""

    @pytest.mark.asyncio
    async def test_load_from_redis(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        security_event: SecurityEvent,
        security_metric: SecurityMetric,
        caplog: LogCaptureFixture,
    ) -> None:
        event_key = "event_123"
        metric_key = "metric_456"
        unknown_key = "unknown_key"
        mock_redis_handler.keys.side_effect = [
            [f"agent_events:{event_key}", f"agent_events:{unknown_key}"],
            [f"agent_metrics:{metric_key}"],
        ]

        from guard_agent.utils import safe_json_serialize

        event_data = await safe_json_serialize(security_event.model_dump())
        metric_data = await safe_json_serialize(security_metric.model_dump())

        async def get_key_side_effect(namespace: str, key: str) -> str | None:
            if namespace == "agent_events" and key == event_key:
                return event_data
            if namespace == "agent_metrics" and key == metric_key:
                return metric_data
            return None

        mock_redis_handler.get_key.side_effect = get_key_side_effect

        await buffer.initialize_redis(mock_redis_handler)  # this calls _load_from_redis

        assert len(buffer.event_buffer) == 1
        assert len(buffer.metric_buffer) == 1
        assert buffer.events_buffered == 1
        assert buffer.metrics_buffered == 1
        assert buffer.event_buffer[0].event_type == "ip_banned"
        assert buffer.metric_buffer[0].metric_type == "request_count"

        message = "Failed to load event from Redis key"
        details = "No data found for key"
        assert f"{message} agent_events:{unknown_key}: {details}" in caplog.text

    @pytest.mark.asyncio
    async def test_load_from_redis_no_handler(self, buffer: EventBuffer) -> None:
        await buffer._load_from_redis()  # should do nothing and not fail

    @pytest.mark.asyncio
    async def test_load_from_redis_exception(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.keys.side_effect = Exception("Redis Error")
        await buffer.initialize_redis(mock_redis_handler)
        assert "Failed to load from Redis: Redis Error" in caplog.text

    @pytest.mark.asyncio
    async def test_load_from_redis_item_exception(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.keys.return_value = ["agent_events:event_123"]
        mock_redis_handler.get_key.side_effect = Exception("Get Key Error")
        await buffer.initialize_redis(mock_redis_handler)
        assert (
            "Failed to load event from Redis key agent_events:event_123: Get Key Error"
            in caplog.text
        )

    @pytest.mark.asyncio
    async def test_load_from_redis_deserialize_fail(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.keys.return_value = ["agent_events:event_123"]
        mock_redis_handler.get_key.return_value = "invalid json"
        await buffer.initialize_redis(mock_redis_handler)
        assert len(buffer.event_buffer) == 0
        assert "Failed to deserialize JSON" in caplog.text

    @pytest.mark.asyncio
    async def test_load_from_redis_model_validation_fail(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.keys.return_value = ["agent_events:event_123"]
        mock_redis_handler.get_key.return_value = """{"invalid": "data"}"""
        await buffer.initialize_redis(mock_redis_handler)
        assert len(buffer.event_buffer) == 0
        assert "Failed to load event from Redis key" in caplog.text

    @pytest.mark.asyncio
    async def test_load_from_redis_unknown_key(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.keys.return_value = ["agent_events:unknown_key"]
        mock_redis_handler.get_key.return_value = (
            None  # Simulate get_key returning None for an unknown key
        )

        await buffer.initialize_redis(mock_redis_handler)

        assert len(buffer.event_buffer) == 0
        assert len(buffer.metric_buffer) == 0

        message = "Failed to load event from Redis key"
        details = "No data found for key"
        assert f"{message} agent_events:unknown_key: {details}" in caplog.text


# Test clearing from Redis
class TestBufferClearFromRedis:
    """Tests for EventBuffer clearing from Redis."""

    @pytest.mark.parametrize(
        "event_keys,clear_count,expected_deletes",
        [
            (
                ["agent_events:event_1", "agent_events:event_2"],
                2,
                ["event_1", "event_2"],
            ),  # Clear all
            (
                [
                    "agent_events:event_1",
                    "agent_events:event_2",
                    "agent_events:event_3",
                ],
                2,
                ["event_1", "event_2"],
            ),  # Partial clear (covers break condition)
        ],
    )
    @pytest.mark.asyncio
    async def test_clear_events_from_redis(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        event_keys: list[str],
        clear_count: int,
        expected_deletes: list[str],
    ) -> None:
        mock_redis_handler.keys.return_value = event_keys
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._clear_events_from_redis(clear_count)
        assert mock_redis_handler.delete_key.call_count == len(expected_deletes)
        for event_id in expected_deletes:
            mock_redis_handler.delete_key.assert_any_await("agent_events", event_id)

    @pytest.mark.asyncio
    async def test_clear_metrics_from_redis(
        self, buffer: EventBuffer, mock_redis_handler: AsyncMock
    ) -> None:
        mock_redis_handler.keys.return_value = [
            "agent_metrics:metric_1",
            "agent_metrics:metric_2",
        ]
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._clear_metrics_from_redis(1)
        assert mock_redis_handler.delete_key.call_count == 1
        mock_redis_handler.delete_key.assert_awaited_once_with(
            "agent_metrics", "metric_1"
        )

    @pytest.mark.asyncio
    async def test_clear_from_redis_no_handler(self, buffer: EventBuffer) -> None:
        await buffer._clear_events_from_redis(1)
        await buffer._clear_metrics_from_redis(1)
        await buffer._clear_redis_buffers()

    @pytest.mark.asyncio
    async def test_clear_events_from_redis_exception(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.keys.side_effect = Exception("Redis Error")
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._clear_events_from_redis(1)
        assert "Failed to clear events from Redis: Redis Error" in caplog.text

    @pytest.mark.asyncio
    async def test_clear_metrics_from_redis_exception(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.keys.side_effect = Exception("Redis Error")
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._clear_metrics_from_redis(1)
        assert "Failed to clear metrics from Redis: Redis Error" in caplog.text

    @pytest.mark.asyncio
    async def test_clear_redis_buffers(
        self, buffer: EventBuffer, mock_redis_handler: AsyncMock
    ) -> None:
        mock_redis_handler.keys.side_effect = [
            [],  # For _load_from_redis events
            [],  # For _load_from_redis metrics
            ["agent_events:event_1"],  # For _clear_redis_buffers events
            ["agent_metrics:metric_1"],  # For _clear_redis_buffers metrics
        ]
        mock_redis_handler.delete_key.return_value = None
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._clear_redis_buffers()
        mock_redis_handler.delete_key.assert_any_await("agent_events", "event_1")
        mock_redis_handler.delete_key.assert_any_await("agent_metrics", "metric_1")

    @pytest.mark.asyncio
    async def test_clear_redis_buffers_exception(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        mock_redis_handler.keys.side_effect = Exception("Redis Error")
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._clear_redis_buffers()
        assert "Failed to clear Redis buffers: Redis Error" in caplog.text


# Test error handling in add_event/add_metric
class TestBufferErrorHandling:
    """Tests for EventBuffer error handling."""

    @pytest.mark.asyncio
    async def test_add_event_exception(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        with patch.object(
            buffer,
            "_persist_event_to_redis",
            side_effect=Exception("Redis Persist Error"),
        ):
            await buffer.add_event(security_event)
            assert "Failed to buffer event: Redis Persist Error" in caplog.text

    @pytest.mark.asyncio
    async def test_add_metric_exception(
        self,
        buffer: EventBuffer,
        security_metric: SecurityMetric,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        with patch.object(
            buffer,
            "_persist_metric_to_redis",
            side_effect=Exception("Redis Persist Error"),
        ):
            await buffer.add_metric(security_metric)
            assert "Failed to buffer metric: Redis Persist Error" in caplog.text


# Test buffer full immediate flush
class TestBufferFullImmediateFlush:
    """Tests for EventBuffer full buffer immediate flush."""

    @pytest.mark.asyncio
    async def test_add_event_full_buffer_flush(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        buffer.config.buffer_size = 1
        with patch.object(
            buffer, "_flush_if_needed", new_callable=AsyncMock
        ) as mock_flush:
            await buffer.add_event(security_event)
            mock_flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_metric_full_buffer_flush(
        self, buffer: EventBuffer, security_metric: SecurityMetric
    ) -> None:
        buffer.config.buffer_size = 1
        with patch.object(
            buffer, "_flush_if_needed", new_callable=AsyncMock
        ) as mock_flush:
            await buffer.add_metric(security_metric)
            mock_flush.assert_called_once()


# Test get_stats
class TestGetStats:
    """Tests for EventBuffer get_stats method."""

    def test_get_stats(self, buffer: EventBuffer) -> None:
        stats = buffer.get_stats()
        assert "events_buffered" in stats
        assert "metrics_buffered" in stats
        assert "events_flushed" in stats
        assert "metrics_flushed" in stats
        assert "current_event_buffer_size" in stats
        assert "current_metric_buffer_size" in stats
        assert "last_flush_time" in stats
        assert "auto_flush_running" in stats
