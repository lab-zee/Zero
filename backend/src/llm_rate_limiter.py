"""
Rate limiter for LLM API calls to prevent hitting rate limits.
Implements token-per-minute (TPM) tracking and request queuing.
"""
import time
import threading
from collections import deque
from typing import Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    tokens_per_minute: int = 30000  # Default OpenAI tier limit
    requests_per_minute: Optional[int] = None  # Optional RPM limit
    retry_after_header: Optional[str] = None  # Header name for retry-after (e.g., 'retry-after')


class LLMRateLimiter:
    """
    Thread-safe rate limiter for LLM API calls.
    Tracks token usage in a rolling window and queues requests when approaching limits.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.lock = threading.Lock()
        
        # Track token usage in rolling 1-minute window
        # Each entry is (timestamp, tokens_used)
        self.token_usage: deque = deque()
        
        # Track request count in rolling 1-minute window
        self.request_times: deque = deque()
        
        # Current estimated token usage (for quick checks)
        self.current_tokens = 0
        
    def _cleanup_old_entries(self):
        """Remove entries older than 1 minute."""
        now = time.time()
        one_minute_ago = now - 60
        
        # Clean up token usage
        while self.token_usage and self.token_usage[0][0] < one_minute_ago:
            _, tokens = self.token_usage.popleft()
            self.current_tokens -= tokens
        
        # Clean up request times
        while self.request_times and self.request_times[0] < one_minute_ago:
            self.request_times.popleft()
    
    def _get_available_tokens(self) -> int:
        """Get available tokens in the current window."""
        self._cleanup_old_entries()
        return max(0, self.config.tokens_per_minute - self.current_tokens)
    
    def _can_make_request(self) -> bool:
        """Check if we can make a request based on RPM limit."""
        if self.config.requests_per_minute is None:
            return True
        
        self._cleanup_old_entries()
        return len(self.request_times) < self.config.requests_per_minute
    
    def wait_if_needed(self, estimated_tokens: int) -> float:
        """
        Wait if necessary to avoid rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for the upcoming request
            
        Returns:
            Time waited in seconds
        """
        with self.lock:
            wait_time = 0.0
            
            # Check token limit
            available = self._get_available_tokens()
            if estimated_tokens > available:
                # Need to wait until enough tokens are available
                if self.token_usage:
                    # Calculate when oldest entry will expire
                    oldest_time = self.token_usage[0][0]
                    time_until_available = (oldest_time + 60) - time.time()
                    if time_until_available > 0:
                        wait_time = max(wait_time, time_until_available)
                else:
                    # No usage history, should be fine
                    pass
            
            # Check request limit
            if not self._can_make_request():
                if self.request_times:
                    oldest_request = self.request_times[0]
                    time_until_available = (oldest_request + 60) - time.time()
                    if time_until_available > 0:
                        wait_time = max(wait_time, time_until_available)
            
            # Wait if needed
            if wait_time > 0:
                # Add small buffer (100ms) to be safe
                wait_time += 0.1
                time.sleep(wait_time)
                # Re-cleanup after waiting
                self._cleanup_old_entries()
            
            return wait_time
    
    def record_usage(self, tokens_used: int):
        """Record token usage for a completed request."""
        with self.lock:
            now = time.time()
            self.token_usage.append((now, tokens_used))
            self.current_tokens += tokens_used
            self.request_times.append(now)
            self._cleanup_old_entries()
    
    def record_rate_limit_error(self, retry_after_seconds: Optional[float] = None):
        """
        Record a rate limit error and adjust timing.
        
        Args:
            retry_after_seconds: Seconds to wait before retrying (from API response)
        """
        if retry_after_seconds:
            # Wait for the specified time
            time.sleep(retry_after_seconds)
        else:
            # Default: wait 1 second
            time.sleep(1.0)


# Global rate limiter instance (shared across all LLM clients)
_rate_limiter: Optional[LLMRateLimiter] = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter() -> LLMRateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        with _rate_limiter_lock:
            if _rate_limiter is None:
                # Default config - can be overridden via environment variables
                import os
                tpm_limit = int(os.getenv("OPENAI_TPM_LIMIT", "30000"))
                rpm_limit = os.getenv("OPENAI_RPM_LIMIT")
                config = RateLimitConfig(
                    tokens_per_minute=tpm_limit,
                    requests_per_minute=int(rpm_limit) if rpm_limit else None
                )
                _rate_limiter = LLMRateLimiter(config)
    return _rate_limiter


def estimate_tokens(messages: list, model: str = "gpt-4o") -> int:
    """
    Estimate token count for a request.
    Simple heuristic: ~4 characters per token for most models.
    """
    total_chars = 0
    for msg in messages:
        if isinstance(msg, dict):
            total_chars += len(str(msg.get("content", "")))
            total_chars += len(str(msg.get("role", "")))
        else:
            total_chars += len(str(msg))
    
    # Rough estimate: 4 chars per token
    estimated = total_chars // 4
    
    # Add overhead for model name, formatting, etc.
    estimated += 50
    
    return estimated





