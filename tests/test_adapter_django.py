"""Integration smoke tests for the Django adapter (djapi-guard).

Verifies guard-agent integrates correctly with ``djangoapi_guard`` when
``SecurityConfig.enable_agent=True``. Scope matches the fastapi/flask adapter
tests: config roundtrip + request roundtrip, not agent wire behavior.

Django requires settings to be configured before any ORM-touching import.
We bootstrap a minimal in-memory settings module inline so this test file
is self-contained and independent of any project-level Django setup.

In sync contexts (Flask, Django) guard_core invokes async agent methods
without an event loop, producing RuntimeWarnings. Filtered here as harmless
for these integration smoke tests.
"""

from __future__ import annotations

import warnings

import django
import pytest
from django.conf import settings

pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine .* was never awaited:RuntimeWarning"
)


def setup_module(_module: object) -> None:
    warnings.filterwarnings(
        "ignore",
        message="coroutine .* was never awaited",
        category=RuntimeWarning,
    )


if not settings.configured:
    settings.configure(
        DEBUG=False,
        SECRET_KEY="test-secret-key-0123456789abcdef",
        ALLOWED_HOSTS=["*"],
        ROOT_URLCONF=__name__,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
        ],
        MIDDLEWARE=[
            "djangoapi_guard.middleware.DjangoAPIGuard",
        ],
    )
    django.setup()

from django.http import HttpRequest, JsonResponse  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import path  # noqa: E402
from guard_core.models import SecurityConfig  # noqa: E402

from guard_agent.models import AgentConfig  # noqa: E402

API_KEY = "test-api-key-1234567890"
PROJECT_ID = "test-project"

settings.GUARD_SECURITY_CONFIG = SecurityConfig(  # type: ignore[misc]
    enable_agent=True,
    agent_api_key=API_KEY,
    agent_project_id=PROJECT_ID,
    passive_mode=True,
    exclude_paths=["/"],
)


def _view(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"ok": True})


urlpatterns = [path("", _view)]


class TestDjangoAdapterIntegration:
    """Agent wiring via djapi-guard (Django adapter)."""

    def test_security_config_produces_agent_config(self) -> None:
        """`SecurityConfig.to_agent_config()` returns a valid `AgentConfig`."""
        config = SecurityConfig(
            enable_agent=True,
            agent_api_key=API_KEY,
            agent_project_id=PROJECT_ID,
        )

        agent_config = config.to_agent_config()

        assert agent_config is not None
        assert isinstance(agent_config, AgentConfig)
        assert agent_config.api_key == API_KEY
        assert agent_config.project_id == PROJECT_ID

    def test_app_with_agent_enabled_serves_requests(self) -> None:
        """Middleware attaches cleanly and requests flow through."""
        client = Client()

        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"ok": True}
