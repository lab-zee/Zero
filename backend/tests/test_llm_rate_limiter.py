"""State-transition tests for the rolling-window LLM rate limiter."""

from __future__ import annotations

from src import llm_rate_limiter as module
from src.llm_rate_limiter import LLMRateLimiter, RateLimitConfig, estimate_tokens


def test_records_usage_and_cleans_expired_entries(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(module.time, "time", lambda: now[0])
    limiter = LLMRateLimiter(RateLimitConfig(tokens_per_minute=100, requests_per_minute=2))

    limiter.record_usage(40)
    now[0] = 120.0
    limiter.record_usage(30)
    assert limiter.current_tokens == 70
    assert limiter._get_available_tokens() == 30
    assert limiter._can_make_request() is False

    now[0] = 161.0
    assert limiter._get_available_tokens() == 70
    assert limiter._can_make_request() is True
    assert list(limiter.token_usage) == [(120.0, 30)]


def test_waits_for_token_window_and_rechecks_state(monkeypatch):
    now = [120.0]
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(module.time, "time", lambda: now[0])
    monkeypatch.setattr(module.time, "sleep", sleep)
    limiter = LLMRateLimiter(RateLimitConfig(tokens_per_minute=50))
    limiter.token_usage.append((100.0, 50))
    limiter.current_tokens = 50

    waited = limiter.wait_if_needed(20)

    assert waited == 40.1
    assert slept == [40.1]
    assert limiter.current_tokens == 0


def test_waits_for_request_window(monkeypatch):
    now = [200.0]
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(module.time, "time", lambda: now[0])
    monkeypatch.setattr(module.time, "sleep", sleep)
    limiter = LLMRateLimiter(RateLimitConfig(tokens_per_minute=100, requests_per_minute=1))
    limiter.request_times.append(180.0)

    assert limiter.wait_if_needed(10) == 40.1
    assert slept == [40.1]
    assert not limiter.request_times


def test_no_wait_when_limits_allow_request(monkeypatch):
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: (_ for _ in ()).throw(AssertionError()))
    limiter = LLMRateLimiter(RateLimitConfig(tokens_per_minute=100))
    assert limiter.wait_if_needed(50) == 0


def test_rate_limit_error_uses_retry_after_or_default(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    limiter = LLMRateLimiter()

    limiter.record_rate_limit_error(2.5)
    limiter.record_rate_limit_error()

    assert sleeps == [2.5, 1.0]


def test_global_limiter_uses_environment_once(monkeypatch):
    monkeypatch.setattr(module, "_rate_limiter", None)
    monkeypatch.setenv("OPENAI_TPM_LIMIT", "1234")
    monkeypatch.setenv("OPENAI_RPM_LIMIT", "7")

    first = module.get_rate_limiter()
    second = module.get_rate_limiter()

    assert first is second
    assert first.config == RateLimitConfig(tokens_per_minute=1234, requests_per_minute=7)


def test_estimate_tokens_accounts_for_roles_content_and_non_dict_messages():
    messages = [{"role": "user", "content": "abcdefgh"}, "plain"]
    expected_chars = len("user") + len("abcdefgh") + len("plain")
    assert estimate_tokens(messages, "ignored-model") == expected_chars // 4 + 50
