from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgentConfig(BaseModel):
    """Agent configuration following SecurityConfig pattern."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    api_key: str = Field(description="Guard Agent API key")
    endpoint: str = Field(
        default="https://api.fastapi-guard.com", description="Agent endpoint URL"
    )
    project_id: str | None = Field(
        default=None, description="Project ID for organization"
    )

    # Buffering configuration
    buffer_size: int = Field(default=100, description="Event buffer size")
    flush_interval: int = Field(
        default=30, description="Buffer flush interval in seconds"
    )

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
        description="Headers to exclude from telemetry",
    )
    max_payload_size: int = Field(
        default=1024, description="Maximum payload size to include in events (bytes)"
    )

    @field_validator("endpoint")  # type: ignore
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Validate that endpoint is a valid URL."""
        if not v:
            raise ValueError("Endpoint URL cannot be empty")

        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Endpoint must be a valid URL with scheme and domain")

        if parsed.scheme not in ("http", "https"):
            raise ValueError("Endpoint URL must use http or https scheme")

        return v


class SecurityEvent(BaseModel):
    """Security event model for telemetry."""

    timestamp: datetime
    event_type: Literal[
        "ip_banned",
        "ip_unbanned",
        "ip_blocked",
        "rate_limited",
        "suspicious_request",
        "cloud_blocked",
        "country_blocked",
        "penetration_attempt",
        "behavioral_violation",
        "user_agent_blocked",
        "custom_rule_triggered",
        "decorator_violation",
        "geo_lookup_failed",
        "redis_connection",
        "redis_error",
        "dynamic_rule_applied",
        "dynamic_rule_updated",
        "path_excluded",
        "pattern_detected",
        "pattern_added",
        "pattern_removed",
        "access_denied",
        "authentication_failed",
        "content_filtered",
        "emergency_mode_activated",
        "emergency_mode_block",
        "dynamic_rule_violation",
        "security_bypass",
        "config_violation",
        "protocol_violation",
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
    decorator_type: str | None = None
    rule_type: str | None = None
    pattern_matched: str | None = None
    handler_name: str | None = None
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
        "cache_hit_rate",
    ]
    value: float
    endpoint: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class DynamicRules(BaseModel):
    """Dynamic rules received from SaaS platform."""

    # Rule metadata
    rule_id: str = Field(default="default-rule", description="Unique rule ID")
    version: int = Field(default=1, description="Rule version number")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Rule creation/update timestamp",
    )
    expires_at: datetime | None = Field(
        default=None, description="Rule expiration time"
    )
    ttl: int = Field(default=300, description="Cache TTL in seconds")

    # IP management rules
    ip_blacklist: list[str] = Field(default_factory=list, description="IPs to ban")
    ip_whitelist: list[str] = Field(default_factory=list, description="IPs to allow")
    ip_ban_duration: int = Field(default=3600, description="Ban duration in seconds")

    # Country/geo rules
    blocked_countries: list[str] = Field(
        default_factory=list, description="Countries to block"
    )
    whitelist_countries: list[str] = Field(
        default_factory=list, description="Countries to allow"
    )

    # Rate limiting rules
    global_rate_limit: int | None = Field(default=None, description="Global rate limit")
    global_rate_window: int | None = Field(
        default=None, description="Global rate window"
    )
    endpoint_rate_limits: dict[str, tuple[int, int]] = Field(
        default_factory=dict,
        description="Per-endpoint rate limits {endpoint: (requests, window)}",
    )

    # Cloud provider rules
    blocked_cloud_providers: set[str] = Field(
        default_factory=set, description="Cloud providers to block"
    )

    # User agent rules
    blocked_user_agents: list[str] = Field(
        default_factory=list, description="User agents to block"
    )

    # Pattern rules
    suspicious_patterns: list[str] = Field(
        default_factory=list, description="Additional suspicious patterns"
    )

    # Feature toggles
    enable_penetration_detection: bool | None = Field(
        default=None, description="Override penetration detection setting"
    )
    enable_ip_banning: bool | None = Field(
        default=None, description="Override IP banning setting"
    )
    enable_rate_limiting: bool | None = Field(
        default=None, description="Override rate limiting setting"
    )

    # Emergency controls
    emergency_mode: bool = Field(default=False, description="Emergency lockdown mode")
    emergency_whitelist: list[str] = Field(
        default_factory=list, description="Emergency whitelist IPs"
    )


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
