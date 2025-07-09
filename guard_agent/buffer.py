import asyncio

# import json
import logging
import time
from collections import deque
from typing import Any

from guard_agent.models import AgentConfig, SecurityEvent, SecurityMetric
from guard_agent.protocols import BufferProtocol, RedisHandlerProtocol
from guard_agent.utils import (
    safe_json_deserialize,
    safe_json_serialize,
)  # , get_current_timestamp


class EventBuffer(BufferProtocol):
    """
    Event buffer with Redis persistence and automatic flushing.
    Follows fastapi-guard handler patterns.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # In-memory buffers
        self.event_buffer: deque[SecurityEvent] = deque(maxlen=config.buffer_size)
        self.metric_buffer: deque[SecurityMetric] = deque(maxlen=config.buffer_size)

        # Redis integration
        self.redis_handler: RedisHandlerProtocol | None = None

        # Flush management
        self._flush_task: asyncio.Task | None = None
        self._running = False

        # Statistics
        self.events_buffered = 0
        self.metrics_buffered = 0
        self.events_flushed = 0
        self.metrics_flushed = 0
        self.last_flush_time: float | None = None

    async def initialize_redis(self, redis_handler: RedisHandlerProtocol) -> None:
        """Initialize Redis connection for persistent buffering."""
        self.redis_handler = redis_handler
        await self._load_from_redis()

    async def start_auto_flush(self) -> None:
        """Start automatic buffer flushing."""
        if self._flush_task and not self._flush_task.done():
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._auto_flush_loop())

    async def stop_auto_flush(self) -> None:
        """Stop automatic buffer flushing."""
        self._running = False
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

    async def add_event(self, event: SecurityEvent) -> None:
        """Add security event to buffer."""
        try:
            self.event_buffer.append(event)
            self.events_buffered += 1

            # Persist to Redis if available
            if self.redis_handler:
                await self._persist_event_to_redis(event)

            # Check if buffer is full and needs immediate flush
            if len(self.event_buffer) >= self.config.buffer_size:
                asyncio.create_task(self._flush_if_needed())

        except Exception as e:
            self.logger.error(f"Failed to buffer event: {str(e)}")

    async def add_metric(self, metric: SecurityMetric) -> None:
        """Add metric to buffer."""
        try:
            self.metric_buffer.append(metric)
            self.metrics_buffered += 1

            # Persist to Redis if available
            if self.redis_handler:
                await self._persist_metric_to_redis(metric)

            # Check if buffer is full and needs immediate flush
            if len(self.metric_buffer) >= self.config.buffer_size:
                asyncio.create_task(self._flush_if_needed())

        except Exception as e:
            self.logger.error(f"Failed to buffer metric: {str(e)}")

    async def flush_events(self) -> list[SecurityEvent]:
        """Flush and return all buffered events."""
        events = list(self.event_buffer)
        self.event_buffer.clear()
        self.events_flushed += len(events)

        # Clear from Redis
        if self.redis_handler and events:
            await self._clear_events_from_redis(len(events))

        self.last_flush_time = time.time()
        return events

    async def flush_metrics(self) -> list[SecurityMetric]:
        """Flush and return all buffered metrics."""
        metrics = list(self.metric_buffer)
        self.metric_buffer.clear()
        self.metrics_flushed += len(metrics)

        # Clear from Redis
        if self.redis_handler and metrics:
            await self._clear_metrics_from_redis(len(metrics))

        self.last_flush_time = time.time()
        return metrics

    async def get_buffer_size(self) -> int:
        """Get current total buffer size."""
        return len(self.event_buffer) + len(self.metric_buffer)

    async def clear_buffer(self) -> None:
        """Clear all buffers."""
        self.event_buffer.clear()
        self.metric_buffer.clear()

        if self.redis_handler:
            await self._clear_redis_buffers()

    async def _auto_flush_loop(self) -> None:
        """Automatic flush loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                if self._running:
                    await self._flush_if_needed()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in auto flush loop: {str(e)}")

    async def _flush_if_needed(self) -> None:
        """Check if flush is needed and perform it."""
        current_time = time.time()

        # Check if it's time to flush based on interval
        time_since_last_flush = (
            current_time - self.last_flush_time
            if self.last_flush_time
            else self.config.flush_interval + 1
        )

        # Flush if buffer is getting full or enough time has passed
        buffer_size = await self.get_buffer_size()
        should_flush = (
            buffer_size >= self.config.buffer_size * 0.8
            or time_since_last_flush >= self.config.flush_interval
        )

        if should_flush and buffer_size > 0:
            self.logger.debug(f"Triggering buffer flush - size: {buffer_size}")
            # Note: This method doesn't actually send data, just marks it ready
            # The actual sending is handled by the transport layer

    async def _persist_event_to_redis(self, event: SecurityEvent) -> None:
        """Persist event to Redis for durability."""
        if not self.redis_handler:
            return

        try:
            key = f"event_{int(time.time() * 1000)}"
            serialized = await safe_json_serialize(event.model_dump())
            await self.redis_handler.set_key(
                "agent_events",
                key,
                serialized,
                ttl=3600,  # 1 hour TTL
            )
        except Exception as e:
            self.logger.warning(f"Failed to persist event to Redis: {str(e)}")

    async def _persist_metric_to_redis(self, metric: SecurityMetric) -> None:
        """Persist metric to Redis for durability."""
        if not self.redis_handler:
            return

        try:
            key = f"metric_{int(time.time() * 1000)}"
            serialized = await safe_json_serialize(metric.model_dump())
            await self.redis_handler.set_key(
                "agent_metrics",
                key,
                serialized,
                ttl=3600,  # 1 hour TTL
            )
        except Exception as e:
            self.logger.warning(f"Failed to persist metric to Redis: {str(e)}")

    async def _load_from_redis(self) -> None:
        """Load any persisted events/metrics from Redis on startup."""
        if not self.redis_handler:
            return

        try:
            # Load events from Redis
            event_keys = await self.redis_handler.keys("agent_events:*") or []
            for key in event_keys:
                try:
                    event_data = await self.redis_handler.get_key(
                        "agent_events", key.split(":")[-1]
                    )
                    if event_data:
                        event_dict = await safe_json_deserialize(event_data)
                        if event_dict:
                            event = SecurityEvent(**event_dict)
                            self.event_buffer.append(event)
                            self.events_buffered += 1
                    else:
                        message = f"Failed to load event from Redis key {key}"
                        self.logger.warning(f"{message}: No data found for key")
                except Exception as e:
                    self.logger.warning(
                        f"Failed to load event from Redis key {key}: {e}"
                    )

            # Load metrics from Redis
            metric_keys = await self.redis_handler.keys("agent_metrics:*") or []
            for key in metric_keys:
                try:
                    metric_data = await self.redis_handler.get_key(
                        "agent_metrics", key.split(":")[-1]
                    )
                    if metric_data:
                        metric_dict = await safe_json_deserialize(metric_data)
                        if metric_dict:
                            metric = SecurityMetric(**metric_dict)
                            self.metric_buffer.append(metric)
                            self.metrics_buffered += 1
                    else:
                        message = f"Failed to load metric from Redis key {key}"
                        self.logger.warning(f"{message}: No data found for key")
                except Exception as e:
                    self.logger.warning(
                        f"Failed to load metric from Redis key {key}: {e}"
                    )

            if self.event_buffer or self.metric_buffer:
                loaded_events = f"Loaded {len(self.event_buffer)} events"
                loaded_metrics = f"Loaded {len(self.metric_buffer)} metrics"
                self.logger.info(f"{loaded_events} and {loaded_metrics} from Redis")

        except Exception as e:
            self.logger.warning(f"Failed to load from Redis: {str(e)}")

    async def _clear_events_from_redis(self, count: int) -> None:
        """Clear flushed events from Redis."""
        if not self.redis_handler:
            return

        try:
            # Get event keys and delete the oldest ones
            event_keys = await self.redis_handler.keys("agent_events:*") or []
            # Sort keys to get oldest first (assuming timestamp-based keys)
            sorted_keys = sorted(event_keys)

            # Delete the specified number of oldest events
            for i, key in enumerate(sorted_keys):
                if i >= count:
                    break
                key_name = key.split(":")[-1]
                await self.redis_handler.delete("agent_events", key_name)

        except Exception as e:
            self.logger.warning(f"Failed to clear events from Redis: {str(e)}")

    async def _clear_metrics_from_redis(self, count: int) -> None:
        """Clear flushed metrics from Redis."""
        if not self.redis_handler:
            return

        try:
            # Get metric keys and delete the oldest ones
            metric_keys = await self.redis_handler.keys("agent_metrics:*") or []
            # Sort keys to get oldest first (assuming timestamp-based keys)
            sorted_keys = sorted(metric_keys)

            # Delete the specified number of oldest metrics
            for i, key in enumerate(sorted_keys):
                if i >= count:
                    break
                key_name = key.split(":")[-1]
                await self.redis_handler.delete("agent_metrics", key_name)

        except Exception as e:
            self.logger.warning(f"Failed to clear metrics from Redis: {str(e)}")

    async def _clear_redis_buffers(self) -> None:
        """Clear all Redis buffers."""
        if not self.redis_handler:
            return

        try:
            # Clear all events
            event_keys = await self.redis_handler.keys("agent_events:*") or []
            for key in event_keys:
                key_name = key.split(":")[-1]
                await self.redis_handler.delete("agent_events", key_name)

            # Clear all metrics
            metric_keys = await self.redis_handler.keys("agent_metrics:*") or []
            for key in metric_keys:
                key_name = key.split(":")[-1]
                await self.redis_handler.delete("agent_metrics", key_name)

            self.logger.info("Cleared all Redis buffers")

        except Exception as e:
            self.logger.warning(f"Failed to clear Redis buffers: {str(e)}")

    def get_stats(self) -> dict[str, Any]:
        """Get buffer statistics."""
        return {
            "events_buffered": self.events_buffered,
            "metrics_buffered": self.metrics_buffered,
            "events_flushed": self.events_flushed,
            "metrics_flushed": self.metrics_flushed,
            "current_event_buffer_size": len(self.event_buffer),
            "current_metric_buffer_size": len(self.metric_buffer),
            "last_flush_time": self.last_flush_time,
            "auto_flush_running": self._running,
        }
