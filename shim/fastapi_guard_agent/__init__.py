"""
Deprecation shim — the package has been renamed to ``guard-agent``.

The Python import path has always been ``guard_agent``, so code that
does ``from guard_agent import ...`` continues to work without change.
This module exists only so that older code that imported from the
``fastapi_guard_agent`` namespace directly keeps working while emitting
a deprecation warning.
"""

from __future__ import annotations

import warnings as _warnings

_warnings.warn(
    "`fastapi_guard_agent` has been renamed. Import from `guard_agent` instead "
    "(e.g. `from guard_agent import GuardAgentHandler, AgentConfig`). "
    "This alias is provided by the `fastapi-guard-agent` meta-package and "
    "will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

from guard_agent import *  # noqa: E402, F401, F403
from guard_agent import __version__  # noqa: E402, F401
