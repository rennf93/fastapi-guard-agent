"""
Basic usage example for FastAPI Guard Agent.

This example shows how to:
1. Integrate FastAPI Guard Agent with FastAPI Guard (recommended)
2. Use direct agent API for custom events (advanced)
3. Monitor agent status and health
"""

import asyncio
from typing import Any

from fastapi import FastAPI, Request
from guard import SecurityConfig, SecurityMiddleware
from guard.decorators import SecurityDecorator

from guard_agent import (
    AgentConfig,
    SecurityEvent,
    SecurityMetric,
    get_current_timestamp,
    guard_agent,
)


async def basic_agent_usage() -> None:
    """Example of direct agent usage (ADVANCED USERS ONLY).

    NOTE: Most users should use the automatic integration with FastAPI Guard
    shown in create_fastapi_app_with_agent() above. Direct usage is only
    needed for custom events or when not using FastAPI Guard.
    """
    print("\n=== Direct Agent Usage (Advanced) ===")
    print("NOTE: This is for advanced use cases only!")
    print("Most users should use the automatic integration with FastAPI Guard.\n")

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
        # Start the agent (only needed for direct usage)
        await agent.start()
        print("Agent started manually (for demonstration)")

        # Example: Send custom business logic events
        custom_event = SecurityEvent(
            timestamp=get_current_timestamp(),
            event_type="custom_business_rule",
            ip_address="192.168.1.100",
            action_taken="logged",
            reason="Custom validation failed",
            endpoint="/api/custom",
            method="POST",
            metadata={"rule": "business_logic_1", "severity": "medium"},
        )

        await agent.send_event(custom_event)
        print(f"Sent custom event: {custom_event.event_type}")

        # Example: Send custom metrics
        custom_metric = SecurityMetric(
            timestamp=get_current_timestamp(),
            metric_type="custom_metric",
            value=42.0,
            endpoint="/api/custom",
            tags={"type": "business_metric", "category": "validation"},
        )

        await agent.send_metric(custom_metric)
        print(
            f"Sent custom metric: {custom_metric.metric_type} = {custom_metric.value}"
        )

        # Get agent status
        status = await agent.get_status()
        print(f"\nDirect agent status: {status.status}")
        print(f"Events processed: {status.events_processed}")

    finally:
        # Stop the agent (only needed for direct usage)
        await agent.stop()
        print("Agent stopped (manual cleanup)")


