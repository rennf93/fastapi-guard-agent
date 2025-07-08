import asyncio
import logging
import time
from typing import Any

from guard_agent.buffer import EventBuffer
from guard_agent.models import (
    AgentConfig,
    AgentStatus,
    DynamicRules,
    SecurityEvent,
    SecurityMetric,
)
from guard_agent.protocols import AgentHandlerProtocol, RedisHandlerProtocol
from guard_agent.transport import HTTPTransport
from guard_agent.utils import (
    get_current_timestamp,
    validate_config,
)  # , setup_agent_logging


class GuardAgentHandler(AgentHandlerProtocol):
    """
    Main agent handler following fastapi-guard handler patterns.
    Implements singleton pattern with Redis integration and automatic flushing.
    """

    _instance: "GuardAgentHandler | None" = None
    _initialized: bool

    def __new__(cls, config: AgentConfig) -> "GuardAgentHandler":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: AgentConfig):
        # Prevent re-initialization of singleton
        if hasattr(self, "_initialized") and self._initialized:
            # Update config if needed
            self.config = config
            return

        self.config = config
        self.logger = logging.getLogger(__name__)

        # Validate configuration
        config_errors = validate_config(config)
        if config_errors:
            raise ValueError(f"Invalid agent configuration: {'; '.join(config_errors)}")

        # Core components
        self.buffer = EventBuffer(config)
        self.transport = HTTPTransport(config)

        # Redis integration
        self.redis_handler: RedisHandlerProtocol | None = None

        # Lifecycle management
        self._running = False
        self._flush_task: asyncio.Task | None = None
        self._status_task: asyncio.Task | None = None
        self._rules_task: asyncio.Task | None = None
        self._start_time = time.time()

        # Statistics
        self.events_sent = 0
        self.metrics_sent = 0
        self.events_failed = 0
        self.metrics_failed = 0
        self.rules_fetched = 0

        # Dynamic rules cache
        self._cached_rules: DynamicRules | None = None
        self._rules_last_update: float = 0

        self._initialized = True
        self.logger.info("Guard Agent Handler initialized")

    async def initialize_redis(self, redis_handler: RedisHandlerProtocol) -> None:
        """Initialize Redis connection following fastapi-guard pattern."""
        self.redis_handler = redis_handler
        await self.buffer.initialize_redis(redis_handler)
        self.logger.info("Redis integration initialized")

    async def start(self) -> None:
        """Start the agent with all background tasks."""
        if self._running:
            self.logger.warning("Agent is already running")
            return

        try:
            # Initialize transport
            await self.transport.initialize()

            # Start buffer auto-flush
            await self.buffer.start_auto_flush()

            # Start background tasks
            self._running = True
            self._flush_task = asyncio.create_task(self._flush_loop())
            self._status_task = asyncio.create_task(self._status_loop())

            # Start rules fetching if enabled
            if self.config.project_id:
                self._rules_task = asyncio.create_task(self._rules_loop())

            self.logger.info("Guard Agent started successfully")

        except Exception as e:
            self.logger.error(f"Failed to start agent: {str(e)}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the agent and cleanup resources."""
        self._running = False

        # Cancel background tasks
        tasks = [self._flush_task, self._status_task, self._rules_task]
        for task in tasks:
            if task and not task.done():
                task.cancel()

        # Wait for tasks to complete
        for task in tasks:
            if task:
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Stop buffer auto-flush
        await self.buffer.stop_auto_flush()

        # Final flush
        await self.flush_buffer()

        # Close transport
        await self.transport.close()

        self.logger.info("Guard Agent stopped")

    async def send_event(self, event: SecurityEvent) -> None:
        """Send security event through buffer."""
        if not self.config.enable_events:
            return

        try:
            await self.buffer.add_event(event)
            self.logger.debug(
                f"Event buffered: {event.event_type} from {event.ip_address}"
            )
        except Exception as e:
            self.logger.error(f"Failed to buffer event: {str(e)}")

    async def send_metric(self, metric: SecurityMetric) -> None:
        """Send metric through buffer."""
        if not self.config.enable_metrics:
            return

        try:
            await self.buffer.add_metric(metric)
            self.logger.debug(f"Metric buffered: {metric.metric_type} = {metric.value}")
        except Exception as e:
            self.logger.error(f"Failed to buffer metric: {str(e)}")

    async def get_dynamic_rules(self) -> DynamicRules | None:
        """Get cached dynamic rules or fetch fresh ones."""
        current_time = time.time()

        # Check if cached rules are still valid
        if (
            self._cached_rules
            and current_time - self._rules_last_update < self._cached_rules.ttl
        ):
            return self._cached_rules

        # Fetch fresh rules
        try:
            rules = await self.transport.fetch_dynamic_rules()
            if rules:
                self._cached_rules = rules
                self._rules_last_update = current_time
                self.rules_fetched += 1
                self.logger.debug("Dynamic rules updated")
            return rules
        except Exception as e:
            self.logger.error(f"Failed to fetch dynamic rules: {str(e)}")
            return self._cached_rules  # Return cached rules as fallback

    async def flush_buffer(self) -> None:
        """Manually flush all buffers."""
        try:
            # Flush events
            events = await self.buffer.flush_events()
            if events:
                success = await self.transport.send_events(events)
                if success:
                    self.events_sent += len(events)
                    self.logger.debug(f"Flushed {len(events)} events")
                else:
                    self.events_failed += len(events)
                    self.logger.warning(f"Failed to send {len(events)} events")

            # Flush metrics
            metrics = await self.buffer.flush_metrics()
            if metrics:
                success = await self.transport.send_metrics(metrics)
                if success:
                    self.metrics_sent += len(metrics)
                    self.logger.debug(f"Flushed {len(metrics)} metrics")
                else:
                    self.metrics_failed += len(metrics)
                    self.logger.warning(f"Failed to send {len(metrics)} metrics")

        except Exception as e:
            self.logger.error(f"Error during buffer flush: {str(e)}")

    async def get_status(self) -> AgentStatus:
        """Get current agent status."""
        current_time = get_current_timestamp()
        uptime = time.time() - self._start_time
        buffer_size = await self.buffer.get_buffer_size()

        # Determine health status
        transport_stats = self.transport.get_stats()
        buffer_stats = self.buffer.get_stats()

        status = "healthy"
        errors = []

        # Check for issues
        if transport_stats["circuit_breaker_state"] == "OPEN":
            status = "degraded"
            errors.append("Transport circuit breaker is open")

        if buffer_size >= self.config.buffer_size * 0.9:
            status = "degraded"
            errors.append("Buffer nearly full")

        if self.events_failed + self.metrics_failed > 0:
            failure_rate = (self.events_failed + self.metrics_failed) / max(
                1,
                self.events_sent
                + self.metrics_sent
                + self.events_failed
                + self.metrics_failed,
            )
            if failure_rate > 0.1:  # 10% failure rate
                status = "degraded"
                errors.append(f"High failure rate: {failure_rate:.1%}")

        return AgentStatus(
            timestamp=current_time,
            status=status,
            uptime=uptime,
            events_sent=self.events_sent,
            events_failed=self.events_failed,
            buffer_size=buffer_size,
            last_flush=buffer_stats.get("last_flush_time"),
            errors=errors,
        )

    async def close(self) -> None:
        """Close agent and cleanup resources."""
        await self.stop()

    async def _flush_loop(self) -> None:
        """Background flush loop."""
        while self._running:
            try:
                await asyncio.sleep(self.config.flush_interval)
                if self._running:
                    await self.flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in flush loop: {str(e)}")

    async def _status_loop(self) -> None:
        """Background status reporting loop."""
        while self._running:
            try:
                # Send status every 5 minutes
                await asyncio.sleep(300)
                if self._running:
                    status = await self.get_status()
                    await self.transport.send_status(status)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in status loop: {str(e)}")

    async def _rules_loop(self) -> None:
        """Background dynamic rules fetching loop."""
        while self._running:
            try:
                # Fetch rules every 5 minutes
                await asyncio.sleep(300)
                if self._running:
                    await self.get_dynamic_rules()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in rules loop: {str(e)}")

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive agent statistics."""
        return {
            "running": self._running,
            "uptime": time.time() - self._start_time,
            "events_sent": self.events_sent,
            "metrics_sent": self.metrics_sent,
            "events_failed": self.events_failed,
            "metrics_failed": self.metrics_failed,
            "rules_fetched": self.rules_fetched,
            "buffer_stats": self.buffer.get_stats(),
            "transport_stats": self.transport.get_stats(),
            "cached_rules": self._cached_rules is not None,
            "rules_last_update": self._rules_last_update,
        }

    async def health_check(self) -> bool:
        """
        Check if the agent is healthy and connected.

        Returns:
            True if agent is healthy, False otherwise
        """
        if not self._running:
            return False

        try:
            # Check transport health
            transport_stats = self.transport.get_stats()
            if transport_stats.get("circuit_breaker_state") == "OPEN":
                return False

            # Check buffer health
            buffer_size = await self.buffer.get_buffer_size()
            if buffer_size >= self.config.buffer_size * 0.95:  # 95% full
                return False

            # Check failure rates
            total_sent = self.events_sent + self.metrics_sent
            total_failed = self.events_failed + self.metrics_failed
            total_attempts = total_sent + total_failed

            if total_attempts > 0:
                failure_rate = total_failed / total_attempts
                if failure_rate > 0.5:  # 50% failure rate
                    return False

            return True
        except Exception as e:
            self.logger.error(f"Error during health check: {str(e)}")
            return False


# Singleton factory function following fastapi-guard pattern
def guard_agent(config: AgentConfig) -> GuardAgentHandler:
    """
    Factory function for GuardAgentHandler singleton.
    Follows the same pattern as other fastapi-guard handlers.
    """
    return GuardAgentHandler(config)
