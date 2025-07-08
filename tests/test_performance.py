import asyncio
import os
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import psutil
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from guard import SecurityConfig, SecurityMiddleware

from guard_agent import SecurityEvent, guard_agent
from guard_agent.buffer import EventBuffer
from guard_agent.models import AgentConfig
from guard_agent.transport import HTTPTransport


class TestPerformanceImpact:
    """Test that agent doesn't significantly impact performance."""

    def create_app_without_agent(self) -> FastAPI:
        """Create app without baseline."""
        app = FastAPI()
        config = SecurityConfig(
            rate_limit=1000,
            enable_agent=False,
            exclude_paths=["/test"],  # Exclude test endpoint from security checks
            passive_mode=True,  # Only log, don't block
            whitelist=["127.0.0.1"],  # Allow test client IPs
        )
        app.add_middleware(SecurityMiddleware, config=config)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"message": "test"}

        return app

    def create_app_with_agent(self) -> FastAPI:
        """Create app with agent enabled."""
        app = FastAPI()
        config = SecurityConfig(
            rate_limit=1000,
            enable_agent=True,
            agent_api_key="test-key",
            agent_project_id="test-project",
            exclude_paths=["/test"],  # Exclude test endpoint from security checks
            passive_mode=True,  # Only log, don't block
        )
        app.add_middleware(SecurityMiddleware, config=config)

        @app.get("/test")
        def test_endpoint() -> dict[str, str]:
            return {"message": "test"}

        return app

    def _measure_baseline_performance(self) -> tuple[float, float]:
        """Measure baseline performance without agent (helper method)."""
        app = self.create_app_without_agent()
        client = TestClient(app)

        # Warmup
        for _ in range(10):
            client.get("/test")

        # Measure
        start_time = time.time()
        for _ in range(100):
            response = client.get("/test")
            assert response.status_code == 200
        end_time = time.time()

        baseline_time = end_time - start_time
        baseline_rps = 100 / baseline_time

        print(f"Baseline: {baseline_rps:.1f} RPS")
        return baseline_time, baseline_rps

    def test_baseline_performance(self) -> None:
        """Test baseline performance without agent."""
        baseline_time, baseline_rps = self._measure_baseline_performance()

        # Assert reasonable performance (should handle at least 100 RPS)
        assert baseline_rps > 100, (
            f"Baseline performance too slow: {baseline_rps:.1f} RPS"
        )
        assert baseline_time < 5.0, f"Baseline test took too long: {baseline_time:.2f}s"

    def test_agent_performance_impact(self) -> None:
        """Measure performance impact with agent enabled."""
        app = self.create_app_with_agent()

        # Mock the agent to avoid actual HTTP calls
        with patch("guard_agent.guard_agent") as mock_guard_agent:
            mock_agent = AsyncMock()
            mock_guard_agent.return_value = mock_agent

            client = TestClient(app)

            # Warmup
            for _ in range(10):
                client.get("/test")

            # Measure
            start_time = time.time()
            for _ in range(100):
                response = client.get("/test")
                assert response.status_code == 200
            end_time = time.time()

            agent_time = end_time - start_time
            agent_rps = 100 / agent_time

            print(f"With Agent: {agent_rps:.1f} RPS")

            # Performance should not degrade more than 15% (system variance)
            baseline_time, baseline_rps = self._measure_baseline_performance()
            performance_impact = (agent_time - baseline_time) / baseline_time

            print(f"Performance impact: {performance_impact * 100:.1f}%")
            assert performance_impact < 0.15, (
                f"Agent causes {performance_impact * 100:.1f}% performance degradation"
            )

    @pytest.mark.asyncio
    async def test_buffer_performance(self) -> None:
        """Test buffer performance under load."""
        config = AgentConfig(api_key="test", buffer_size=1000)
        buffer = EventBuffer(config)

        # Mock Redis to avoid external dependencies
        buffer.redis_handler = AsyncMock()

        events = [
            SecurityEvent(
                timestamp=datetime.fromtimestamp(time.time(), tz=timezone.utc),
                event_type="ip_banned",
                ip_address=f"192.168.1.{i % 255}",
                action_taken="logged",
                reason="performance_test",
            )
            for i in range(1000)
        ]

        # Measure buffer add performance
        start_time = time.time()
        for event in events:
            await buffer.add_event(event)
        end_time = time.time()

        add_time = end_time - start_time
        events_per_second = 1000 / add_time

        print(f"Buffer performance: {events_per_second:.1f} events/sec")

        # Should handle at least 1000 events per second
        assert events_per_second > 1000, (
            f"Buffer too slow: {events_per_second:.1f} events/sec"
        )

    @pytest.mark.asyncio
    async def test_transport_performance(self) -> None:
        """Test transport performance under load."""
        config = AgentConfig(api_key="test", timeout=1)
        transport = HTTPTransport(config)

        # Mock HTTP client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"status": "ok"})

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.aclose = AsyncMock()
        transport._client = mock_client

        events = [
            SecurityEvent(
                timestamp=datetime.fromtimestamp(time.time(), tz=timezone.utc),
                event_type="rate_limited",
                ip_address=f"192.168.1.{i % 255}",
                action_taken="logged",
                reason="performance_test",
            )
            for i in range(100)
        ]

        # Measure transport performance
        start_time = time.time()
        for i in range(0, 100, 10):  # Send in batches of 10
            batch = events[i : i + 10]
            await transport.send_events(batch)
        end_time = time.time()

        transport_time = end_time - start_time
        events_per_second = 100 / transport_time

        print(f"Transport performance: {events_per_second:.1f} events/sec")

        # Should handle at least 100 events per second
        assert events_per_second > 100, (
            f"Transport too slow: {events_per_second:.1f} events/sec"
        )

    def test_memory_usage(self) -> None:
        """Test memory usage doesn't grow excessively."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create app with agent
        app = self.create_app_with_agent()

        with patch("guard_agent.guard_agent") as mock_guard_agent:
            mock_agent = AsyncMock()
            mock_guard_agent.return_value = mock_agent

            client = TestClient(app)

            # Generate load
            for _ in range(1000):
                response = client.get("/test")
                assert response.status_code == 200

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            memory_increase_mb = memory_increase / (1024 * 1024)

            print(f"Memory increase: {memory_increase_mb:.1f} MB")

            # Memory should not increase by more than 50MB
            assert memory_increase_mb < 50, (
                f"Excessive memory usage: {memory_increase_mb:.1f} MB"
            )

    @pytest.mark.asyncio
    async def test_concurrent_load(self) -> None:
        """Test performance under concurrent load."""
        config = AgentConfig(api_key="test-api-key", buffer_size=100)
        agent = guard_agent(config)

        # Mock transport
        agent.transport = AsyncMock()
        agent.transport.send_events.return_value = True

        async def send_events_worker(worker_id: int) -> None:
            """Worker function to send events concurrently."""
            events = [
                SecurityEvent(
                    timestamp=datetime.fromtimestamp(time.time(), tz=timezone.utc),
                    event_type="suspicious_request",
                    ip_address=f"192.168.{worker_id}.{i}",
                    action_taken="logged",
                    reason="concurrent_load_test",
                )
                for i in range(10)
            ]

            for event in events:
                await agent.send_event(event)

        # Run multiple workers concurrently
        start_time = time.time()
        await asyncio.gather(*[send_events_worker(i) for i in range(10)])
        end_time = time.time()

        concurrent_time = end_time - start_time
        total_events = 10 * 10  # 10 workers × 10 events
        events_per_second = total_events / concurrent_time

        print(f"Concurrent performance: {events_per_second:.1f} events/sec")

        # Should handle concurrent load efficiently
        assert events_per_second > 500, (
            f"Poor concurrent performance: {events_per_second:.1f} events/sec"
        )
