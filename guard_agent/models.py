from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentConfig(BaseModel):
    """Agent configuration following SecurityConfig pattern."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    api_key: str = Field(description="Guard Agent API key")
    endpoint: str = Field(
        default="https://api.fastapi-guard.com",
        description="Agent endpoint URL"
    )
    project_id: str | None = Field(default=None, description="Project ID for organization")

    # Buffering configuration
    buffer_size: int = Field(default=100, description="Event buffer size")
    flush_interval: int = Field(default=30, description="Buffer flush interval in seconds")

    # Feature toggles
    enable_metrics: bool = Field(default=True, description="Send performance metrics")
    enable_events: bool = Field(default=True, description="Send security events")

    # HTTP configuration
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    backoff_factor: float = Field(default=1.0, description="Backoff factor for retries")

    # Data filtering
    sensitive_headers: list[str] = Field(
        default_factory=lambda: ["authorization", "cookie", "x-api-key"],
        description="Headers to exclude from telemetry"
    )
    max_payload_size: int = Field(
        default=1024,
        description="Maximum payload size to include in events (bytes)"
    )


class SecurityEvent(BaseModel):
    """Security event model for telemetry."""

    timestamp: datetime
    event_type: Literal[
        "ip_banned",
        "rate_limited",
        "suspicious_request",
        "cloud_blocked",
        "country_blocked",
        "penetration_attempt",
        "behavioral_violation",
        "user_agent_blocked",
        "custom_rule_triggered"
    ]
    ip_address: str
    country: str | None = None
    user_agent: str | None = None
    action_taken: str
    reason: str
    endpoint: str | None = None
    method: str | None = None
    status_code: int | None = None
    response_time: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityMetric(BaseModel):
    """Performance and usage metrics."""

    timestamp: datetime
    metric_type: Literal[
        "request_count",
        "response_time",
        "error_rate",
        "bandwidth_usage",
        "threat_level",
        "block_rate",
        "cache_hit_rate"
    ]
    value: float
    endpoint: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class DynamicRules(BaseModel):
    """Dynamic rules received from SaaS platform."""

    ip_blacklist: list[str] = Field(default_factory=list)
    ip_whitelist: list[str] = Field(default_factory=list)
    rate_limits: dict[str, int] = Field(default_factory=dict)
    country_blocks: list[str] = Field(default_factory=list)
    custom_patterns: list[str] = Field(default_factory=list)
    updated_at: datetime
    ttl: int = Field(default=3600, description="Time to live in seconds")


class AgentStatus(BaseModel):
    """Agent health and status information."""

    timestamp: datetime
    status: Literal["healthy", "degraded", "failed"]
    uptime: float
    events_sent: int
    events_failed: int
    buffer_size: int
    last_flush: datetime | None = None
    errors: list[str] = Field(default_factory=list)


class EventBatch(BaseModel):
    """Batch of events/metrics for efficient transmission."""

    project_id: str
    events: list[SecurityEvent] = Field(default_factory=list)
    metrics: list[SecurityMetric] = Field(default_factory=list)
    batch_id: str
    created_at: datetime
    compressed: bool = Field(default=False)
