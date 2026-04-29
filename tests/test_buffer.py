import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from pytest import LogCaptureFixture

from guard_agent.buffer import EventBuffer
from guard_agent.exceptions import BufferFullError, GuardAgentError
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

        await buffer.flush_events()

        assert mock_redis_handler.delete.call_count == 1
        args = mock_redis_handler.delete.call_args.args
        assert args[0] == "agent_events"
        assert args[1].startswith("event_")

    @pytest.mark.asyncio
    async def test_flush_metrics_with_redis(
        self,
        buffer: EventBuffer,
        security_metric: SecurityMetric,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.add_metric(security_metric)

        await buffer.flush_metrics()

        assert mock_redis_handler.delete.call_count == 1
        args = mock_redis_handler.delete.call_args.args
        assert args[0] == "agent_metrics"
        assert args[1].startswith("metric_")

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

    @pytest.mark.asyncio
    async def test_auto_flush_loop(
        self, buffer: EventBuffer, agent_config: AgentConfig
    ) -> None:
        agent_config.flush_interval = 1
        buffer = EventBuffer(agent_config)
        with patch.object(
            buffer, "_flush_if_needed", new_callable=AsyncMock
        ) as mock_flush:
            await buffer.start_auto_flush()
            await asyncio.sleep(1.5)
            await buffer.stop_auto_flush()
            mock_flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_auto_flush_loop_cancel(self, buffer: EventBuffer) -> None:
        await buffer.start_auto_flush()
        await buffer.stop_auto_flush()
        assert buffer._flush_task and buffer._flush_task.cancelled()

    @pytest.mark.asyncio
    async def test_auto_flush_loop_exception(
        self, buffer: EventBuffer, caplog: LogCaptureFixture
    ) -> None:
        buffer.config.flush_interval = 1
        with patch.object(
            buffer, "_flush_if_needed", side_effect=Exception("Test Error")
        ):
            await buffer.start_auto_flush()
            await asyncio.sleep(1.5)
            await buffer.stop_auto_flush()
            assert "Error in auto flush loop: Test Error" in caplog.text


# Test _flush_if_needed
class TestBufferFlushIfNeeded:
    """Tests for EventBuffer _flush_if_needed method."""

    @pytest.mark.asyncio
    async def test_flush_if_needed_by_size(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        called: list[int] = []

        async def cb() -> None:
            called.append(1)

        buffer._flush_callback = cb
        buffer._flush_semaphore = asyncio.Semaphore(1)
        buffer.config.buffer_size = 10
        for _ in range(8):
            await buffer.add_event(security_event)

        with patch.object(buffer.logger, "debug") as mock_debug:
            await buffer._flush_if_needed()
            mock_debug.assert_called_with("Triggering buffer flush - size: 8")

        assert called, "callback must be invoked when watermark is reached"

    @pytest.mark.asyncio
    async def test_flush_if_needed_by_time(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        called: list[int] = []

        async def cb() -> None:
            called.append(1)

        buffer._flush_callback = cb
        buffer._flush_semaphore = asyncio.Semaphore(1)
        buffer.config.flush_interval = 1
        buffer.last_flush_time = time.time() - 2
        await buffer.add_event(security_event)

        with patch.object(buffer.logger, "debug") as mock_debug:
            await buffer._flush_if_needed()
            mock_debug.assert_called_with("Triggering buffer flush - size: 1")

        assert called, "callback must be invoked when flush interval elapsed"

    @pytest.mark.asyncio
    async def test_flush_if_needed_not_needed(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        called: list[int] = []

        async def cb() -> None:
            called.append(1)

        buffer._flush_callback = cb
        buffer._flush_semaphore = asyncio.Semaphore(1)
        buffer.config.flush_interval = 10
        buffer.last_flush_time = time.time()
        await buffer.add_event(security_event)

        with patch.object(buffer.logger, "debug") as mock_debug:
            await buffer._flush_if_needed()
            mock_debug.assert_not_called()

        assert not called, (
            "callback must not fire when below watermark and time not elapsed"
        )


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
    async def test_persist_duck_typed_metric_to_redis(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
    ) -> None:
        """Test Redis persistence for duck-typed metric without model_dump."""
        await buffer.initialize_redis(mock_redis_handler)
        duck_metric = type(
            "Metric", (), {"metric_type": "request_count", "value": 1.0}
        )()
        await buffer._persist_metric_to_redis(duck_metric)
        mock_redis_handler.set_key.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persist_duck_typed_event_to_redis(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
    ) -> None:
        """Test Redis persistence for duck-typed event without model_dump."""
        await buffer.initialize_redis(mock_redis_handler)
        duck_event = type(
            "Event", (), {"event_type": "ip_banned", "ip_address": "1.1.1.1"}
        )()
        await buffer._persist_event_to_redis(duck_event)
        mock_redis_handler.set_key.assert_awaited_once()

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
        assert mock_redis_handler.delete.call_count == len(expected_deletes)
        for event_id in expected_deletes:
            mock_redis_handler.delete.assert_any_await("agent_events", event_id)

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
        assert mock_redis_handler.delete.call_count == 1
        mock_redis_handler.delete.assert_awaited_once_with("agent_metrics", "metric_1")

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
        mock_redis_handler.delete.return_value = None
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._clear_redis_buffers()
        mock_redis_handler.delete.assert_any_await("agent_events", "event_1")
        mock_redis_handler.delete.assert_any_await("agent_metrics", "metric_1")

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
        assert "events_dropped" in stats
        assert "metrics_dropped" in stats
        assert "current_event_buffer_size" in stats
        assert "current_metric_buffer_size" in stats
        assert "last_flush_time" in stats
        assert "auto_flush_running" in stats


class TestBufferOverflowDropTracking:
    """Tests for buffer overflow drop accounting."""

    @pytest.mark.asyncio
    async def test_event_overflow_increments_drop_counter(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        buffer.config.buffer_size = 3
        buffer.event_buffer = type(buffer.event_buffer)(maxlen=3)

        for _ in range(5):
            await buffer.add_event(security_event)

        assert len(buffer.event_buffer) == 3
        assert buffer.events_dropped == 2
        assert buffer.events_buffered == 5
        assert buffer.get_stats()["events_dropped"] == 2

    @pytest.mark.asyncio
    async def test_metric_overflow_increments_drop_counter(
        self, buffer: EventBuffer, security_metric: SecurityMetric
    ) -> None:
        buffer.config.buffer_size = 2
        buffer.metric_buffer = type(buffer.metric_buffer)(maxlen=2)

        for _ in range(5):
            await buffer.add_metric(security_metric)

        assert len(buffer.metric_buffer) == 2
        assert buffer.metrics_dropped == 3
        assert buffer.get_stats()["metrics_dropped"] == 3

    @pytest.mark.asyncio
    async def test_no_drops_when_buffer_has_capacity(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        for _ in range(buffer.config.buffer_size - 1):
            await buffer.add_event(security_event)

        assert buffer.events_dropped == 0

    @pytest.mark.asyncio
    async def test_overflow_logs_warning_at_first_drop(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        caplog: LogCaptureFixture,
    ) -> None:
        buffer.config.buffer_size = 1
        buffer.event_buffer = type(buffer.event_buffer)(maxlen=1)
        await buffer.add_event(security_event)

        with caplog.at_level("WARNING", logger="guard_agent.buffer"):
            await buffer.add_event(security_event)

        assert any("buffer full" in r.message.lower() for r in caplog.records)


class TestBufferConfirmAndRequeue:
    """Tests for transport-acked Redis confirmation and requeue on failure."""

    @pytest.mark.asyncio
    async def test_persisted_event_keys_are_unique_per_event(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.add_event(security_event)
        await buffer.add_event(security_event)

        keys = [c.args[1] for c in mock_redis_handler.set_key.call_args_list]
        assert len(keys) == 2
        assert len(set(keys)) == 2
        assert all(k.startswith("event_") for k in keys)

    @pytest.mark.asyncio
    async def test_flush_with_keys_does_not_delete_redis_until_confirmed(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.add_event(security_event)

        events, keys = await buffer.flush_events_with_keys()

        assert len(events) == 1
        assert len(keys) == 1
        assert mock_redis_handler.delete.call_count == 0

        await buffer.confirm_event_redis_keys(keys)
        assert mock_redis_handler.delete.call_count == 1
        assert mock_redis_handler.delete.call_args.args == ("agent_events", keys[0])

    @pytest.mark.asyncio
    async def test_requeue_restores_events_for_retry(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.add_event(security_event)

        events, keys = await buffer.flush_events_with_keys()
        assert len(buffer.event_buffer) == 0

        buffer.requeue_events_in_memory(events, keys)
        assert len(buffer.event_buffer) == 1
        assert id(buffer.event_buffer[0]) in buffer._event_redis_keys

    @pytest.mark.asyncio
    async def test_legacy_flush_events_still_deletes_redis(
        self,
        buffer: EventBuffer,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.add_event(security_event)

        events = await buffer.flush_events()

        assert len(events) == 1
        assert mock_redis_handler.delete.call_count == 1

    def test_forget_oldest_event_key_no_op_when_buffer_empty(
        self, buffer: EventBuffer
    ) -> None:
        buffer._forget_oldest_event_key()

    def test_forget_oldest_metric_key_no_op_when_buffer_empty(
        self, buffer: EventBuffer
    ) -> None:
        buffer._forget_oldest_metric_key()

    @pytest.mark.asyncio
    async def test_confirm_event_redis_keys_no_op_when_redis_missing(
        self, buffer: EventBuffer
    ) -> None:
        await buffer.confirm_event_redis_keys(["evt_1"])

    @pytest.mark.asyncio
    async def test_confirm_event_redis_keys_no_op_on_empty_list(
        self, buffer: EventBuffer, mock_redis_handler: AsyncMock
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.confirm_event_redis_keys([])
        assert mock_redis_handler.delete.call_count == 0

    @pytest.mark.asyncio
    async def test_confirm_event_redis_keys_swallows_redis_failure(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        mock_redis_handler.delete.side_effect = RuntimeError("redis down")

        with caplog.at_level("WARNING", logger="guard_agent.buffer"):
            await buffer.confirm_event_redis_keys(["evt_1"])

        assert any(
            "Failed to delete confirmed event key" in r.message for r in caplog.records
        )

    @pytest.mark.asyncio
    async def test_confirm_metric_redis_keys_no_op_when_redis_missing(
        self, buffer: EventBuffer
    ) -> None:
        await buffer.confirm_metric_redis_keys(["m_1"])

    @pytest.mark.asyncio
    async def test_confirm_metric_redis_keys_no_op_on_empty_list(
        self, buffer: EventBuffer, mock_redis_handler: AsyncMock
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.confirm_metric_redis_keys([])
        assert mock_redis_handler.delete.call_count == 0

    @pytest.mark.asyncio
    async def test_confirm_metric_redis_keys_swallows_redis_failure(
        self,
        buffer: EventBuffer,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        mock_redis_handler.delete.side_effect = RuntimeError("redis down")

        with caplog.at_level("WARNING", logger="guard_agent.buffer"):
            await buffer.confirm_metric_redis_keys(["m_1"])

        assert any(
            "Failed to delete confirmed metric key" in r.message for r in caplog.records
        )

    @pytest.mark.asyncio
    async def test_requeue_events_drops_when_buffer_already_full(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        buffer.config.buffer_size = 1
        buffer.event_buffer = type(buffer.event_buffer)(maxlen=1)
        await buffer.add_event(security_event)

        before_dropped = buffer.events_dropped
        buffer.requeue_events_in_memory([security_event], ["evt_x"])

        assert buffer.events_dropped == before_dropped + 1
        assert len(buffer.event_buffer) == 1

    @pytest.mark.asyncio
    async def test_requeue_metrics_restores_for_retry_and_drops_overflow(
        self,
        buffer: EventBuffer,
        security_metric: SecurityMetric,
        mock_redis_handler: AsyncMock,
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.add_metric(security_metric)
        metrics, keys = await buffer.flush_metrics_with_keys()
        assert len(buffer.metric_buffer) == 0

        buffer.requeue_metrics_in_memory(metrics, keys)
        assert len(buffer.metric_buffer) == 1
        assert id(buffer.metric_buffer[0]) in buffer._metric_redis_keys

        buffer.config.buffer_size = 1
        buffer.metric_buffer = type(buffer.metric_buffer)(maxlen=1)
        await buffer.add_metric(security_metric)

        before_dropped = buffer.metrics_dropped
        buffer.requeue_metrics_in_memory([security_metric], ["m_x"])
        assert buffer.metrics_dropped == before_dropped + 1
        assert len(buffer.metric_buffer) == 1


class TestBufferMissingBranches:
    @pytest.mark.asyncio
    async def test_stop_auto_flush_when_task_already_done(
        self, buffer: EventBuffer
    ) -> None:
        await buffer.start_auto_flush()
        await buffer.stop_auto_flush()
        await buffer.stop_auto_flush()
        assert not buffer._running
        assert buffer._flush_semaphore is None

    @pytest.mark.asyncio
    async def test_stop_auto_flush_awaits_inflight_tasks(
        self, buffer: EventBuffer
    ) -> None:
        completed: list[int] = []

        async def slow_flush() -> None:
            await asyncio.sleep(0.05)
            completed.append(1)

        buffer._flush_semaphore = asyncio.Semaphore(1)
        buffer._flush_callback = slow_flush
        buffer._running = True
        task: asyncio.Task[None] = asyncio.create_task(buffer._flush_if_needed())
        buffer._inflight_flush_tasks.add(task)
        task.add_done_callback(buffer._inflight_flush_tasks.discard)
        buffer.last_flush_time = None
        await buffer.add_event(
            SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="ip_blocked",
                ip_address="1.2.3.4",
            )
        )
        await buffer.stop_auto_flush()
        assert not buffer._inflight_flush_tasks
        assert buffer._flush_semaphore is None

    @pytest.mark.asyncio
    async def test_add_event_redis_persist_returns_none_skips_key_store(
        self, buffer: EventBuffer, mock_redis_handler: AsyncMock
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        with patch.object(
            buffer, "_persist_event_to_redis", new_callable=AsyncMock, return_value=None
        ):
            event = SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="ip_blocked",
                ip_address="1.2.3.4",
            )
            await buffer.add_event(event)
        assert id(event) not in buffer._event_redis_keys

    @pytest.mark.asyncio
    async def test_add_metric_redis_persist_returns_none_skips_key_store(
        self, buffer: EventBuffer, mock_redis_handler: AsyncMock
    ) -> None:
        await buffer.initialize_redis(mock_redis_handler)
        with patch.object(
            buffer,
            "_persist_metric_to_redis",
            new_callable=AsyncMock,
            return_value=None,
        ):
            metric = SecurityMetric(
                timestamp=datetime.now(timezone.utc),
                metric_type="request_count",
                value=1.0,
            )
            await buffer.add_metric(metric)
        assert id(metric) not in buffer._metric_redis_keys

    @pytest.mark.asyncio
    async def test_requeue_events_with_empty_key_skips_redis_tracking(
        self, buffer: EventBuffer, security_event: SecurityEvent
    ) -> None:
        buffer.requeue_events_in_memory([security_event], [""])
        assert id(security_event) not in buffer._event_redis_keys

    @pytest.mark.asyncio
    async def test_requeue_metrics_with_empty_key_skips_redis_tracking(
        self, buffer: EventBuffer, security_metric: SecurityMetric
    ) -> None:
        buffer.requeue_metrics_in_memory([security_metric], [""])
        assert id(security_metric) not in buffer._metric_redis_keys

    @pytest.mark.asyncio
    async def test_auto_flush_loop_exits_normally_when_running_set_false(
        self, buffer: EventBuffer
    ) -> None:
        buffer.config.flush_interval = 1
        buffer._running = True
        buffer._flush_semaphore = asyncio.Semaphore(1)

        loop_task: asyncio.Task[None] = asyncio.create_task(buffer._auto_flush_loop())
        await asyncio.sleep(0)
        buffer._running = False
        await asyncio.sleep(1.1)
        assert loop_task.done()
        assert not loop_task.cancelled()

    @pytest.mark.asyncio
    async def test_auto_flush_loop_skips_flush_when_running_false_after_sleep(
        self, buffer: EventBuffer
    ) -> None:
        flushed: list[int] = []

        async def fake_flush() -> None:
            flushed.append(1)

        buffer.config.flush_interval = 1
        buffer._flush_callback = fake_flush
        buffer._flush_semaphore = asyncio.Semaphore(1)
        buffer._running = True

        loop_task = asyncio.create_task(buffer._auto_flush_loop())
        await asyncio.sleep(0.5)
        buffer._running = False
        await asyncio.sleep(0.7)
        loop_task.cancel()
        try:
            await loop_task
        except asyncio.CancelledError:
            pass
        assert not flushed

    @pytest.mark.asyncio
    async def test_clear_metrics_from_redis_all_keys_cleared_without_break(
        self, buffer: EventBuffer, mock_redis_handler: AsyncMock
    ) -> None:
        mock_redis_handler.keys.side_effect = [
            [],
            [],
            ["agent_metrics:metric_1", "agent_metrics:metric_2"],
        ]
        await buffer.initialize_redis(mock_redis_handler)
        await buffer._clear_metrics_from_redis(10)
        assert mock_redis_handler.delete.call_count == 2


class TestBufferOverflowPolicy:
    """Tests for the configurable buffer_overflow_policy."""

    def test_overflow_policy_default_is_drop(self) -> None:
        config = AgentConfig(api_key="k")
        assert config.buffer_overflow_policy == "drop"

    def test_buffer_full_error_is_guard_agent_error(self) -> None:
        assert issubclass(BufferFullError, GuardAgentError)
        assert issubclass(GuardAgentError, Exception)

    @pytest.mark.asyncio
    async def test_overflow_policy_drop_evicts_oldest_and_increments_counter(
        self, security_event: SecurityEvent
    ) -> None:
        config = AgentConfig(api_key="k", buffer_size=2, buffer_overflow_policy="drop")
        buffer = EventBuffer(config)

        first = SecurityEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="ip_banned",
            ip_address="1.1.1.1",
        )
        second = SecurityEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="ip_banned",
            ip_address="2.2.2.2",
        )
        third = SecurityEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="ip_banned",
            ip_address="3.3.3.3",
        )

        await buffer.add_event(first)
        await buffer.add_event(second)
        await buffer.add_event(third)

        assert buffer.events_dropped == 1
        assert len(buffer.event_buffer) == 2
        assert first not in list(buffer.event_buffer)
        assert third in list(buffer.event_buffer)

    @pytest.mark.asyncio
    async def test_metric_overflow_policy_drop_evicts_oldest(self) -> None:
        config = AgentConfig(api_key="k", buffer_size=2, buffer_overflow_policy="drop")
        buffer = EventBuffer(config)

        first = SecurityMetric(
            timestamp=datetime.now(timezone.utc),
            metric_type="request_count",
            value=1.0,
        )
        second = SecurityMetric(
            timestamp=datetime.now(timezone.utc),
            metric_type="request_count",
            value=2.0,
        )
        third = SecurityMetric(
            timestamp=datetime.now(timezone.utc),
            metric_type="request_count",
            value=3.0,
        )

        await buffer.add_metric(first)
        await buffer.add_metric(second)
        await buffer.add_metric(third)

        assert buffer.metrics_dropped == 1
        assert len(buffer.metric_buffer) == 2
        assert first not in list(buffer.metric_buffer)
        assert third in list(buffer.metric_buffer)

    @pytest.mark.asyncio
    async def test_overflow_policy_raise_throws_buffer_full_error_for_events(
        self, security_event: SecurityEvent
    ) -> None:
        config = AgentConfig(api_key="k", buffer_size=2, buffer_overflow_policy="raise")
        buffer = EventBuffer(config)

        await buffer.add_event(security_event)
        await buffer.add_event(security_event)

        with pytest.raises(BufferFullError):
            await buffer.add_event(security_event)

        assert len(buffer.event_buffer) == 2
        assert buffer.events_dropped == 0

    @pytest.mark.asyncio
    async def test_overflow_policy_raise_throws_buffer_full_error_for_metrics(
        self, security_metric: SecurityMetric
    ) -> None:
        config = AgentConfig(api_key="k", buffer_size=2, buffer_overflow_policy="raise")
        buffer = EventBuffer(config)

        await buffer.add_metric(security_metric)
        await buffer.add_metric(security_metric)

        with pytest.raises(BufferFullError):
            await buffer.add_metric(security_metric)

        assert len(buffer.metric_buffer) == 2
        assert buffer.metrics_dropped == 0

    @pytest.mark.asyncio
    async def test_overflow_policy_raise_is_not_swallowed_by_redis_try_block(
        self,
        security_event: SecurityEvent,
        mock_redis_handler: AsyncMock,
        caplog: LogCaptureFixture,
    ) -> None:
        config = AgentConfig(api_key="k", buffer_size=1, buffer_overflow_policy="raise")
        buffer = EventBuffer(config)
        await buffer.initialize_redis(mock_redis_handler)
        await buffer.add_event(security_event)

        with caplog.at_level("ERROR", logger="guard_agent.buffer"):
            with pytest.raises(BufferFullError):
                await buffer.add_event(security_event)

        assert not any("Failed to buffer event" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_overflow_policy_block_awaits_until_space_frees_for_events(
        self, security_event: SecurityEvent
    ) -> None:
        config = AgentConfig(api_key="k", buffer_size=2, buffer_overflow_policy="block")
        buffer = EventBuffer(config)

        await buffer.add_event(security_event)
        await buffer.add_event(security_event)
        assert len(buffer.event_buffer) == 2

        third = SecurityEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="ip_banned",
            ip_address="9.9.9.9",
        )
        pending = asyncio.create_task(buffer.add_event(third))
        await asyncio.sleep(0.05)
        assert not pending.done()

        await buffer.flush_events()

        await asyncio.wait_for(pending, timeout=1.0)
        assert third in list(buffer.event_buffer)
        assert buffer.events_dropped == 0

    @pytest.mark.asyncio
    async def test_overflow_policy_block_awaits_until_space_frees_for_metrics(
        self, security_metric: SecurityMetric
    ) -> None:
        config = AgentConfig(api_key="k", buffer_size=2, buffer_overflow_policy="block")
        buffer = EventBuffer(config)

        await buffer.add_metric(security_metric)
        await buffer.add_metric(security_metric)
        assert len(buffer.metric_buffer) == 2

        third = SecurityMetric(
            timestamp=datetime.now(timezone.utc),
            metric_type="request_count",
            value=99.0,
        )
        pending = asyncio.create_task(buffer.add_metric(third))
        await asyncio.sleep(0.05)
        assert not pending.done()

        await buffer.flush_metrics()

        await asyncio.wait_for(pending, timeout=1.0)
        assert third in list(buffer.metric_buffer)
        assert buffer.metrics_dropped == 0

    @pytest.mark.asyncio
    async def test_flush_events_with_keys_no_signal_when_buffer_empty(
        self, buffer: EventBuffer
    ) -> None:
        events, keys = await buffer.flush_events_with_keys()
        assert events == []
        assert keys == []
        assert buffer._event_space_available is None

    @pytest.mark.asyncio
    async def test_flush_metrics_with_keys_no_signal_when_buffer_empty(
        self, buffer: EventBuffer
    ) -> None:
        metrics, keys = await buffer.flush_metrics_with_keys()
        assert metrics == []
        assert keys == []
        assert buffer._metric_space_available is None

    @pytest.mark.asyncio
    async def test_get_space_event_returns_existing_when_already_initialized(
        self,
    ) -> None:
        config = AgentConfig(api_key="k", buffer_size=2, buffer_overflow_policy="block")
        buffer = EventBuffer(config)

        first_event = buffer._get_event_space_event()
        second_event = buffer._get_event_space_event()
        assert first_event is second_event

        first_metric = buffer._get_metric_space_event()
        second_metric = buffer._get_metric_space_event()
        assert first_metric is second_metric

    @pytest.mark.asyncio
    async def test_overflow_policy_block_resumes_via_clear_buffer(
        self, security_event: SecurityEvent, security_metric: SecurityMetric
    ) -> None:
        config = AgentConfig(api_key="k", buffer_size=1, buffer_overflow_policy="block")
        buffer = EventBuffer(config)

        await buffer.add_event(security_event)
        await buffer.add_metric(security_metric)

        pending_event = asyncio.create_task(buffer.add_event(security_event))
        pending_metric = asyncio.create_task(buffer.add_metric(security_metric))
        await asyncio.sleep(0.05)
        assert not pending_event.done()
        assert not pending_metric.done()

        await buffer.clear_buffer()

        await asyncio.wait_for(pending_event, timeout=1.0)
        await asyncio.wait_for(pending_metric, timeout=1.0)
