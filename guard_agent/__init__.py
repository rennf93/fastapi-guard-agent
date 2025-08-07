"""
FastAPI Guard Agent - Telemetry and monitoring agent for FastAPI Guard.

This library provides telemetry capabilities for the FastAPI Guard security middleware,
enabling monitoring, analytics, and dynamic rule management through a SaaS platform.
"""

from guard_agent.buffer import EventBuffer
from guard_agent.client import GuardAgentHandler, guard_agent
from guard_agent.models import (
    AgentConfig,
    AgentStatus,
    DynamicRules,
    EventBatch,
    SecurityEvent,
    SecurityMetric,
)
from guard_agent.protocols import (
    AgentHandlerProtocol,
    BufferProtocol,
    RedisHandlerProtocol,
    TransportProtocol,
)
from guard_agent.transport import HTTPTransport
from guard_agent.utils import (
    CircuitBreaker,
    RateLimiter,
    generate_batch_id,
    get_current_timestamp,
    hash_ip,
    sanitize_headers,
    setup_agent_logging,
    truncate_payload,
    validate_config,
)

__version__ = "1.0.1"

__all__ = [
    # Main components
    "guard_agent",
    "GuardAgentHandler",
    "AgentConfig",
    # Models
    "SecurityEvent",
    "SecurityMetric",
    "DynamicRules",
    "AgentStatus",
    "EventBatch",
    # Core components
    "EventBuffer",
    "HTTPTransport",
    # Protocols
    "AgentHandlerProtocol",
    "TransportProtocol",
    "BufferProtocol",
    "RedisHandlerProtocol",
    # Utilities
    "generate_batch_id",
    "get_current_timestamp",
    "hash_ip",
    "sanitize_headers",
    "truncate_payload",
    "validate_config",
    "setup_agent_logging",
    "RateLimiter",
    "CircuitBreaker",
    # Version
    "__version__",
]
