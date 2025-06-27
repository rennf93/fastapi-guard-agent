import asyncio
import logging
from typing import Any

import aiohttp

from guard_agent.models import AgentConfig, AgentStatus, DynamicRules, EventBatch, SecurityEvent, SecurityMetric
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

        # HTTP session management
        self._session: aiohttp.ClientSession | None = None
        self._connector: aiohttp.TCPConnector | None = None

        # Reliability features
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0
        )
        self.rate_limiter = RateLimiter(
            max_calls=100,  # 100 calls per minute
            time_window=60.0
        )

        # Statistics
        self.requests_sent = 0
        self.requests_failed = 0
        self.bytes_sent = 0

    async def initialize(self) -> None:
        """Initialize HTTP session and connector."""
        if self._session and not self._session.closed:
            return

        try:
            # Create connector with connection pooling
            self._connector = aiohttp.TCPConnector(
                limit=10,  # Total connection pool size
                limit_per_host=5,  # Connections per host
                ttl_dns_cache=300,  # DNS cache TTL
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )

            # Create session with timeouts
            timeout = aiohttp.ClientTimeout(
                total=self.config.timeout,
                connect=10,
                sock_read=self.config.timeout,
            )

            # Setup headers
            headers = {
                "User-Agent": "FastAPI-Guard-Agent/0.0.1",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            }

            if self.config.project_id:
                headers["X-Project-ID"] = self.config.project_id

            self._session = aiohttp.ClientSession(
                connector=self._connector,
                timeout=timeout,
                headers=headers,
                raise_for_status=False,  # Handle status codes manually
            )

            self.logger.info("HTTP transport initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize HTTP transport: {str(e)}")
            raise

    async def close(self) -> None:
        """Close HTTP session and connector."""
        if self._session and not self._session.closed:
            await self._session.close()

        if self._connector:
            await self._connector.close()

    async def send_events(self, events: list[SecurityEvent]) -> bool:
        """Send security events to the SaaS platform."""
        if not events:
            return True

        try:
            # Create event batch
            batch = EventBatch(
                project_id=self.config.project_id or "default",
                events=events,
                batch_id=generate_batch_id(),
                created_at=get_current_timestamp(),
            )

            # Send with reliability features
            return await self._send_with_retry(
                "/api/v1/events",
                batch.model_dump(),
                "events"
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
            # Create metric batch
            batch = EventBatch(
                project_id=self.config.project_id or "default",
                metrics=metrics,
                batch_id=generate_batch_id(),
                created_at=get_current_timestamp(),
            )

            # Send with reliability features
            return await self._send_with_retry(
                "/api/v1/metrics",
                batch.model_dump(),
                "metrics"
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
                "/api/v1/status",
                status.model_dump(),
                "status"
            )

        except Exception as e:
            self.logger.error(f"Failed to send status: {str(e)}")
            return False

    async def _send_with_retry(self, endpoint: str, data: dict[str, Any], data_type: str) -> bool:
        """Send data with retry logic and circuit breaker."""
        for attempt in range(self.config.retry_attempts + 1):
            try:
                # Check rate limit
                if not await self.rate_limiter.acquire():
                    retry_after = self.rate_limiter.get_retry_after()
                    self.logger.warning(f"Rate limit exceeded, waiting {retry_after:.1f}s")
                    await asyncio.sleep(retry_after)
                    continue

                # Send via circuit breaker
                success = await self.circuit_breaker.call(
                    self._make_request,
                    "POST",
                    endpoint,
                    data
                )

                if success:
                    self.requests_sent += 1
                    self.logger.debug(f"Successfully sent {data_type} batch")
                    return True
                else:
                    self.requests_failed += 1

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {data_type}: {str(e)}")

                if attempt < self.config.retry_attempts:
                    delay = calculate_backoff_delay(
                        attempt,
                        self.config.backoff_factor
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"All retry attempts failed for {data_type}")
                    self.requests_failed += 1

        return False

    async def _get_with_retry(self, endpoint: str) -> dict[str, Any] | None:
        """GET request with retry logic and circuit breaker."""
        for attempt in range(self.config.retry_attempts + 1):
            try:
                # Check rate limit
                if not await self.rate_limiter.acquire():
                    retry_after = self.rate_limiter.get_retry_after()
                    await asyncio.sleep(retry_after)
                    continue

                # Request via circuit breaker
                response_data = await self.circuit_breaker.call(
                    self._make_request,
                    "GET",
                    endpoint,
                    None
                )

                if response_data:
                    self.requests_sent += 1
                    return response_data
                else:
                    self.requests_failed += 1

            except Exception as e:
                self.logger.warning(f"GET attempt {attempt + 1} failed for {endpoint}: {str(e)}")

                if attempt < self.config.retry_attempts:
                    delay = calculate_backoff_delay(attempt, self.config.backoff_factor)
                    await asyncio.sleep(delay)
                else:
                    self.requests_failed += 1

        return None

    async def _make_request(self, method: str, endpoint: str, data: dict[str, Any] | None) -> Any:
        """Make HTTP request with proper error handling."""
        if not self._session:
            await self.initialize()

        if not self._session:
            raise Exception("Failed to initialize HTTP session")

        url = f"{self.config.endpoint.rstrip('/')}{endpoint}"

        try:
            if method == "POST" and data:
                # Serialize data
                json_data = await safe_json_serialize(data)
                self.bytes_sent += len(json_data.encode('utf-8'))

                async with self._session.post(url, data=json_data) as response:
                    return await self._handle_response(response)

            elif method == "GET":
                async with self._session.get(url) as response:
                    return await self._handle_response(response)

            else:
                raise ValueError(f"Unsupported method: {method}")

        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error for {method} {url}: {str(e)}")
            raise
        except asyncio.TimeoutError as e:
            self.logger.error(f"Timeout error for {method} {url}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error for {method} {url}: {str(e)}")
            raise

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Any:
        """Handle HTTP response with proper error checking."""
        # Log response
        self.logger.debug(f"Response: {response.status} for {response.url}")

        # Check status codes
        if response.status == 200:
            try:
                return await response.json()
            except Exception:
                return True  # Success for non-JSON responses

        elif response.status == 201:
            return True  # Created successfully

        elif response.status == 429:
            # Rate limited by server
            retry_after = response.headers.get('Retry-After', '60')
            raise Exception(f"Rate limited by server, retry after {retry_after}s")

        elif response.status in [401, 403]:
            # Authentication/authorization error
            raise Exception(f"Authentication failed: {response.status}")

        elif response.status >= 500:
            # Server error - retryable
            error_text = await response.text()
            raise Exception(f"Server error {response.status}: {error_text}")

        else:
            # Client error - likely not retryable
            error_text = await response.text()
            self.logger.error(f"Client error {response.status}: {error_text}")
            return False

    def get_stats(self) -> dict[str, Any]:
        """Get transport statistics."""
        return {
            "requests_sent": self.requests_sent,
            "requests_failed": self.requests_failed,
            "bytes_sent": self.bytes_sent,
            "circuit_breaker_state": self.circuit_breaker.state,
            "failure_count": self.circuit_breaker.failure_count,
            "session_closed": self._session.closed if self._session else True,
        }
