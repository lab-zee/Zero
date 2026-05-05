"""
Tests for the execution trace summarizer utility.
"""
import pytest
from src.agents.trace_summarizer import summarize_execution_trace, _get_agent_tool_results


class TestSummarizeExecutionTrace:
    """Tests for summarize_execution_trace."""

    def test_empty_trace(self):
        """Returns empty string for empty/None traces."""
        assert summarize_execution_trace(None) == ""
        assert summarize_execution_trace({}) == ""
        assert summarize_execution_trace({"nodes": []}) == ""

    def test_agents_only(self):
        """Summarizes agent chain correctly."""
        trace = {
            "nodes": [
                {"id": "agent_1", "type": "agent", "name": "Strategic Director", "metadata": {}},
                {"id": "agent_2", "type": "agent", "name": "Market Research", "metadata": {}},
                {"id": "agent_3", "type": "agent", "name": "Synthesizer", "metadata": {}},
            ],
            "edges": []
        }
        result = summarize_execution_trace(trace)
        assert "Agents consulted:" in result
        assert "Strategic Director" in result
        assert "Market Research" in result
        assert "Synthesizer" in result

    def test_tool_usage_summary(self):
        """Summarizes tool usage with counts."""
        trace = {
            "nodes": [
                {"id": "tool_1", "type": "tool", "name": "web_search", "metadata": {}},
                {"id": "tool_2", "type": "tool", "name": "web_search", "metadata": {}},
                {"id": "tool_3", "type": "tool", "name": "calculator", "metadata": {}},
            ],
            "edges": []
        }
        result = summarize_execution_trace(trace)
        assert "Tools used:" in result
        assert "web_search (2x)" in result
        assert "calculator (1x)" in result

    def test_delegation_tasks(self):
        """Extracts delegation task descriptions from edges."""
        trace = {
            "nodes": [
                {"id": "agent_1", "type": "agent", "name": "Strategic Director", "metadata": {}},
                {"id": "agent_2", "type": "agent", "name": "Market Research", "metadata": {}},
            ],
            "edges": [
                {"source": "agent_1", "target": "agent_2", "label": "delegates: Analyze healthcare market trends"},
            ]
        }
        result = summarize_execution_trace(trace)
        assert "Market Research" in result
        assert "Analyze healthcare market trends" in result

    def test_excludes_director_and_synthesizer_from_findings(self):
        """Director and Synthesizer should not appear in key findings."""
        trace = {
            "nodes": [
                {"id": "agent_1", "type": "agent", "name": "Strategic Director", "metadata": {}},
                {"id": "agent_2", "type": "agent", "name": "Business SME", "metadata": {}},
                {"id": "agent_3", "type": "agent", "name": "Strategy Synthesizer", "metadata": {}},
            ],
            "edges": [
                {"source": "agent_1", "target": "agent_2", "label": "delegates: Analyze business context"},
            ]
        }
        result = summarize_execution_trace(trace)
        findings_section = result.split("Key findings from specialists:")[-1] if "Key findings" in result else ""
        # Director and Synthesizer should not be in the findings
        assert "Strategic Director" not in findings_section
        assert "Strategy Synthesizer" not in findings_section
        # But Business SME should be
        assert "Business SME" in findings_section

    def test_tool_results_linked_to_agents(self):
        """Notable tool outputs should be included."""
        trace = {
            "nodes": [
                {"id": "agent_1", "type": "agent", "name": "Market Research", "metadata": {}},
                {"id": "tool_1", "type": "tool", "name": "web_search", "metadata": {
                    "result_preview": "Found 5 results about healthcare market growth trends..."
                }},
            ],
            "edges": [
                {"source": "agent_1", "target": "tool_1", "label": "uses"},
            ]
        }
        result = summarize_execution_trace(trace)
        assert "Notable tool outputs:" in result
        assert "healthcare market growth" in result

    def test_max_length_respected(self):
        """Summary should not exceed max_length."""
        trace = {
            "nodes": [
                {"id": f"agent_{i}", "type": "agent", "name": f"Agent {i}", "metadata": {}}
                for i in range(20)
            ] + [
                {"id": f"tool_{i}", "type": "tool", "name": f"tool_{i}", "metadata": {
                    "result_preview": "A" * 500
                }}
                for i in range(20)
            ],
            "edges": []
        }
        result = summarize_execution_trace(trace, max_length=500)
        assert len(result) <= 500

    def test_deduplicates_agent_names(self):
        """Agent names should not be repeated in the chain."""
        trace = {
            "nodes": [
                {"id": "agent_1", "type": "agent", "name": "Director", "metadata": {}},
                {"id": "agent_2", "type": "agent", "name": "Director", "metadata": {}},
            ],
            "edges": []
        }
        result = summarize_execution_trace(trace)
        # "Director" should appear only once in the chain
        agents_line = [l for l in result.split("\n") if "Agents consulted:" in l][0]
        assert agents_line.count("Director") == 1

    def test_full_realistic_trace(self):
        """Integration test with a realistic trace structure."""
        trace = {
            "nodes": [
                {"id": "query_1", "type": "query", "name": "User Query", "metadata": {"query": "What's our market opportunity?"}},
                {"id": "agent_dir", "type": "agent", "name": "Strategic Director", "metadata": {"role": "orchestrator"}},
                {"id": "agent_mkt", "type": "agent", "name": "Market Research", "metadata": {"role": "market analyst"}},
                {"id": "tool_ws1", "type": "tool", "name": "web_search", "metadata": {
                    "arguments": {"query": "healthcare SaaS market 2025"},
                    "result_preview": "The global healthcare SaaS market is projected to reach $50B by 2026..."
                }},
                {"id": "agent_fin", "type": "agent", "name": "Financial Analyst", "metadata": {"role": "financial modeling"}},
                {"id": "tool_calc", "type": "tool", "name": "calculator", "metadata": {
                    "arguments": {"expression": "50000000000 * 0.03"},
                    "result_preview": "1500000000"
                }},
                {"id": "agent_syn", "type": "agent", "name": "Strategy Synthesizer", "metadata": {"role": "synthesizer"}},
                {"id": "resp_1", "type": "response", "name": "Final Response", "metadata": {"preview": "Based on analysis..."}},
            ],
            "edges": [
                {"source": "query_1", "target": "agent_dir", "label": "routes to"},
                {"source": "agent_dir", "target": "agent_mkt", "label": "delegates: Analyze healthcare SaaS market"},
                {"source": "agent_mkt", "target": "tool_ws1", "label": "uses"},
                {"source": "agent_dir", "target": "agent_fin", "label": "delegates: Model revenue projections"},
                {"source": "agent_fin", "target": "tool_calc", "label": "uses"},
                {"source": "agent_dir", "target": "agent_syn", "label": "delegates: Synthesize findings"},
                {"source": "agent_syn", "target": "resp_1", "label": "produces"},
            ]
        }
        result = summarize_execution_trace(trace)

        # Should contain agent chain
        assert "Market Research" in result
        assert "Financial Analyst" in result

        # Should contain tool usage
        assert "web_search" in result
        assert "calculator" in result

        # Should contain delegation tasks
        assert "healthcare SaaS market" in result
        assert "revenue projections" in result

        # Should contain tool results
        assert "healthcare SaaS market" in result or "$50B" in result


class TestGetAgentToolResults:
    """Tests for _get_agent_tool_results helper."""

    def test_finds_connected_tools(self):
        """Correctly finds tool results connected to an agent."""
        nodes = [
            {"id": "agent_1", "type": "agent", "name": "Agent"},
            {"id": "tool_1", "type": "tool", "name": "web_search", "metadata": {"result_preview": "Found results"}},
            {"id": "tool_2", "type": "tool", "name": "calculator", "metadata": {"result_preview": "42"}},
            {"id": "tool_3", "type": "tool", "name": "other", "metadata": {"result_preview": "Unrelated"}},
        ]
        edges = [
            {"source": "agent_1", "target": "tool_1", "label": "uses"},
            {"source": "agent_1", "target": "tool_2", "label": "uses"},
            # tool_3 is NOT connected to agent_1
        ]
        result = _get_agent_tool_results("agent_1", nodes, edges)
        assert "Found results" in result
        assert "42" in result
        assert "Unrelated" not in result

    def test_no_connected_tools(self):
        """Returns empty string when no tools are connected."""
        result = _get_agent_tool_results("agent_1", [], [])
        assert result == ""
