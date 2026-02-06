"""
Rate limiter for API calls with exponential backoff

Provides protection against API abuse, respects rate limits, and implements
exponential backoff for retries. Essential for compliance with API quotas
and cost control.

Security features:
- Configurable rate limits per minute/hour
- Exponential backoff on failures
- Thread-safe implementation
- Audit trail logging
"""

from __future__ import annotations

import time
import threading
from typing import Optional, Callable, TypeVar, ParamSpec
from datetime import datetime, timedelta
from collections import deque
import hashlib
import json

# Type variables for generic callable typing
P = ParamSpec("P")
T = TypeVar("T")

# TypeAlias for internal tracking
FailureCount = int
RequestTimestamp = datetime


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded after all retries."""

    def __init__(self, message: str, attempts: int = 0) -> None:
        super().__init__(message)
        self.attempts = attempts


class RateLimiter:
    """
    Thread-safe rate limiter with exponential backoff

    Implements token bucket algorithm with sliding window for rate limiting
    and exponential backoff for retry logic.
    """

    def __init__(
        self,
        requests_per_minute: int = 10,
        requests_per_hour: int = 500,
        max_retries: int = 3,
        initial_backoff: float = 1.0,
        max_backoff: float = 32.0,
        backoff_multiplier: float = 2.0
    ) -> None:
        """
        Initialize rate limiter

        Args:
            requests_per_minute: Maximum requests allowed per minute
            requests_per_hour: Maximum requests allowed per hour
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff time in seconds
            max_backoff: Maximum backoff time in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier

        # Thread safety
        self.lock = threading.Lock()

        # Request tracking (sliding window)
        self.minute_requests: deque[RequestTimestamp] = deque()
        self.hour_requests: deque[RequestTimestamp] = deque()

        # Failure tracking for backoff
        self.failure_counts: dict[str, FailureCount] = {}
        self.last_failure_time: dict[str, RequestTimestamp] = {}

    def _cleanup_old_requests(self) -> None:
        """Remove expired requests from tracking queues"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        # Clean minute window
        while self.minute_requests and self.minute_requests[0] < minute_ago:
            self.minute_requests.popleft()

        # Clean hour window
        while self.hour_requests and self.hour_requests[0] < hour_ago:
            self.hour_requests.popleft()

    def _get_request_id(
        self,
        func: Callable[..., object],
        args: tuple[object, ...],
        kwargs: dict[str, object]
    ) -> str:
        """Generate unique ID for request based on function and arguments"""
        # Create hash of function name and arguments for tracking
        func_name: str = func.__name__ if hasattr(func, '__name__') else str(func)
        data: dict[str, str] = {
            'func': func_name,
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def _calculate_backoff(self, request_id: str) -> float:
        """Calculate exponential backoff time based on failure count"""
        failure_count = self.failure_counts.get(request_id, 0)
        if failure_count == 0:
            return 0

        backoff = min(
            self.initial_backoff * (self.backoff_multiplier ** (failure_count - 1)),
            self.max_backoff
        )
        return backoff

    def wait_if_needed(self) -> float:
        """
        Check rate limits and wait if necessary

        Returns:
            Time waited in seconds
        """
        with self.lock:
            self._cleanup_old_requests()

            now = datetime.now()
            wait_time = 0.0

            # Check minute limit
            if len(self.minute_requests) >= self.requests_per_minute:
                # Calculate wait time until oldest request expires
                oldest = self.minute_requests[0]
                wait_until = oldest + timedelta(minutes=1)
                if wait_until > now:
                    wait_time = max(wait_time, (wait_until - now).total_seconds())

            # Check hour limit
            if len(self.hour_requests) >= self.requests_per_hour:
                oldest = self.hour_requests[0]
                wait_until = oldest + timedelta(hours=1)
                if wait_until > now:
                    wait_time = max(wait_time, (wait_until - now).total_seconds())

            # Wait if necessary
            if wait_time > 0:
                print(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)

            # Record this request
            now = datetime.now()
            self.minute_requests.append(now)
            self.hour_requests.append(now)

            return wait_time

    def execute_with_backoff(
        self,
        func: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs
    ) -> T:
        """
        Execute function with rate limiting and exponential backoff

        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Result from function execution

        Raises:
            RateLimitError: If all retries are exhausted
        """
        # Cast args/kwargs to tuple/dict for request ID generation
        args_tuple: tuple[object, ...] = tuple(args) if args else ()
        kwargs_dict: dict[str, object] = dict(kwargs) if kwargs else {}
        request_id = self._get_request_id(func, args_tuple, kwargs_dict)

        for attempt in range(self.max_retries):
            # Wait for rate limit
            self.wait_if_needed()

            # Calculate and apply backoff if this is a retry
            if attempt > 0:
                backoff = self._calculate_backoff(request_id)
                if backoff > 0:
                    print(f"Retry {attempt}/{self.max_retries} after {backoff:.1f}s backoff...")
                    time.sleep(backoff)

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Success - reset failure count
                with self.lock:
                    if request_id in self.failure_counts:
                        del self.failure_counts[request_id]
                    if request_id in self.last_failure_time:
                        del self.last_failure_time[request_id]

                return result

            except Exception as e:
                # Track failure
                with self.lock:
                    self.failure_counts[request_id] = self.failure_counts.get(request_id, 0) + 1
                    self.last_failure_time[request_id] = datetime.now()

                # Sanitize error message to prevent information leakage
                error_str = str(e).lower()
                if any(sensitive in error_str for sensitive in ['api', 'key', 'token', 'secret', 'password']):
                    safe_error = "Authentication or authorization error"
                elif 'rate' in error_str and 'limit' in error_str:
                    safe_error = "Rate limit exceeded"
                else:
                    safe_error = "API request failed"

                # If this was the last attempt, raise
                if attempt == self.max_retries - 1:
                    raise RateLimitError(
                        f"{safe_error} after {self.max_retries} attempts",
                        attempts=self.max_retries
                    ) from e

                print(f"Request failed: {safe_error}. Retrying...")

        # Should never reach here, but required for type checker
        raise RateLimitError(f"Failed after {self.max_retries} attempts", attempts=self.max_retries)


# Global singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    requests_per_minute: int = 10,
    requests_per_hour: int = 500
) -> RateLimiter:
    """
    Get or create the global rate limiter instance

    Args:
        requests_per_minute: Max requests per minute (only used on first call)
        requests_per_hour: Max requests per hour (only used on first call)

    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour
        )
    return _rate_limiter