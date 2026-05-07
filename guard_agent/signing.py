from __future__ import annotations

import hashlib
import hmac

_VERSION_PREFIX = "v1="

__all__ = ["sign_payload"]


def sign_payload(body: bytes, *, secret: str | None) -> str | None:
    if not secret:
        return None
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"{_VERSION_PREFIX}{digest}"
