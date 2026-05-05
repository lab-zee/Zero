"""
Tests for agent system.
"""
import pytest
from pathlib import Path
from src.agents.base import Agent, AgentConfig, ExecutionTrace, AgentNode, AgentEdge


class TestExecutionTrace:
    """Tests for ExecutionTrace."""

    def test_create_trace(self):
        """Test creating an execution trace."""
        trace = ExecutionTrace()
        assert trace.nodes == []
        assert trace.edges == []

    def test_add_node(self):
        """Test adding nodes to trace."""
        trace = ExecutionTrace()
        node_id = trace.add_node("agent", "Test Agent", {"role": "tester"})

        assert node_id.startswith("agent_")
        assert len(trace.nodes) == 1
        assert trace.nodes[0].type == "agent"
        assert trace.nodes[0].name == "Test Agent"
        assert trace.nodes[0].metadata == {"role": "tester"}

    def test_add_edge(self):
        """Test adding edges to trace."""
        trace = ExecutionTrace()
        node1 = trace.add_node("agent", "Agent 1")
        node2 = trace.add_node("tool", "Tool 1")
        trace.add_edge(node1, node2, "uses")

        assert len(trace.edges) == 1
        assert trace.edges[0].source == node1
        assert trace.edges[0].target == node2
        assert trace.edges[0].label == "uses"

    def test_merge_traces(self):
        """Test merging two traces."""
        trace1 = ExecutionTrace()
        node1 = trace1.add_node("agent", "Agent 1")

        trace2 = ExecutionTrace()
        node2 = trace2.add_node("agent", "Agent 2")
        trace2.add_edge(node1, node2, "delegates")

        trace1.merge(trace2)

        assert len(trace1.nodes) == 2
        assert len(trace1.edges) == 1

    def test_trace_to_dict(self):
        """Test converting trace to dictionary."""
        trace = ExecutionTrace()
        node_id = trace.add_node("agent", "Test Agent", {"role": "test"})

        trace_dict = trace.to_dict()
        assert "nodes" in trace_dict
        assert "edges" in trace_dict
        assert len(trace_dict["nodes"]) == 1
        assert trace_dict["nodes"][0]["name"] == "Test Agent"


class TestAgentNode:
    """Tests for AgentNode."""

    def test_create_node(self):
        """Test creating an agent node."""
        node = AgentNode(
            id="test_123",
            type="agent",
            name="Test Agent",
            metadata={"role": "tester"}
        )

        assert node.id == "test_123"
        assert node.type == "agent"
        assert node.name == "Test Agent"
        assert node.metadata == {"role": "tester"}

    def test_node_to_dict(self):
        """Test converting node to dictionary."""
        node = AgentNode(
            id="test_123",
            type="agent",
            name="Test Agent"
        )

        node_dict = node.to_dict()
        assert node_dict["id"] == "test_123"
        assert node_dict["type"] == "agent"
        assert node_dict["name"] == "Test Agent"
        assert "metadata" in node_dict


class TestAgentEdge:
    """Tests for AgentEdge."""

    def test_create_edge(self):
        """Test creating an agent edge."""
        edge = AgentEdge(
            source="node1",
            target="node2",
            label="connects"
        )

        assert edge.source == "node1"
        assert edge.target == "node2"
        assert edge.label == "connects"

    def test_edge_to_dict(self):
        """Test converting edge to dictionary."""
        edge = AgentEdge(
            source="node1",
            target="node2",
            label="uses"
        )

        edge_dict = edge.to_dict()
        assert edge_dict["source"] == "node1"
        assert edge_dict["target"] == "node2"
        assert edge_dict["label"] == "uses"


class TestAgentConfig:
    """Tests for AgentConfig."""

    def test_create_config(self):
        """Test creating agent configuration."""
        config = AgentConfig(
            id="test_agent",
            name="Test Agent",
            role="Testing agent functionality",
            tools=["test_tool"],
            can_delegate_to=["other_agent"],
            system_prompt="You are a test agent."
        )

        assert config.id == "test_agent"
        assert config.name == "Test Agent"
        assert config.role == "Testing agent functionality"
        assert "test_tool" in config.tools
        assert "other_agent" in config.can_delegate_to


class TestAgentIntegration:
    """Integration tests for agent system."""

    def test_agent_can_load_from_yaml(self):
        """Test that agents can be loaded from YAML configs."""
        # This would require actual YAML config files and registry
        # For now, this is a placeholder for integration testing
        pass

    def test_agent_delegation(self):
        """Test agent delegation mechanism."""
        # This would test actual delegation between agents
        # Placeholder for future implementation
        pass

    def test_agent_tool_execution(self):
        """Test agent tool execution."""
        # This would test tool calling
        # Placeholder for future implementation
        pass
