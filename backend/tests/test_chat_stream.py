"""Tests for the streaming chat endpoint (mocked crew execution)."""

import json
from unittest.mock import patch

import pytest

from src.agents.base import ExecutionTrace


def _parse_sse_events(raw: str) -> list[dict]:
    events = []
    for block in raw.split("\n\n"):
        if not block.strip() or block.strip().startswith(":"):
            continue
        for line in block.split("\n"):
            if line.startswith("data:"):
                try:
                    events.append(json.loads(line.split(":", 1)[1].strip()))
                except json.JSONDecodeError:
                    continue
    return events


def _mock_crew_execute(self, query, context=None, event_callback=None):
    trace = ExecutionTrace()
    trace.add_node("agent", "Test Synthesizer", {"role": "test"})
    if event_callback:
        event_callback("trace_update", {"trace": trace.to_dict()})
    return "Mock strategic answer with enough words for validation.", trace, []


class TestChatStreamEndpoint:
    def test_stream_returns_response_event(
        self,
        authenticated_client,
        test_organization,
        test_thread,
        monkeypatch,
    ):
        monkeypatch.setenv("GEMINI_API_KEY", "test_key_for_testing")

        with patch("src.main.Crew.execute", _mock_crew_execute):
            with patch(
                "src.agents.tools.followup_generator.generate_followup_questions",
                return_value={"related": [], "deep_dive": []},
            ):
                response = authenticated_client.post(
                    "/api/llm/chat/stream",
                    json={
                        "message": "What is our go-to-market strategy?",
                        "organization_id": test_organization.id,
                        "thread_id": test_thread.id,
                        "chat_mode": "agentic",
                    },
                )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        events = _parse_sse_events(response.text)
        event_types = [e.get("type") for e in events]
        assert "response" in event_types or "done" in event_types

    def test_stream_requires_organization(
        self,
        authenticated_client,
        monkeypatch,
    ):
        monkeypatch.setenv("GEMINI_API_KEY", "test_key_for_testing")

        response = authenticated_client.post(
            "/api/llm/chat/stream",
            json={"message": "Hello"},
        )
        assert response.status_code == 422 or response.status_code == 400

    def test_stream_creates_thread_when_missing(
        self,
        authenticated_client,
        test_organization,
        monkeypatch,
    ):
        monkeypatch.setenv("GEMINI_API_KEY", "test_key_for_testing")

        with patch("src.main.Crew.execute", _mock_crew_execute):
            with patch(
                "src.agents.tools.followup_generator.generate_followup_questions",
                return_value={"related": [], "deep_dive": []},
            ):
                response = authenticated_client.post(
                    "/api/llm/chat/stream",
                    json={
                        "message": "Quick question",
                        "organization_id": test_organization.id,
                        "chat_mode": "agentic",
                    },
                )

        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        assert any(e.get("type") == "thread_created" for e in events)
