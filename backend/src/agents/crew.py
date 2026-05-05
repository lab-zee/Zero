"""
Crew orchestration - manages agent collaboration.
"""

from typing import Dict, Any, Optional, Callable
from .base import ExecutionTrace, AgentNode, LLMCallRecord
from .registry import AgentRegistry
from openai import OpenAI


class Crew:
    """
    Crew manages a team of agents and orchestrates their collaboration.
    Routes queries to the Strategic Director who coordinates specialist agents.
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.director = registry.get_director()
        
        if not self.director:
            raise ValueError("Strategic Director agent not found in registry")
    
    def execute(
        self,
        query: str,
        context: Dict[str, Any] = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> tuple[str, ExecutionTrace, list[LLMCallRecord]]:
        """
        Execute a query through the crew.

        The query goes to the Strategic Director, who orchestrates
        specialist agents as needed.

        Args:
            query: User's query
            context: Additional context (organization, conversation history, files)

        Returns:
            tuple: (response_text, execution_trace, llm_call_records)
        """
        context = context or {}
        
        # Create a master trace
        master_trace = ExecutionTrace()
        
        # Add query node
        query_node_id = master_trace.add_node(
            type="query",
            name="User Query",
            metadata={"query": query}
        )
        
        # Add context node if there's conversation history
        if context.get("conversation_history"):
            context_node_id = master_trace.add_node(
                type="context",
                name="Conversation Context",
                metadata={"summary": "Previous conversation history"}
            )
            master_trace.add_edge(context_node_id, query_node_id, label="feeds into")

        # Add parent analysis node for deep-dive follow-ups
        if context.get("parent_analysis_context"):
            parent_node_id = master_trace.add_node(
                type="context",
                name="Parent Analysis",
                metadata={"summary": "Building on previous analysis", "type": "followup"}
            )
            master_trace.add_edge(parent_node_id, query_node_id, label="builds on")

        # Emit initial trace with query/context nodes
        if event_callback:
            event_callback("trace_update", {
                "trace": master_trace.to_dict()
            })
        
        # Wrap event callback to merge master trace structure with agent traces
        def wrapped_event_callback(event_type: str, data: Dict[str, Any]):
            """Wrap event callback to merge master trace structure into trace updates."""
            if event_type == "trace_update" and "trace" in data:
                # Get master trace as dict
                master_trace_dict = master_trace.to_dict()
                agent_trace_dict = data["trace"]
                
                # Merge nodes (deduplicate by ID, keep master trace nodes first)
                merged_nodes = []
                node_ids_seen = set()
                
                # Add master trace nodes first (query, context)
                for node in master_trace_dict.get("nodes", []):
                    if node["id"] not in node_ids_seen:
                        merged_nodes.append(node)
                        node_ids_seen.add(node["id"])
                
                # Add agent trace nodes
                for node in agent_trace_dict.get("nodes", []):
                    if node["id"] not in node_ids_seen:
                        merged_nodes.append(node)
                        node_ids_seen.add(node["id"])
                
                # Merge edges (deduplicate by source->target pair)
                merged_edges = []
                edge_pairs_seen = set()
                
                # Add master trace edges first
                for edge in master_trace_dict.get("edges", []):
                    edge_key = (edge["source"], edge["target"])
                    if edge_key not in edge_pairs_seen:
                        merged_edges.append(edge)
                        edge_pairs_seen.add(edge_key)
                
                # Add agent trace edges
                for edge in agent_trace_dict.get("edges", []):
                    edge_key = (edge["source"], edge["target"])
                    if edge_key not in edge_pairs_seen:
                        # Only add edge if both source and target nodes exist
                        if edge["source"] in node_ids_seen and edge["target"] in node_ids_seen:
                            merged_edges.append(edge)
                            edge_pairs_seen.add(edge_key)
                
                # Ensure query node connects to director if director exists
                director_main_node = None
                for node in merged_nodes:
                    if node["type"] == "agent" and "Director" in node.get("name", ""):
                        director_main_node = node["id"]
                        break
                
                if director_main_node:
                    # Check if edge already exists
                    edge_exists = any(
                        e["source"] == query_node_id and e["target"] == director_main_node 
                        for e in merged_edges
                    )
                    if not edge_exists:
                        merged_edges.append({
                            "source": query_node_id,
                            "target": director_main_node,
                            "label": "routes to"
                        })
                
                # Emit merged trace update
                if event_callback:
                    event_callback("trace_update", {
                        "trace": {
                            "nodes": merged_nodes,
                            "edges": merged_edges
                        }
                    })
            else:
                # Pass through other events unchanged
                if event_callback:
                    event_callback(event_type, data)
        
        # Execute through director (pass wrapped event callback, allow deep delegation)
        response, director_trace, llm_call_records = self.director.execute(
            query,
            context,
            max_iterations=30,  # Director can make many delegations
            max_depth=7,  # Allow up to 7 levels of delegation
            visited_agents=set(),
            event_callback=wrapped_event_callback if event_callback else None
        )

        # Handle None response (agent execution failed)
        if response is None:
            response = "I encountered an error while processing your request. Please try again or rephrase your question."

        # Merge director trace
        if director_trace:
            # Find director's main node
            director_main_node = None
            for node in director_trace.nodes:
                if node.type == "agent" and "Director" in node.name:
                    director_main_node = node.id
                    break
            
            if director_main_node:
                master_trace.add_edge(query_node_id, director_main_node, label="routes to")
            
            master_trace.merge(director_trace)
        
        # Add response node
        response_preview = ""
        if response:
            response_preview = response[:200] + "..." if len(response) > 200 else response
        response_node_id = master_trace.add_node(
            type="response",
            name="Final Response",
            metadata={"preview": response_preview}
        )
        
        # Connect last agent node to response
        if director_trace and director_trace.nodes:
            last_agent_node = None
            for node in reversed(director_trace.nodes):
                if node.type == "agent":
                    last_agent_node = node.id
                    break
            if last_agent_node:
                master_trace.add_edge(last_agent_node, response_node_id, label="produces")
        
        # Emit final trace with response node
        if event_callback:
            event_callback("trace_update", {
                "trace": master_trace.to_dict()
            })
        
        return response, master_trace, llm_call_records or []
