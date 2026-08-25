"""Behavioral coverage for provider selection, conversion, retries, and fallbacks."""

from __future__ import annotations

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src import llm_client as module
from src.llm_client import LLMClient, LLMProviderError


def test_initializes_openai_local_gemini_and_rejects_invalid_provider(monkeypatch):
    openai = MagicMock()
    gemini = MagicMock()
    monkeypatch.setattr(module, "OpenAI", openai)
    monkeypatch.setattr(module.genai, "Client", gemini)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("LOCAL_LLM_BASE_URL", "https://local.example/v1")
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "local-key")

    openai_client = LLMClient("openai", "gpt-4o")
    local_client = LLMClient("local", "ollama/qwen:8b")
    gemini_client = LLMClient("gemini", "gemini-test")

    assert openai_client.client is openai.return_value
    assert local_client.model == "qwen:8b"
    assert gemini_client.genai_client is gemini.return_value
    openai.assert_any_call(api_key="openai-key")
    openai.assert_any_call(
        api_key="local-key",
        base_url="https://local.example/v1",
        default_headers={"User-Agent": "labz-backend/1.0"},
    )
    gemini.assert_called_once_with(api_key="gemini-key")
    with pytest.raises(ValueError, match="Unsupported provider"):
        LLMClient("other", "model")


@pytest.mark.parametrize(
    ("provider", "variable"),
    [("openai", "OPENAI_API_KEY"), ("gemini", "GEMINI_API_KEY")],
)
def test_initialization_requires_provider_key(monkeypatch, provider, variable):
    monkeypatch.delenv(variable, raising=False)
    with pytest.raises(ValueError, match=variable):
        LLMClient(provider, "model")


def _client(provider: str = "openai", model: str = "gpt-4o") -> LLMClient:
    client = object.__new__(LLMClient)
    client.provider = provider
    client.model = model
    client._fallback_model = "gpt-5.6-luna"
    client._gemini_content_cache = {}
    return client


def test_dispatches_by_provider_and_rejects_mutated_invalid_provider(monkeypatch):
    client = _client()
    openai = MagicMock(return_value="openai")
    gemini = MagicMock(return_value="gemini")
    monkeypatch.setattr(client, "_openai_chat_completion", openai)
    monkeypatch.setattr(client, "_gemini_chat_completion", gemini)

    assert client.chat_completions_create([{"role": "user", "content": "hi"}]) == "openai"
    client.provider = "gemini"
    assert client.chat_completions_create([], temperature=0.2) == "gemini"
    client.provider = "broken"
    with pytest.raises(ValueError, match="Unsupported provider"):
        client.chat_completions_create([])


def test_openai_completion_builds_payload_records_usage_and_handles_reasoning(monkeypatch):
    client = _client(model="gpt-5.6-luna")
    api = MagicMock()
    response = SimpleNamespace(usage=SimpleNamespace(total_tokens=77))
    api.chat.completions.create.return_value = response
    client.client = api
    limiter = MagicMock()
    limiter.wait_if_needed.return_value = 0
    monkeypatch.setattr(module, "get_rate_limiter", lambda: limiter)
    monkeypatch.setattr(module, "estimate_tokens", lambda _messages, _model: 12)
    tools = [{"type": "function", "function": {"name": "lookup"}}]

    assert client._openai_chat_completion(
        [{"role": "user", "content": "hi"}],
        tools,
        "required",
        0.2,
        max_tokens=50,
    ) is response

    api.chat.completions.create.assert_called_once_with(
        model="gpt-5.6-luna",
        messages=[{"role": "user", "content": "hi"}],
        tools=tools,
        tool_choice="required",
        reasoning_effort="none",
        max_tokens=50,
    )
    limiter.wait_if_needed.assert_called_once_with(112)
    limiter.record_usage.assert_called_once_with(77)


def test_openai_completion_records_estimate_without_usage(monkeypatch):
    client = _client(model="gpt-4o")
    api = MagicMock()
    api.chat.completions.create.return_value = SimpleNamespace(usage=None)
    client.client = api
    limiter = MagicMock()
    limiter.wait_if_needed.return_value = 1.25
    monkeypatch.setattr(module, "get_rate_limiter", lambda: limiter)
    monkeypatch.setattr(module, "estimate_tokens", lambda _messages, _model: 30)

    client._openai_chat_completion([], None, None, 0.5)

    api.chat.completions.create.assert_called_once_with(
        model="gpt-4o",
        messages=[],
        temperature=0.5,
    )
    limiter.record_usage.assert_called_once_with(30)


