from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

__all__ = ["resolve_install_id"]


def resolve_install_id(
    *, state_path: Path | None = None, override: str | None = None
) -> str:
    if override:
        return override
    if state_path is None:
        state_path = Path.home() / ".guard-agent" / "install-id"
    if state_path.exists():
        try:
            return state_path.read_text(encoding="utf-8").strip()
        except OSError:
            logger.exception("install_id.read_failed path=%s", state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    new_id = str(uuid4())
    try:
        state_path.write_text(new_id, encoding="utf-8")
    except OSError:
        logger.exception("install_id.write_failed path=%s", state_path)
    return new_id
