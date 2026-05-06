from __future__ import annotations

import hashlib
import hmac

from guard_agent.signing import sign_payload


def test_sign_payload_returns_v1_prefixed_hex_digest() -> None:
    body = b'{"events": []}'
    secret = "test-secret"
    sig = sign_payload(body, secret=secret)
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert sig == f"v1={expected}"


def test_sign_payload_returns_none_when_no_secret() -> None:
    assert sign_payload(b"{}", secret=None) is None


def test_sign_payload_returns_none_when_empty_secret() -> None:
    assert sign_payload(b"{}", secret="") is None


def test_sign_payload_changes_with_body() -> None:
    secret = "test-secret"
    sig_a = sign_payload(b'{"a": 1}', secret=secret)
    sig_b = sign_payload(b'{"a": 2}', secret=secret)
    assert sig_a != sig_b
