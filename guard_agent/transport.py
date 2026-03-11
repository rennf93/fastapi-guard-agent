import asyncio
import logging
from typing import Any

import httpx

from guard_agent.encryption import EncryptionError, PayloadEncryptor, create_encryptor
from guard_agent.models import (
    AgentConfig,
    AgentStatus,
    DynamicRules,
    EventBatch,
    SecurityEvent,
    SecurityMetric,
)
from guard_agent.protocols import TransportProtocol
from guard_agent.utils import (
    CircuitBreaker,
    RateLimiter,
    calculate_backoff_delay,
    generate_batch_id,
    get_current_timestamp,
    safe_json_serialize,
)


class HTTPTransport(TransportProtocol):
    """
    HTTP transport layer for communicating with FastAPI Guard SaaS platform.
    Includes retry logic, circuit breaker, and rate limiting.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

        self._client: httpx.AsyncClient | None = None

        self._encryptor: PayloadEncryptor | None = None
        self._encryption_enabled = False
        self._init_encryption()

        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5, recovery_timeout=60.0
        )
        self.rate_limiter = RateLimiter(
            max_calls=100,
            time_window=60.0,
        )

        self.requests_sent = 0
        self.requests_failed = 0
        self.bytes_sent = 0

    def _init_encryption(self) -> None:
        """Initialize encryption if configured."""
        if not self.config.project_encryption_key:
            self.logger.info("Encryption not configured - using unencrypted transport")
            return

        try:
            self._encryptor = create_encryptor(self.config.project_encryption_key)
            if self._encryptor and self._encryptor.verify_key():
                self._encryption_enabled = True
                self.logger.info("Encryption enabled - using encrypted endpoint")
            else:
                self.logger.warning(
                    "Invalid encryption key - falling back to unencrypted"
                )
        except EncryptionError as e:
            self.logger.warning(
                f"Encryption setup failed: {e} - using unencrypted transport"
            )
            self._encryption_enabled = False

    async def initialize(self) -> None:
        """Initialize HTTP client."""
        if self._client and not self._client.is_closed:
            return

        try:
            headers = {
                "User-Agent": "FastAPI-Guard-Agent/1.1.0",
                "Content-Type": "application/json",
                "X-API-Key": self.config.api_key,
            }

            if self.config.project_id:
                headers["X-Project-ID"] = self.config.project_id

            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(
                    timeout=self.config.timeout,
                    connect=10.0,
                    read=self.config.timeout,
                ),
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                    keepalive_expiry=30.0,
                ),
                follow_redirects=False,
            )

            self.logger.info("HTTP transport initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize HTTP transport: {str(e)}")
            raise

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def send_events(self, events: list[SecurityEvent]) -> bool:
        """Send security events to the SaaS platform."""
        if not events:
            return True

        try:
            batch = EventBatch(
                project_id=self.config.project_id or "default",
                events=events,
                batch_id=generate_batch_id(),
                created_at=get_current_timestamp(),
                agent_version="1.1.0",
            )

            return await self._send_with_retry(
                "/api/v1/events", batch.model_dump(), "events"
            )

        except Exception as e:
            self.logger.error(f"Failed to send events: {str(e)}")
            self.requests_failed += 1
            return False

    async def send_metrics(self, metrics: list[SecurityMetric]) -> bool:
        """Send metrics to the SaaS platform."""
        if not metrics:
            return True

        try:
            batch = EventBatch(
                project_id=self.config.project_id or "default",
                metrics=metrics,
                batch_id=generate_batch_id(),
                created_at=get_current_timestamp(),
                agent_version="1.1.0",
            )

            return await self._send_with_retry(
                "/api/v1/metrics", batch.model_dump(), "metrics"
            )

        except Exception as e:
            self.logger.error(f"Failed to send metrics: {str(e)}")
            self.requests_failed += 1
            return False

    async def fetch_dynamic_rules(self) -> DynamicRules | None:
        """Fetch dynamic rules from the SaaS platform."""
        try:
            response_data = await self._get_with_retry("/api/v1/rules")

            if response_data:
                return DynamicRules(**response_data)

            return None

        except Exception as e:
            self.logger.error(f"Failed to fetch dynamic rules: {str(e)}")
            return None

    async def send_status(self, status: AgentStatus) -> bool:
        """Send agent status/health information."""
        try:
            return await self._send_with_retry(
                "/api/v1/status", status.model_dump(), "status"
            )

        except Exception as e:
            self.logger.error(f"Failed to send status: {str(e)}")
            return False

    async def _send_with_retry(
        self, endpoint: str, data: dict[str, Any], data_type: str
    ) -> bool:
        """Send data with retry logic and circuit breaker."""
        for attempt in range(self.config.retry_attempts + 1):
            try:
                if not await self.rate_limiter.acquire():
                    retry_after = self.rate_limiter.get_retry_after()
                    self.logger.warning(
                        f"Rate limit exceeded, waiting {retry_after:.1f}s"
                    )
                    await asyncio.sleep(retry_after)
                    continue

                success = await self.circuit_breaker.call(
                    self._make_request, "POST", endpoint, data
                )

                if success:
                    self.requests_sent += 1
                    self.logger.debug(f"Successfully sent {data_type} batch")
                    return True
                else:
                    self.requests_failed += 1

            except Exception as e:
                self.logger.warning(
                    f"Attempt {attempt + 1} failed for {data_type}: {str(e)}"
                )

                if attempt < self.config.retry_attempts:
                    delay = calculate_backoff_delay(attempt, self.config.backoff_factor)
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"All retry attempts failed for {data_type}")
                    self.requests_failed += 1

        return False

    async def _get_with_retry(self, endpoint: str) -> dict[str, Any] | None:
        """GET request with retry logic and circuit breaker."""
        for attempt in range(self.config.retry_attempts + 1):
            try:
                if not await self.rate_limiter.acquire():
                    retry_after = self.rate_limiter.get_retry_after()
                    await asyncio.sleep(retry_after)
                    continue

                response_data = await self.circuit_breaker.call(
                    self._make_request, "GET", endpoint, None
                )

                if isinstance(response_data, dict):
                    self.requests_sent += 1
                    return response_data
                else:
                    self.requests_failed += 1

            except Exception as e:
                self.logger.warning(
                    f"GET attempt {attempt + 1} failed for {endpoint}: {str(e)}"
                )

                if attempt < self.config.retry_attempts:
                    delay = calculate_backoff_delay(attempt, self.config.backoff_factor)
                    await asyncio.sleep(delay)
                else:
                    self.requests_failed += 1

        return None

    async def _make_request(
        self, method: str, endpoint: str, data: dict[str, Any] | None
    ) -> dict[str, Any] | bool:
        """Make HTTP request with proper error handling and optional encryption."""
        if not self._client:
            await self.initialize()

        if not self._client:
            raise Exception("Failed to initialize HTTP client")

        url = f"{self.config.endpoint.rstrip('/')}{endpoint}"

        try:
            if method == "POST" and data:
                if self._encryption_enabled and endpoint in [
                    "/api/v1/events",
                    "/api/v1/metrics",
                ]:
                    if not self._encryptor:
                        raise EncryptionError("Encryptor not initialized")

                    payload_to_encrypt = {
                        "events": [
                            event.model_dump(mode="json")
                            if hasattr(event, "model_dump")
                            else event
                            for event in data.get("events", [])
                        ],
                        "metrics": [
                            metric.model_dump(mode="json")
                            if hasattr(metric, "model_dump")
                            else metric
                            for metric in data.get("metrics", [])
                        ],
                    }

                    encrypted_payload = self._encryptor.encrypt(payload_to_encrypt)

                    encrypted_data = {
                        "encrypted_payload": encrypted_payload,
                        "batch_id": data.get("batch_id"),
                        "agent_version": "1.1.0",
                    }

                    encrypted_url = (
                        f"{self.config.endpoint.rstrip('/')}/api/v1/events/encrypted"
                    )

                    json_data = await safe_json_serialize(encrypted_data)
                    self.bytes_sent += len(json_data.encode("utf-8"))

                    response = await self._client.post(encrypted_url, content=json_data)
                    return await self._handle_response(response)
                else:
                    json_data = await safe_json_serialize(data)
                    self.bytes_sent += len(json_data.encode("utf-8"))

                    response = await self._client.post(url, content=json_data)
                    return await self._handle_response(response)

            elif method == "GET":
                response = await self._client.get(url)
                return await self._handle_response(response)

            else:
                raise ValueError(f"Unsupported method: {method}")

        except EncryptionError as e:
            self.logger.error(f"Encryption error for {method} {url}: {str(e)}")
            raise
        except httpx.HTTPError as e:
            self.logger.error(f"HTTP client error for {method} {url}: {str(e)}")
            raise
        except asyncio.TimeoutError as e:
            self.logger.error(f"Timeout error for {method} {url}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error for {method} {url}: {str(e)}")
            raise

    async def _handle_response(self, response: httpx.Response) -> dict[str, Any] | bool:
        """Handle HTTP response with proper error checking."""
        self.logger.debug(f"Response: {response.status_code} for {response.url}")

        if response.status_code == 200:
            try:
                json_data = response.json()
                if isinstance(json_data, dict):
                    return json_data
                else:
                    return True
            except Exception:
                return True

        elif response.status_code == 201:
            return True

        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            raise Exception(f"Rate limited by server, retry after {retry_after}s")

        elif response.status_code in [401, 403]:
            raise Exception(f"Authentication failed: {response.status_code}")

        elif response.status_code >= 500:
            error_text = response.text
            raise Exception(f"Server error {response.status_code}: {error_text}")

        else:
            error_text = response.text
            self.logger.error(f"Client error {response.status_code}: {error_text}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get transport statistics."""
        return {
            "requests_sent": self.requests_sent,
            "requests_failed": self.requests_failed,
            "bytes_sent": self.bytes_sent,
            "circuit_breaker_state": self.circuit_breaker.state,
            "failure_count": self.circuit_breaker.failure_count,
            "session_closed": self._client.is_closed if self._client else True,
        }
