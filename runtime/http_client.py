"""
HTTP Client with retry, timeout, logging, and keep-alive session.

Usage:
    from runtime.http_client import HTTPClient

    client = HTTPClient(timeout=30, max_retries=5)
    data = client.get("https://api.example.com/status")
    result = client.post("https://api.example.com/order", json={...}, headers={...})

All public methods return parsed response data (.json() or .text()) — never raw
Response objects.  On failure after exhausting retries an HTTPClientError is raised.
"""
import logging
import random
import time
from typing import Any, Dict, Optional, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("FunPayHUB.HTTPClient")

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_TIMEOUT = 30
_DEFAULT_MAX_RETRIES = 5
_DEFAULT_BACKOFF = 2  # base multiplier for delay = base_backoff^(attempt-1)
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class HTTPClientError(Exception):
    """Raised when all retry attempts have been exhausted."""
    def __init__(self, method: str, url: str, status_code: Optional[int],
                 attempts: int, last_error: str, body: Optional[str] = None):
        self.method = method
        self.url = url
        self.status_code = status_code
        self.attempts = attempts
        self.last_error = last_error
        self.body = body
        super().__init__(self._format())

    def _format(self) -> str:
        parts = [
            f"HTTP failed after {self.attempts} attempt(s)",
            f"[{self.method}] {self.url}",
        ]
        if self.status_code:
            parts.append(f"last HTTP {self.status_code}")
        if self.last_error:
            parts.append(f"{self.last_error}")
        if self.body:
            parts.append(f"body={self.body[:200]}")
        return " — ".join(parts)


# ---------------------------------------------------------------------------
# HTTPClient
# ---------------------------------------------------------------------------

class HTTPClient:
    """
    A requests-based HTTP client with automatic retry, exponential backoff,
    structured logging, and a keep-alive session.

    Typical usage:

        client = HTTPClient(timeout=30, max_retries=5)
        try:
            result = client.get("https://api.example.com/v1/status")
            # result is already parsed JSON dict or raw text
        except HTTPClientError as exc:
            logger.error("Request failed: %s", exc)
    """

    def __init__(
        self,
        timeout: int = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        base_backoff: float = _DEFAULT_BACKOFF,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_backoff = base_backoff

        # Keep-alive session with re-use and connection pooling
        self._session = requests.Session()

        # Mount adapters with urllib3 Retry for connection-level retries
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=base_backoff,
            status_forcelist=sorted(_RETRYABLE_STATUSES),
            allowed_methods={"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"},
            raise_on_status=False,  # we handle it ourselves
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=20, pool_maxsize=40)
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)

        if default_headers:
            self._session.headers.update(default_headers)

    # ------------------------------------------------------------------
    # Public convenience methods — return parsed data
    # ------------------------------------------------------------------

    def get(self, url: str, **kwargs) -> Any:
        """GET request. Returns parsed JSON dict/list, or raw text on failure to parse."""
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> Any:
        """POST request. Returns parsed JSON dict/list, or raw text on failure to parse."""
        return self._request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> Any:
        """PUT request. Returns parsed JSON dict/list, or raw text on failure to parse."""
        return self._request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs) -> Any:
        """DELETE request. Returns parsed JSON dict/list, or raw text on failure to parse."""
        return self._request("DELETE", url, **kwargs)

    # ------------------------------------------------------------------
    # Core request method
    # ------------------------------------------------------------------

    def _request(self, method: str, url: str, **kwargs) -> Any:
        """
        Core request method with logging, retry, and error handling.

        The urllib3 Retry adapter handles connection-level retries transparently.
        We add application-level retry for HTTP status codes that bypassed the
        adapter (e.g. 429 on a non-idempotent method or 5xx that still raised).
        """
        timeout = kwargs.pop("timeout", self.timeout)
        headers = kwargs.pop("headers", {})

        # Merge per-request headers into session headers
        merged_headers = dict(self._session.headers)
        merged_headers.update(headers)

        logger.info("→ %s %s  timeout=%s", method, url, timeout)
        if logger.isEnabledFor(logging.DEBUG):
            safe_kwargs = {k: v for k, v in kwargs.items() if k != "data" or len(str(v)) < 500}
            logger.debug("Headers: %s  Args: %s", merged_headers, safe_kwargs)

        last_error: Optional[str] = None
        last_status: Optional[int] = None
        last_body: Optional[str] = None

        # We manage retries manually so we can log each attempt clearly
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._session.request(
                    method=method,
                    url=url,
                    timeout=timeout,
                    headers=merged_headers,
                    **kwargs,
                )
                last_status = resp.status_code
                last_body = resp.text[:500] if resp.text else None

                logger.info(
                    "← %s %s → HTTP %d (attempt %d/%d) in %.1fs",
                    method, url, resp.status_code,
                    attempt, self.max_retries,
                    resp.elapsed.total_seconds(),
                )

                # Success
                if resp.ok:
                    return self._parse_response(resp)

                # Retryable status
                if resp.status_code in _RETRYABLE_STATUSES:
                    if attempt < self.max_retries:
                        self._sleep(method, url, attempt, resp.status_code)
                    else:
                        last_error = f"HTTP {resp.status_code}"
                    continue

                # Non-retryable error (4xx except 429)
                raise HTTPClientError(
                    method=method,
                    url=url,
                    status_code=resp.status_code,
                    attempts=attempt,
                    last_error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    body=resp.text[:500],
                )

            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = f"{exc.__class__.__name__}: {exc}"
                logger.error("✕ %s %s attempt %d/%d — %s", method, url, attempt, self.max_retries, last_error)
                if attempt < self.max_retries:
                    self._sleep(method, url, attempt, status_code=None)
                continue

            except HTTPClientError:
                raise  # re-raise our own exceptions immediately

            except Exception as exc:
                last_error = f"{exc.__class__.__name__}: {exc}"
                logger.error("✕ %s %s attempt %d/%d — %s", method, url, attempt, self.max_retries, last_error)
                if attempt < self.max_retries:
                    self._sleep(method, url, attempt, status_code=None)
                continue

        # All attempts exhausted
        raise HTTPClientError(
            method=method,
            url=url,
            status_code=last_status,
            attempts=self.max_retries,
            last_error=last_error or "unknown",
            body=last_body,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(resp: requests.Response) -> Any:
        """Try to parse as JSON; fall back to .text."""
        ct = (resp.headers.get("Content-Type") or "").lower()
        if "application/json" in ct or "text/json" in ct:
            try:
                return resp.json()
            except Exception:
                pass
        # Try json anyway for APIs that don't set Content-Type
        try:
            return resp.json()
        except Exception:
            return resp.text

    def _sleep(self, method: str, url: str, attempt: int, status_code: Optional[int]):
        """Exponential backoff: delay = base_backoff^(attempt-1) with jitter."""
        delay = self.base_backoff ** (attempt - 1)
        jitter = random.uniform(0, delay * 0.25)
        total = delay + jitter
        ctx = f"HTTP {status_code}" if status_code else "connection error"
        logger.debug(
            "Retry %s %s attempt %d — %s — sleeping %.1fs",
            method, url, attempt, ctx, total,
        )
        time.sleep(total)

    def close(self):
        """Close the underlying session."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
