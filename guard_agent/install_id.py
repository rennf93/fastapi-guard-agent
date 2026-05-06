from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)

__all__ = ["resolve_install_id"]


def _read_install_id(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        logger.exception("install_id.read_failed path=%s", path)
        return None


def _write_install_id(path: Path, install_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(install_id, encoding="utf-8")
    except OSError:
        logger.exception("install_id.write_failed path=%s", path)


def resolve_install_id(
    *, state_path: Path | None = None, override: str | None = None
) -> str:
    if override:
        return override
    if state_path is None:
        state_path = Path.home() / ".guard-agent" / "install-id"
    existing = _read_install_id(state_path)
    if existing:
        return existing
    new_id = str(uuid4())
    _write_install_id(state_path, new_id)
    return new_id
