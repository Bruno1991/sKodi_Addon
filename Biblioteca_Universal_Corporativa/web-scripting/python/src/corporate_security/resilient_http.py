from __future__ import annotations

import ipaddress
import random
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import Message
from enum import Enum
from typing import Callable, Mapping

from .errors import CorporateError


class BreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0, *, clock: Callable[[], float] = time.monotonic) -> None:
        if failure_threshold < 1 or recovery_timeout <= 0:
            raise ValueError("Circuit breaker thresholds must be positive.")
        self._threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._clock = clock
        self._state = BreakerState.CLOSED
        self._failures = 0
        self._opened_at = 0.0
        self._probe_in_flight = False
        self._lock = threading.Lock()

    @property
    def state(self) -> BreakerState:
        with self._lock:
            return self._state

    def before_call(self) -> None:
        with self._lock:
            if self._state is BreakerState.CLOSED:
                return
            if self._state is BreakerState.OPEN:
                if self._clock() - self._opened_at < self._recovery_timeout:
                    raise CorporateError("circuit_open", "Dependency circuit is open.")
                self._state = BreakerState.HALF_OPEN
                self._probe_in_flight = True
                return
            if self._probe_in_flight:
                raise CorporateError("circuit_open", "Dependency circuit probe is already in progress.")
            self._probe_in_flight = True

    def on_success(self) -> None:
        with self._lock:
            self._state = BreakerState.CLOSED
            self._failures = 0
            self._probe_in_flight = False

    def on_failure(self) -> None:
        with self._lock:
            self._probe_in_flight = False
            self._failures += 1
            if self._state is BreakerState.HALF_OPEN or self._failures >= self._threshold:
                self._state = BreakerState.OPEN
                self._opened_at = self._clock()


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay: float = 0.25
    max_delay: float = 4.0
    max_elapsed: float = 15.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or min(self.base_delay, self.max_delay, self.max_elapsed) <= 0:
            raise ValueError("Retry policy values must be positive.")


@dataclass(frozen=True, slots=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


class ResilientHttpClient:
    RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}
    IDEMPOTENT_METHODS = {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}

    def __init__(self, allowed_hosts: set[str], *, retry_policy: RetryPolicy | None = None, circuit_breaker: CircuitBreaker | None = None, timeout: float = 5.0, max_response_bytes: int = 1_048_576, allow_http: bool = False, sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic, jitter: Callable[[], float] = random.random) -> None:
        if not allowed_hosts or timeout <= 0 or max_response_bytes < 1:
            raise ValueError("Allowed hosts, positive timeout and response limit are required.")
        self._allowed_hosts = {host.lower() for host in allowed_hosts}
        self._policy = retry_policy or RetryPolicy()
        self._breaker = circuit_breaker or CircuitBreaker(clock=clock)
        self._timeout = timeout
        self._max_response_bytes = max_response_bytes
        self._allow_http = allow_http
        self._sleep = sleep
        self._clock = clock
        self._jitter = jitter

    def request(self, method: str, url: str, *, headers: Mapping[str, str] | None = None, body: bytes | None = None, idempotency_key: str | None = None) -> HttpResponse:
        method = method.upper()
        self._validate_url(url)
        if method not in self.IDEMPOTENT_METHODS and not idempotency_key:
            raise CorporateError("non_idempotent_request", "A non-idempotent request requires an idempotency key.")
        request_headers = dict(headers or {})
        if idempotency_key:
            request_headers["Idempotency-Key"] = idempotency_key
        self._breaker.before_call()
        started = self._clock()
        last_error: BaseException | None = None
        for attempt in range(1, self._policy.max_attempts + 1):
            retry_after: float | None = None
            try:
                request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
                with urllib.request.urlopen(request, timeout=self._timeout) as response:
                    result = HttpResponse(response.status, dict(response.headers.items()), self._read_limited(response))
                    self._breaker.on_success()
                    return result
            except urllib.error.HTTPError as error:
                if error.code not in self.RETRYABLE_STATUS:
                    self._breaker.on_success()
                    raise CorporateError("http_error", f"Dependency returned HTTP {error.code}.", cause=error) from error
                last_error = error
                retry_after = self._parse_retry_after(error.headers)
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as error:
                last_error = error
            elapsed = self._clock() - started
            if attempt >= self._policy.max_attempts or elapsed >= self._policy.max_elapsed:
                break
            exponential = min(self._policy.max_delay, self._policy.base_delay * (2 ** (attempt - 1)))
            delay = retry_after if retry_after is not None else exponential * (0.5 + self._jitter())
            if elapsed + delay >= self._policy.max_elapsed:
                break
            self._sleep(delay)
        self._breaker.on_failure()
        raise CorporateError("dependency_unavailable", "Dependency remained unavailable after retries.", cause=last_error)

    def _validate_url(self, url: str) -> None:
        parsed = urllib.parse.urlsplit(url)
        schemes = {"https", "http"} if self._allow_http else {"https"}
        if parsed.scheme not in schemes or not parsed.hostname or parsed.username or parsed.password:
            raise CorporateError("invalid_url", "URL does not satisfy the outbound policy.")
        if parsed.hostname.lower() not in self._allowed_hosts:
            raise CorporateError("host_not_allowed", "Destination host is not allowed.")
        try:
            address = ipaddress.ip_address(parsed.hostname)
            if address.is_private or address.is_loopback or address.is_link_local or address.is_multicast:
                raise CorporateError("host_not_allowed", "Private or special-purpose destination is not allowed.")
        except ValueError:
            pass

    def _read_limited(self, response: object) -> bytes:
        content_length = getattr(response, "headers").get("Content-Length")
        if content_length and int(content_length) > self._max_response_bytes:
            raise CorporateError("response_too_large", "Dependency response exceeds the configured limit.")
        payload = getattr(response, "read")(self._max_response_bytes + 1)
        if len(payload) > self._max_response_bytes:
            raise CorporateError("response_too_large", "Dependency response exceeds the configured limit.")
        return payload

    @staticmethod
    def _parse_retry_after(headers: Message) -> float | None:
        value = headers.get("Retry-After")
        if value is None:
            return None
        try:
            seconds = float(value)
            return seconds if 0 <= seconds <= 60 else None
        except ValueError:
            return None