def create_fastapi_app_with_agent() -> FastAPI:
    """Example of integrating agent with FastAPI Guard (RECOMMENDED)."""
    print("\n=== FastAPI Guard + Agent Integration (Recommended) ===")

    app = FastAPI(title="FastAPI Guard Agent Example")

    # Configure FastAPI Guard with agent enabled
    config = SecurityConfig(
        # Basic security settings
        auto_ban_threshold=5,
        auto_ban_duration=300,
        enable_rate_limiting=True,
        rate_limit=100,
        rate_limit_window=60,

        # Enable agent for telemetry
        enable_agent=True,
        agent_api_key="demo-api-key-12345",
        agent_project_id="fastapi-demo",
        agent_endpoint="https://api.fastapi-guard.com",

        # Agent configuration
        agent_buffer_size=50,
        agent_flush_interval=30,
        agent_enable_events=True,
        agent_enable_metrics=True,

        # Enable dynamic rules from SaaS
        enable_dynamic_rules=True,
        dynamic_rule_interval=300,
    )

    # Add security middleware - agent starts automatically
    middleware = SecurityMiddleware(app, config=config)

    # Create decorator instance for enhanced security
    guard = SecurityDecorator(config)
    middleware.set_decorator_handler(guard)

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {"message": "FastAPI Guard Agent Demo - Automatic Integration"}

    @app.get("/protected")
    @guard.rate_limit(requests=5, window=60)
    async def protected_endpoint() -> dict[str, str]:
        """Rate limited endpoint - violations automatically sent to agent."""
        return {"message": "This endpoint is rate limited"}

    @app.get("/admin")
    @guard.require_ip(whitelist=["127.0.0.1", "10.0.0.0/8"])
    @guard.rate_limit(requests=2, window=300)
    async def admin_endpoint() -> dict[str, str]:
        """Admin endpoint - all security events automatically tracked."""
        return {"message": "Admin access granted"}

    @app.get("/api/data")
    @guard.block_countries(["CN", "RU"])
    @guard.rate_limit(requests=10, window=60)
    async def api_endpoint() -> dict[str, str]:
        """API endpoint with country blocking - events sent automatically."""
        return {"data": "Sensitive information"}

    @app.get("/custom-event")
    async def trigger_custom_event(request: Request) -> dict[str, str]:
        """Example of sending custom events through direct agent access."""
        # Get agent instance (singleton) - only for custom events
        agent_config = AgentConfig(
            api_key="demo-api-key-12345",
            project_id="fastapi-demo",
        )
        agent = guard_agent(agent_config)

        # Send custom business logic event
        event = SecurityEvent(
            timestamp=get_current_timestamp(),
            event_type="custom_rule_triggered",
            ip_address=request.client.host,
            action_taken="logged",
            reason="Custom business logic event",
            endpoint="/custom-event",
            method="GET",
            metadata={"custom_field": "custom_value"}
        )

        await agent.send_event(event)
        return {"message": "Custom event sent", "event_type": event.event_type}

    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Health check including agent status."""
        # Agent is managed by FastAPI Guard, but we can check its status
        agent_config = AgentConfig(
            api_key="demo-api-key-12345",
            project_id="fastapi-demo",
        )
        agent = guard_agent(agent_config)  # Get singleton instance

        try:
            status = await agent.get_status()
            stats = agent.get_stats()

            return {
                "app": "healthy",
                "agent": {
                    "status": status.status,
                    "uptime": status.uptime,
                    "events_sent": status.events_sent,
                    "buffer_size": status.buffer_size,
                    "transport_stats": stats.get("transport_stats", {})
                }
            }
        except Exception as e:
            return {
                "app": "healthy",
                "agent": {"status": "error", "error": str(e)}
            }

    print("FastAPI app created with automatic agent integration")
    print("Endpoints:")
    print("  GET /                - Basic endpoint")
    print("  GET /protected       - Rate limited (5 req/min)")
    print("  GET /admin           - IP whitelist + rate limit")
    print("  GET /api/data        - Country blocking + rate limit")
    print("  GET /custom-event    - Send custom events")
    print("  GET /health          - Health check with agent status")
    print("\nAll security violations are automatically sent to the agent!")

    return app


async def integrated_app_example() -> None:
    """Example showing the complete integration with FastAPI Guard."""
    print("\n=== Complete Integration Example ===")

    print("When using FastAPI Guard with agent enabled:")
    print("1. Agent starts automatically with SecurityMiddleware")
    print("2. All security events are collected automatically:")
    print("   - IP bans and blocks")
    print("   - Rate limit violations")
    print("   - Country/region blocks")
    print("   - Suspicious request patterns")
    print("   - Authentication failures")
    print("   - Custom security rules")
    print("3. Performance metrics are collected")
    print("4. Dynamic rules are fetched from SaaS")
    print("5. Redis integration is handled by FastAPI Guard")
    print("\nNo manual agent management needed!")


async def main() -> None:
    """Run all examples."""
    print("FastAPI Guard Agent Examples")
    print("=" * 40)

    # Show recommended integration first
    app = create_fastapi_app_with_agent()

    # Show complete integration benefits
    await integrated_app_example()

    # Basic direct usage example (advanced users)
    await basic_agent_usage()

    print("\n" + "=" * 40)
    print("Examples completed!")
    print("\nTo run the FastAPI app with automatic agent integration:")
    print("uvicorn examples.basic_usage:app --reload")
    print("\nThe agent will start automatically and collect all security events!")


# Export the app for uvicorn
app = create_fastapi_app_with_agent()

if __name__ == "__main__":
    # Note: This will try to connect to the demo endpoint which doesn't exist
    # In a real implementation, you would have a valid API key and endpoint
    asyncio.run(main())
