"""
Guard Agent — framework-agnostic telemetry agent for the Guard ecosystem.

Provides telemetry capabilities for the Guard adapters (``fastapi-guard``,
``flaskapi-guard``, ``djangoapi-guard``, ``tornadoapi-guard``), enabling
monitoring, analytics, and dynamic rule management through a centralized
management platform.
"""

from guard_agent._version import __version__
from guard_agent.buffer import EventBuffer
from guard_agent.client import GuardAgentHandler, SyncGuardAgentHandler, guard_agent
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

__all__ = [
    "guard_agent",
    "GuardAgentHandler",
    "SyncGuardAgentHandler",
    "AgentConfig",
    "SecurityEvent",
    "SecurityMetric",
    "DynamicRules",
    "AgentStatus",
    "EventBatch",
    "EventBuffer",
    "HTTPTransport",
    "AgentHandlerProtocol",
    "TransportProtocol",
    "BufferProtocol",
    "RedisHandlerProtocol",
    "generate_batch_id",
    "get_current_timestamp",
    "hash_ip",
    "sanitize_headers",
    "truncate_payload",
    "validate_config",
    "setup_agent_logging",
    "RateLimiter",
    "CircuitBreaker",
    "__version__",
]
