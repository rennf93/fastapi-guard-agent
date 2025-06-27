from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from guard_agent.models import (
    AgentConfig,
    AgentStatus,
    DynamicRules,
    EventBatch,
    SecurityEvent,
    SecurityMetric,
)


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_valid_config(self) -> None:
        """Test creating a valid agent configuration."""
        config = AgentConfig(
            api_key="test-key",
            endpoint="https://api.example.com",
            project_id="test-project",
        )

        assert config.api_key == "test-key"
        assert config.endpoint == "https://api.example.com"
        assert config.project_id == "test-project"
        assert config.buffer_size == 100  # default
        assert config.flush_interval == 30  # default

    def test_invalid_config_missing_api_key(self) -> None:
        """Test that missing API key raises validation error."""
        with pytest.raises(ValidationError):
            AgentConfig()

    def test_config_defaults(self) -> None:
        """Test that default values are set correctly."""
        config = AgentConfig(api_key="test")

        assert config.endpoint == "https://api.fastapi-guard.com"
        assert config.buffer_size == 100
        assert config.flush_interval == 30
        assert config.enable_metrics is True
        assert config.enable_events is True

    def test_invalid_endpoint_empty(self) -> None:
        """Test that empty endpoint raises validation error."""
        with pytest.raises(ValidationError, match="Endpoint URL cannot be empty"):
            AgentConfig(api_key="test", endpoint="")

    def test_invalid_endpoint_no_scheme(self) -> None:
        """Test that endpoint without scheme raises validation error."""
        with pytest.raises(
            ValidationError, match="Endpoint must be a valid URL with scheme and domain"
        ):
            AgentConfig(api_key="test", endpoint="api.example.com")

    def test_invalid_endpoint_no_domain(self) -> None:
        """Test that endpoint without domain raises validation error."""
        with pytest.raises(
            ValidationError, match="Endpoint must be a valid URL with scheme and domain"
        ):
            AgentConfig(api_key="test", endpoint="https://")

    def test_invalid_endpoint_scheme(self) -> None:
        """Test that endpoint with invalid scheme raises validation error."""
        with pytest.raises(
            ValidationError, match="Endpoint URL must use http or https scheme"
        ):
            AgentConfig(api_key="test", endpoint="ftp://api.example.com")

    def test_valid_endpoint_http(self) -> None:
        """Test that HTTP endpoint is valid."""
        config = AgentConfig(api_key="test", endpoint="http://api.example.com")
        assert config.endpoint == "http://api.example.com"

    def test_valid_endpoint_https(self) -> None:
        """Test that HTTPS endpoint is valid."""
        config = AgentConfig(api_key="test", endpoint="https://api.example.com")
        assert config.endpoint == "https://api.example.com"


class TestSecurityEvent:
    """Tests for SecurityEvent model."""

    def test_valid_event(self) -> None:
        """Test creating a valid security event."""
        timestamp = datetime.now(timezone.utc)
        event = SecurityEvent(
            timestamp=timestamp,
            event_type="ip_banned",
            ip_address="192.168.1.1",
            action_taken="banned",
            reason="threshold_exceeded",
        )

        assert event.timestamp == timestamp
        assert event.event_type == "ip_banned"
        assert event.ip_address == "192.168.1.1"
        assert event.action_taken == "banned"
        assert event.reason == "threshold_exceeded"

    def test_invalid_event_type(self) -> None:
        """Test that invalid event type raises validation error."""
        with pytest.raises(ValidationError):
            SecurityEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="invalid_type",
                ip_address="192.168.1.1",
                action_taken="banned",
                reason="test",
            )


class TestSecurityMetric:
    """Tests for SecurityMetric model."""

    def test_valid_metric(self) -> None:
        """Test creating a valid security metric."""
        timestamp = datetime.now(timezone.utc)
        metric = SecurityMetric(
            timestamp=timestamp,
            metric_type="request_count",
            value=42.0,
            tags={"endpoint": "/api/test"},
        )

        assert metric.timestamp == timestamp
        assert metric.metric_type == "request_count"
        assert metric.value == 42.0
        assert metric.tags == {"endpoint": "/api/test"}

    def test_invalid_metric_type(self) -> None:
        """Test that invalid metric type raises validation error."""
        with pytest.raises(ValidationError):
            SecurityMetric(
                timestamp=datetime.now(timezone.utc),
                metric_type="invalid_metric",
                value=1.0,
            )


class TestDynamicRules:
    """Tests for DynamicRules model."""

    def test_valid_rules(self) -> None:
        """Test creating valid dynamic rules."""
        rules = DynamicRules(
            ip_blacklist=["192.168.1.1", "10.0.0.1"],
            ip_whitelist=["127.0.0.1"],
            blocked_countries=["XX"],
            whitelist_countries=["US"],
            global_rate_limit=100,
            ttl=300,
        )

        assert "192.168.1.1" in rules.ip_blacklist
        assert "127.0.0.1" in rules.ip_whitelist
        assert "XX" in rules.blocked_countries
        assert "US" in rules.whitelist_countries
        assert rules.global_rate_limit == 100
        assert rules.ttl == 300

    def test_default_rules(self) -> None:
        """Test default values for dynamic rules."""
        rules = DynamicRules()

        assert rules.ip_blacklist == []
        assert rules.ip_whitelist == []
        assert rules.blocked_countries == []
        assert rules.whitelist_countries == []
        assert rules.endpoint_rate_limits == {}
        assert rules.ttl == 300
        assert rules.rule_id == "default-rule"
        assert rules.version == 1


class TestAgentStatus:
    """Tests for AgentStatus model."""

    def test_valid_status(self) -> None:
        """Test creating a valid agent status."""
        timestamp = datetime.now(timezone.utc)
        status = AgentStatus(
            timestamp=timestamp,
            status="healthy",
            uptime=3600.0,
            events_sent=100,
            events_failed=5,
            buffer_size=10,
        )

        assert status.timestamp == timestamp
        assert status.status == "healthy"
        assert status.uptime == 3600.0
        assert status.events_sent == 100
        assert status.events_failed == 5
        assert status.buffer_size == 10


class TestEventBatch:
    """Tests for EventBatch model."""

    def test_valid_batch(self) -> None:
        """Test creating a valid event batch."""
        timestamp = datetime.now(timezone.utc)
        events = [
            SecurityEvent(
                timestamp=timestamp,
                event_type="ip_banned",
                ip_address="192.168.1.1",
                action_taken="banned",
                reason="test",
            )
        ]

        batch = EventBatch(
            project_id="test-project",
            events=events,
            batch_id="test-batch-123",
            created_at=timestamp,
        )

        assert batch.project_id == "test-project"
        assert len(batch.events) == 1
        assert batch.batch_id == "test-batch-123"
        assert batch.created_at == timestamp
