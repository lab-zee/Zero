"""
Execution Trace Summarizer - Extracts structured text summaries from execution traces.

Used to provide context for follow-up question generation and true follow-up queries
that build on the full analysis of a parent question.
"""

from typing import Dict, Any, List
from collections import Counter


def summarize_execution_trace(trace_dict: Dict[str, Any], max_length: int = 3000) -> str:
    """
    Summarize an execution trace into a concise text description.

    Extracts agent chain, tool usage, and key findings from each specialist
    for use as context in follow-up generation and follow-up queries.

    Args:
        trace_dict: The execution trace as a dict with "nodes" and "edges" keys
        max_length: Maximum character length for the summary (progressively truncates)

    Returns:
        Structured text summary of the execution trace
    """
    if not trace_dict or not trace_dict.get("nodes"):
        return ""

    nodes = trace_dict.get("nodes", [])
    edges = trace_dict.get("edges", [])

    agents = [n for n in nodes if n.get("type") == "agent"]
    tools = [n for n in nodes if n.get("type") == "tool"]

    if not agents and not tools:
        return ""

    parts = []

    # 1. Agent chain (ordered by appearance)
    agent_names = []
    for a in agents:
        name = a.get("name", "Unknown")
        if name not in agent_names:
            agent_names.append(name)
    if agent_names:
        parts.append(f"Agents consulted: {' -> '.join(agent_names)}")

    # 2. Tool usage summary
    tool_counts = Counter(t.get("name", "unknown") for t in tools)
    if tool_counts:
        tool_summary = ", ".join(f"{name} ({count}x)" for name, count in tool_counts.items())
        parts.append(f"Tools used: {tool_summary}")

    # 3. Build delegation map from edges to understand what each agent was asked to do
    delegation_tasks = {}
    for edge in edges:
        label = edge.get("label", "")
        if label.startswith("delegates:"):
            target_id = edge.get("target", "")
            task_text = label.replace("delegates:", "").strip()
            delegation_tasks[target_id] = task_text

    # 4. Key findings per agent
    # Calculate available space for findings
    header_length = sum(len(p) for p in parts) + 20  # overhead
    remaining = max_length - header_length

    # Exclude Director and filter to specialist agents with meaningful content
    specialist_agents = [
        a for a in agents
        if "Director" not in a.get("name", "") and "Synthesizer" not in a.get("name", "")
    ]

    if specialist_agents:
        parts.append("\nKey findings from specialists:")
        per_agent_budget = max(150, remaining // max(len(specialist_agents), 1))

        for agent in specialist_agents:
            meta = agent.get("metadata", {}) or {}
            agent_name = agent.get("name", "Unknown")
            agent_id = agent.get("id", "")

            # Get the delegation task (what the agent was asked to do)
            task = delegation_tasks.get(agent_id, "")

            # Get tool results connected to this agent
            agent_tool_results = _get_agent_tool_results(agent_id, nodes, edges)

            finding_parts = []
            if task:
                finding_parts.append(f"Task: {task[:200]}")
            if agent_tool_results:
                finding_parts.append(f"Findings: {agent_tool_results[:per_agent_budget - 220]}")

            if finding_parts:
                parts.append(f"- {agent_name}: {'; '.join(finding_parts)}")

    # 5. Tool results summary (for tools with notable outputs)
    notable_tools = [
        t for t in tools
        if t.get("metadata", {}).get("result_preview")
        and t.get("name") not in ("delegate_to_agent",)
    ]

    if notable_tools:
        # Only add if we have budget remaining
        current_length = sum(len(p) for p in parts)
        if current_length < max_length - 200:
            parts.append("\nNotable tool outputs:")
            tool_budget = (max_length - current_length - 50) // max(len(notable_tools), 1)
            tool_budget = min(tool_budget, 300)  # Cap per-tool

            for tool in notable_tools[:8]:  # Limit to 8 most notable
                meta = tool.get("metadata", {}) or {}
                tool_name = tool.get("name", "unknown")
                preview = meta.get("result_preview", "")
                if preview:
                    parts.append(f"- {tool_name}: {preview[:tool_budget]}")

    summary = "\n".join(parts)
    return summary[:max_length]


def _get_agent_tool_results(agent_id: str, nodes: List[Dict], edges: List[Dict]) -> str:
    """Get concatenated tool result previews for tools used by a specific agent."""
    # Find tool node IDs connected to this agent via "uses" edges
    tool_ids = set()
    for edge in edges:
        if edge.get("source") == agent_id and edge.get("label") == "uses":
            tool_ids.add(edge.get("target", ""))

    results = []
    for node in nodes:
        if node.get("id") in tool_ids and node.get("type") == "tool":
            meta = node.get("metadata", {}) or {}
            preview = meta.get("result_preview", "")
            if preview:
                results.append(preview)

    return " | ".join(results)
