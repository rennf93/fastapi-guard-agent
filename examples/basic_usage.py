"""
Basic usage example for FastAPI Guard Agent.

This example shows how to:
1. Configure and start the agent
2. Send events and metrics manually
3. Integrate with FastAPI applications
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from guard_agent import (
    AgentConfig,
    guard_agent,
    get_current_timestamp,
    SecurityEvent,
    SecurityMetric,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan for FastAPI application."""
    agent = await get_agent(AgentConfig(
        api_key="demo-api-key-12345",
        project_id="fastapi-demo",
        buffer_size=50,
        flush_interval=30,
    ))
    try:
        yield
    finally:
        await agent.stop()


async def get_agent(config: AgentConfig):
    """Get agent instance."""
    agent = guard_agent(config)
    return agent


async def basic_agent_usage():
    """Example of basic agent usage."""
    print("=== Basic Agent Usage ===")

    # Configure the agent
    config = AgentConfig(
        api_key="demo-api-key-12345",
        project_id="demo-project",
        endpoint="https://api.fastapi-guard.com",
        buffer_size=10,
        flush_interval=5,
    )

    # Get agent instance (singleton)
    agent = guard_agent(config)

    try:
        # Start the agent
        await agent.start()
        print("Agent started successfully")

        # Send some example events
        events = [
            SecurityEvent(
                timestamp=get_current_timestamp(),
                event_type="ip_banned",
                ip_address="192.168.1.100",
                action_taken="banned",
                reason="Rate limit exceeded",
                endpoint="/api/login",
                method="POST",
            ),
            SecurityEvent(
                timestamp=get_current_timestamp(),
                event_type="suspicious_request",
                ip_address="10.0.0.5",
                action_taken="blocked",
                reason="SQL injection detected",
                endpoint="/api/users",
                method="GET",
                metadata={"pattern": "union select", "severity": "high"},
            ),
        ]

        for event in events:
            await agent.send_event(event)
            print(f"Sent event: {event.event_type} from {event.ip_address}")

        # Send some metrics
        metrics = [
            SecurityMetric(
                timestamp=get_current_timestamp(),
                metric_type="request_count",
                value=150.0,
                endpoint="/api/users",
                tags={"method": "GET", "status": "200"},
            ),
            SecurityMetric(
                timestamp=get_current_timestamp(),
                metric_type="response_time",
                value=45.2,
                endpoint="/api/login",
                tags={"method": "POST", "status": "401"},
            ),
        ]

        for metric in metrics:
            await agent.send_metric(metric)
            print(f"Sent metric: {metric.metric_type} = {metric.value}")

        # Get agent status
        status = await agent.get_status()
        print(f"Agent status: {status.status}")
        print(f"Uptime: {status.uptime:.1f}s")
        print(f"Events sent: {status.events_sent}")

        # Wait a bit to see auto-flushing in action
        print("Waiting 10 seconds to see auto-flush...")
        await asyncio.sleep(10)

        # Get updated stats
        stats = agent.get_stats()
        print(f"Final stats: {stats}")

    finally:
        # Stop the agent
        await agent.stop()
        print("Agent stopped")


def create_fastapi_app_with_agent():
    """Example of integrating agent with FastAPI application."""
    print("\n=== FastAPI Integration Example ===")

    app = FastAPI(title="FastAPI Guard Agent Example", lifespan=lifespan)

    # Configure agent
    agent_config = AgentConfig(
        api_key="demo-api-key-12345",
        project_id="fastapi-demo",
        buffer_size=50,
        flush_interval=30,
    )

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {"message": "FastAPI Guard Agent Demo"}

    @app.get("/trigger-event")
    async def trigger_event():
        """Manually trigger a security event."""
        agent = guard_agent(agent_config)

        event = SecurityEvent(
            timestamp=get_current_timestamp(),
            event_type="custom_rule_triggered",
            ip_address="203.0.113.1",
            action_taken="logged",
            reason="Manual test event",
            endpoint="/trigger-event",
            method="GET",
        )

        await agent.send_event(event)
        return {"message": "Security event sent", "event_type": event.event_type}

    @app.get("/agent-status")
    async def agent_status():
        """Get current agent status."""
        agent = guard_agent(agent_config)
        status = await agent.get_status()
        stats = agent.get_stats()

        return {
            "status": status.model_dump(),
            "stats": stats,
        }

    print("FastAPI app created with agent integration")
    print("Endpoints:")
    print("  GET /")
    print("  GET /trigger-event")
    print("  GET /agent-status")

    return app


async def redis_integration_example():
    """Example showing Redis integration."""
    print("\n=== Redis Integration Example ===")

    config = AgentConfig(
        api_key="demo-api-key-12345",
        project_id="redis-demo",
    )

    agent = guard_agent(config)

    # In a real application, you would pass your actual Redis handler
    # from fastapi-guard that implements RedisHandlerProtocol
    print("Redis integration would be initialized like this:")
    print("await agent.initialize_redis(your_redis_handler)")
    print("This enables distributed buffering and persistence")


async def main():
    """Run all examples."""
    print("FastAPI Guard Agent Examples")
    print("=" * 40)

    # Basic usage example
    await basic_agent_usage()

    # FastAPI integration example (just show the setup)
    app = create_fastapi_app_with_agent()

    # Redis integration example
    await redis_integration_example()

    print("\n" + "=" * 40)
    print("Examples completed!")
    print("\nTo run the FastAPI app:")
    print("uvicorn basic_usage:app --reload")


if __name__ == "__main__":
    # Note: This will try to connect to the demo endpoint which doesn't exist
    # In a real implementation, you would have a valid API key and endpoint
    asyncio.run(main())