class GuardAgentError(Exception):
    """Base exception for all guard-agent errors."""


class BufferFullError(GuardAgentError):
    """Raised when an EventBuffer is full and the configured policy is 'raise'."""