def test_openai_rate_limit_retries_then_succeeds(monkeypatch):
    class FakeRateLimitError(Exception):
        def __init__(self, retry_after: str):
            self.response = SimpleNamespace(headers={"Retry-After": retry_after})

    client = _client()
    api = MagicMock()
    api.chat.completions.create.side_effect = [
        FakeRateLimitError("0.25"),
        SimpleNamespace(usage=None),
    ]
    client.client = api
    limiter = MagicMock()
    limiter.wait_if_needed.return_value = 0
    monkeypatch.setattr(module, "RateLimitError", FakeRateLimitError)
    monkeypatch.setattr(module, "get_rate_limiter", lambda: limiter)
    monkeypatch.setattr(module, "estimate_tokens", lambda *_args: 10)
    sleeps: list[float] = []
    monkeypatch.setattr(module.time, "sleep", sleeps.append)

    client._openai_chat_completion([], None, None, 0.7)

    assert api.chat.completions.create.call_count == 2
    limiter.record_rate_limit_error.assert_called_once_with(0.25)
    assert sleeps == [0.25]


def test_openai_rate_limit_raises_after_three_attempts(monkeypatch):
    class FakeRateLimitError(Exception):
        response = None

    client = _client()
    api = MagicMock()
    api.chat.completions.create.side_effect = FakeRateLimitError("limited")
    client.client = api
    limiter = MagicMock()
    limiter.wait_if_needed.return_value = 0
    monkeypatch.setattr(module, "RateLimitError", FakeRateLimitError)
    monkeypatch.setattr(module, "get_rate_limiter", lambda: limiter)
    monkeypatch.setattr(module, "estimate_tokens", lambda *_args: 10)
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    with pytest.raises(FakeRateLimitError):
        client._openai_chat_completion([], None, None, 0.7)
    assert api.chat.completions.create.call_count == 3
    assert limiter.record_rate_limit_error.call_count == 2


def test_converts_tools_and_full_message_history_for_gemini():
    client = _client("gemini", "gemini-test")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "lookup",
                "description": "Look up evidence",
                "parameters": {"type": "object"},
            },
        },
        {"type": "other"},
    ]
    converted_tools = client._convert_openai_tools_to_gemini(tools)
    declaration = converted_tools[0].function_declarations[0]
    assert declaration.name == "lookup"

    signature = base64.b64encode(b"signature").decode("ascii")
    messages = [
        {"role": "system", "content": "System one"},
        {"role": "system", "content": "System two"},
        {"role": "user", "content": "Question"},
        {
            "role": "assistant",
            "content": "Calling",
            "tool_calls": [
                {
                    "id": "call-1",
                    "function": {"name": "lookup", "arguments": '{"query": "risk"}'},
                    "thought_signature": signature,
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call-1", "content": "Result"},
    ]

    contents, system = client._convert_messages_for_gemini(messages)

    assert system == "System one\n\nSystem two"
    assert [content.role for content in contents] == ["user", "model", "user"]
    assert contents[1].parts[1].function_call.name == "lookup"
    assert contents[1].parts[1].thought_signature == b"signature"
    assert contents[2].parts[0].function_response.name == "lookup"


def test_message_conversion_reuses_cached_content_and_handles_bad_arguments():
    client = _client("gemini", "gemini-test")
    cached = module.types.Content(role="model", parts=[module.types.Part(text="cached")])
    client._gemini_content_cache["cached-id"] = cached
    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "cached-id", "function": {"name": "cached", "arguments": "{}"}}
            ],
        },
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "bad-id", "function": {"name": "bad", "arguments": "{bad"}}
            ],
        },
    ]
    contents, _system = client._convert_messages_for_gemini(messages)
    assert contents[0] is cached
    assert contents[1].parts[0].function_call.args == {}
    assert client._find_function_name_for_tool_call(messages, "missing") == "unknown"


def test_gemini_text_and_tool_responses(monkeypatch):
    client = _client("gemini", "gemini-test")
    model_api = MagicMock()
    client.genai_client = SimpleNamespace(models=model_api)
    text_part = SimpleNamespace(function_call=None, text="answer", thought=False)
    model_api.generate_content.return_value = SimpleNamespace(
        candidates=[SimpleNamespace(content=SimpleNamespace(parts=[text_part]))]
    )

    response = client._gemini_chat_completion(
        [{"role": "user", "content": "question"}],
        None,
        None,
        0.3,
    )
    assert response.choices[0].message.content == "answer"
    assert response.model == "gemini-test"

    function_call = SimpleNamespace(name="lookup", args={"q": "risk"})
    tool_part = SimpleNamespace(
        function_call=function_call,
        text=None,
        thought=False,
        thought_signature=b"sig",
    )
    original = SimpleNamespace(parts=[tool_part])
    model_api.generate_content.return_value = SimpleNamespace(
        candidates=[SimpleNamespace(content=original)]
    )
    response = client._gemini_chat_completion([], [], "none", 0.1)
    call = response.choices[0].message.tool_calls[0]
    assert call.function.name == "lookup"
    assert call.function.arguments == '{"q": "risk"}'
    assert call.thought_signature == base64.b64encode(b"sig").decode("ascii")
    assert client._gemini_content_cache[call.id] is original


