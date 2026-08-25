"""Behavioral tests for crew trace orchestration and event state transitions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.agents.base import ExecutionTrace
from src.agents.crew import Crew


def test_crew_requires_director():
    registry = MagicMock()
    registry.get_director.return_value = None
    with pytest.raises(ValueError, match="Strategic Director"):
        Crew(registry)


def test_execute_merges_context_agent_events_and_final_response():
    director = MagicMock()
    registry = MagicMock()
    registry.get_director.return_value = director
    events: list[tuple[str, dict]] = []

    director_trace = ExecutionTrace()
    director_id = director_trace.add_node("agent", "Strategic Director", {"role": "lead"})
    specialist_id = director_trace.add_node("agent", "Risk Analyst", {})
    director_trace.add_edge(director_id, specialist_id, "delegates")

    def execute(_query, _context, **kwargs):
        callback = kwargs["event_callback"]
        callback(
            "trace_update",
            {
                "trace": {
                    "nodes": [
                        {
                            "id": director_id,
                            "type": "agent",
                            "name": "Strategic Director",
                            "metadata": {},
                        },
                        {
                            "id": "tool-1",
                            "type": "tool",
                            "name": "lookup",
                            "metadata": {},
                        },
                    ],
                    "edges": [
                        {"source": director_id, "target": "tool-1", "label": "uses"},
                        {"source": "missing", "target": "tool-1", "label": "invalid"},
                    ],
                }
            },
        )
        callback("progress", {"status": "working"})
        return "A" * 250, director_trace, ["record"]

    director.execute.side_effect = execute
    crew = Crew(registry)

    response, trace, records = crew.execute(
        "Assess risk",
        {
            "conversation_history": [{"role": "user", "content": "Earlier"}],
            "parent_analysis_context": "Prior analysis",
        },
        event_callback=lambda event, data: events.append((event, data)),
    )

    assert response == "A" * 250
    assert records == ["record"]
    assert {node.type for node in trace.nodes} >= {"query", "context", "agent", "response"}
    response_node = next(node for node in trace.nodes if node.type == "response")
    assert response_node.metadata["preview"] == "A" * 200 + "..."
    assert any(edge.label == "routes to" for edge in trace.edges)
    assert any(edge.source == specialist_id and edge.target == response_node.id for edge in trace.edges)
    assert events[0][0] == "trace_update"
    assert ("progress", {"status": "working"}) in events
    merged_event = events[1][1]["trace"]
    assert "tool-1" in {node["id"] for node in merged_event["nodes"]}
    assert not any(edge["source"] == "missing" for edge in merged_event["edges"])
    director.execute.assert_called_once()
    kwargs = director.execute.call_args.kwargs
    assert kwargs["max_iterations"] == 30
    assert kwargs["max_depth"] == 7
    assert kwargs["visited_agents"] == set()


def test_execute_handles_failed_director_without_trace_or_callback():
    director = MagicMock()
    director.execute.return_value = (None, None, None)
    registry = MagicMock()
    registry.get_director.return_value = director

    response, trace, records = Crew(registry).execute("question")

    assert response.startswith("I encountered an error")
    assert records == []
    assert [node.type for node in trace.nodes] == ["query", "response"]
    assert not trace.edges