def test_gemini_retry_and_fallback(monkeypatch):
    client = _client("gemini", "gemini-test")
    transient = RuntimeError("503 UNAVAILABLE")
    model_api = MagicMock()
    model_api.generate_content.side_effect = [
        transient,
        transient,
        SimpleNamespace(candidates=[]),
    ]
    client.genai_client = SimpleNamespace(models=model_api)
    sleeps: list[float] = []
    monkeypatch.setattr(module.time, "sleep", sleeps.append)

    response = client._gemini_chat_completion([], None, None, 0.2)
    assert response.choices[0].message.content == ""
    assert sleeps == [2.0, 4.0]

    model_api.generate_content.side_effect = transient
    fallback = MagicMock(return_value="fallback")
    monkeypatch.setattr(client, "_openai_fallback", fallback)
    assert client._gemini_chat_completion([], None, None, 0.2) == "fallback"
    fallback.assert_called_once()

    model_api.generate_content.side_effect = RuntimeError("invalid request")
    with pytest.raises(Exception, match="Gemini API error"):
        client._gemini_chat_completion([], None, None, 0.2)


def test_fallback_requires_key_and_routes_to_openai(monkeypatch):
    client = _client("gemini", "gemini-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LLMProviderError) as exc:
        client._openai_fallback([], None, None, 0.2)
    assert exc.value.code == "LLM_FALLBACK_FAILED"

    monkeypatch.setenv("OPENAI_API_KEY", "fallback-key")
    openai = MagicMock()
    monkeypatch.setattr(module, "OpenAI", openai)
    completion = MagicMock(return_value="ok")
    monkeypatch.setattr(client, "_openai_chat_completion", completion)
    assert client._openai_fallback([], None, None, 0.2) == "ok"
    completion.assert_called_once_with(
        [],
        None,
        None,
        0.2,
        client=openai.return_value,
        model="gpt-5.6-luna",
    )


def test_response_builders_reasoning_and_retryable_detection():
    client = _client()
    assert client._is_reasoning_model("GPT-5.6-Luna")
    assert client._is_reasoning_model("o3-mini")
    assert not client._is_reasoning_model("gpt-4o")
    assert client._is_retryable_gemini_error(SimpleNamespace(code=429))
    assert client._is_retryable_gemini_error(RuntimeError("service overloaded"))
    assert not client._is_retryable_gemini_error(RuntimeError("bad input"))

    text = client._build_text_response("hello", "model")
    assert text.choices[0].finish_reason == "stop"
    assert text.choices[0].message.content == "hello"


def test_embeddings_create_handles_single_list_and_missing_key(monkeypatch):
    client = _client()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="required for embeddings"):
        client.embeddings_create("text")

    monkeypatch.setenv("OPENAI_API_KEY", "key")
    api = MagicMock()
    api.return_value.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[1.0]), SimpleNamespace(embedding=[2.0])]
    )
    monkeypatch.setattr(module, "OpenAI", api)
    assert client.embeddings_create("text") == [[1.0]]
    assert client.embeddings_create(["one", "two"]) == [[1.0], [2.0]]


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (LLMProviderError("typed", "CUSTOM"), "CUSTOM"),
        (RuntimeError("429 rate limit"), "RATE_LIMIT"),
        (RuntimeError("OPENAI_API_KEY is not set for fallback"), "LLM_FALLBACK_FAILED"),
        (RuntimeError("Gemini unavailable now"), "LLM_FALLBACK_FAILED"),
        (RuntimeError("API key not configured"), "MISSING_API_KEY"),
        (RuntimeError("other"), "LLM_ERROR"),
    ],
)
def test_classifies_llm_errors(error, code):
    payload = module.classify_llm_error(error)
    assert payload["code"] == code
    assert payload["message"]


def test_provider_detection_factories_and_missing_key_messages(monkeypatch):
    constructor = MagicMock(return_value="client")
    monkeypatch.setattr(module, "LLMClient", constructor)
    monkeypatch.setenv("OPENAI_API_KEY", "openai")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini")

    assert module.get_llm_client("gemini-fast") == "client"
    constructor.assert_called_with(provider="gemini", model="gemini-fast")
    module.get_llm_client("ollama/qwen")
    assert constructor.call_args.kwargs["provider"] == "local"
    module.get_llm_client("gpt-4o")
    assert constructor.call_args.kwargs["provider"] == "openai"

    assert module.provider_for_model("gemini-fast") == "gemini"
    assert module.provider_for_model("qwen:8b") == "local"
    assert module.provider_for_model("gpt-4o") == "openai"
    assert module.missing_chat_api_key_message("gpt-4o") is None
    monkeypatch.delenv("GEMINI_API_KEY")
    assert "Gemini API key" in module.missing_chat_api_key_message("gemini-fast")
