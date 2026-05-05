"""
Base Agent class with OpenAI function calling and execution trace.
"""

import copy
import json
import uuid
import time
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Union, TYPE_CHECKING
from dataclasses import dataclass, field
from openai import OpenAI
from ..llm_client import LLMClient

if TYPE_CHECKING:
    from .registry import AgentRegistry


@dataclass
class AgentNode:
    """Represents a node in the execution trace graph."""
    id: str
    type: str  # "agent" | "tool" | "context" | "query" | "response"
    name: str
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "metadata": self.metadata or {}
        }


@dataclass
class AgentEdge:
    """Represents an edge (connection) in the execution trace graph."""
    source: str
    target: str
    label: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "label": self.label
        }


@dataclass
class ExecutionTrace:
    """Captures the execution flow of agents and tools. Thread-safe for parallel delegation."""
    nodes: List[AgentNode] = field(default_factory=list)
    edges: List[AgentEdge] = field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add_node(self, type: str, name: str, metadata: Optional[Dict] = None) -> str:
        """Add a node and return its ID."""
        node_id = f"{type}_{uuid.uuid4().hex[:8]}"
        with self._lock:
            self.nodes.append(AgentNode(id=node_id, type=type, name=name, metadata=metadata))
        return node_id

    def add_edge(self, source: str, target: str, label: Optional[str] = None):
        """Add an edge between two nodes."""
        with self._lock:
            self.edges.append(AgentEdge(source=source, target=target, label=label))

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            result = {
                "nodes": [n.to_dict() for n in self.nodes],
                "edges": [e.to_dict() for e in self.edges]
            }
            if self.metadata:
                result["metadata"] = self.metadata
        return result

    def merge(self, other: "ExecutionTrace"):
        """Merge another trace into this one, deduplicating nodes by ID."""
        with self._lock:
            # Track existing node IDs to avoid duplicates (use dict to keep first occurrence)
            existing_nodes = {node.id: node for node in self.nodes}

            # Add nodes that don't already exist (keep first occurrence)
            for node in other.nodes:
                if node.id not in existing_nodes:
                    existing_nodes[node.id] = node

            # Update nodes list with deduplicated nodes
            self.nodes = list(existing_nodes.values())

            # Get all valid node IDs
            valid_node_ids = {node.id for node in self.nodes}

            # Track existing edge pairs to avoid duplicates
            existing_edges = {(edge.source, edge.target) for edge in self.edges}

            # Add edges that don't already exist and reference valid nodes
            for edge in other.edges:
                edge_key = (edge.source, edge.target)
                if edge_key not in existing_edges:
                    # Only add edge if both source and target nodes exist
                    if edge.source in valid_node_ids and edge.target in valid_node_ids:
                        self.edges.append(edge)
                        existing_edges.add(edge_key)


@dataclass
class AgentConfig:
    """Configuration for an agent loaded from YAML."""
    id: str
    name: str
    role: str
    tools: List[str]
    can_delegate_to: List[str]
    system_prompt: str
    model: Optional[str] = None  # Optional per-agent model override (e.g., "gpt-4o-mini", "gemini-3-pro-preview")


@dataclass
class LLMCallRecord:
    """Records a single LLM API call for prompt traceability."""
    agent_name: str
    agent_id: str
    model: str
    iteration: int
    messages: List[Dict[str, Any]]
    tools: Optional[List[Dict[str, Any]]]
    response_content: Optional[str]
    response_tool_calls: Optional[List[Dict[str, Any]]]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_id": self.agent_id,
            "model": self.model,
            "iteration": self.iteration,
            "messages": self.messages,
            "tools": self.tools,
            "response_content": self.response_content,
            "response_tool_calls": self.response_tool_calls,
            "timestamp": self.timestamp,
        }


class Agent:
    """
    Base Agent class with OpenAI function calling and execution tracing.
    
    Each agent:
    - Has a specific role and system prompt
    - Can use tools via OpenAI function calling
    - Can delegate to other agents
    - Records execution trace for visualization
    """
    
    def __init__(
        self,
        config: AgentConfig,
        client: Union[OpenAI, LLMClient],
        tool_registry: Dict[str, Callable] = None,
        agent_registry: "AgentRegistry" = None,
        model: str = "gpt-4o"
    ):
        self.config = config
        # Support both OpenAI client and LLMClient abstraction
        if isinstance(client, LLMClient):
            self.llm_client = client
            self.client = None  # Legacy OpenAI client not used
        else:
            self.client = client
            self.llm_client = None  # Use legacy OpenAI client
        self.tool_registry = tool_registry or {}
        self.agent_registry = agent_registry
        self.model = model
        self.trace = ExecutionTrace()
        self.node_id: Optional[str] = None
        self._event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    
    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI function definitions for available tools."""
        from .tools import TOOL_DEFINITIONS
        
        definitions = []
        for tool_name in self.config.tools:
            if tool_name in TOOL_DEFINITIONS:
                definitions.append(TOOL_DEFINITIONS[tool_name])
        
        # Add delegate_to_agent if this agent can delegate
        if self.config.can_delegate_to:
            definitions.append({
                "type": "function",
                "function": {
                    "name": "delegate_to_agent",
                    "description": f"Delegate a task to another specialist agent. Available agents: {', '.join(self.config.can_delegate_to)}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "agent_id": {
                                "type": "string",
                                "description": f"The ID of the agent to delegate to. Must be one of: {', '.join(self.config.can_delegate_to)}",
                                "enum": self.config.can_delegate_to
                            },
                            "task": {
                                "type": "string",
                                "description": "The specific task or question to delegate to the agent"
                            }
                        },
                        "required": ["agent_id", "task"]
                    }
                }
            })
        
        return definitions
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any], parent_node_id: str) -> str:
        """Execute a tool and record in trace."""
        from .tools import execute_tool
        
        # Add tool node to trace
        tool_node_id = self.trace.add_node(
            type="tool",
            name=tool_name,
            metadata={"arguments": arguments}
        )
        self.trace.add_edge(parent_node_id, tool_node_id, label="uses")
        
        # Execute the tool with timing
        from .tools.cache import tool_cache
        start_time = time.time()
        result = execute_tool(tool_name, arguments, self.tool_registry)
        execution_time = time.time() - start_time
        cache_hit = tool_cache.last_hit

        # Update tool node with result summary, full result, and execution time
        for node in self.trace.nodes:
            if node.id == tool_node_id:
                if not node.metadata:
                    node.metadata = {}
                node.metadata["result_preview"] = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                node.metadata["result"] = str(result)  # Store full result for visualizations
                node.metadata["execution_time"] = execution_time  # Store execution time in seconds
                node.metadata["cache_hit"] = cache_hit

        # Emit progress event after tool execution (for key findings)
        if hasattr(self, '_event_callback') and self._event_callback:
            # Create a summary of the tool result
            result_preview = str(result)[:150] + "..." if len(str(result)) > 150 else str(result)
            self._event_callback("progress_update", {
                "agent_name": self.config.name,
                "tool_name": tool_name,
                "message": f"Used {tool_name}: {result_preview}",
                "type": "tool_result"
            })

        # Emit trace update event
        if hasattr(self, '_event_callback') and self._event_callback:
            self._event_callback("trace_update", {
                "trace": self.trace.to_dict()
            })
        
        return result
    
    def _delegate_to_agent(self, agent_id: str, task: str, context: Dict[str, Any], parent_node_id: str, max_depth: int = 5, visited_agents: set = None) -> str:
        """Delegate a task to another agent."""
        if not self.agent_registry:
            return "Error: Agent registry not available for delegation"
        
        if agent_id not in self.config.can_delegate_to:
            return f"Error: Cannot delegate to {agent_id}. Allowed: {self.config.can_delegate_to}"
        
        # Check for circular dependencies
        visited_agents = visited_agents or set()
        if agent_id in visited_agents:
            return f"Error: Circular delegation detected. Agent {agent_id} was already called in this chain: {visited_agents}"
        
        # Check max depth
        if max_depth <= 0:
            return f"Error: Maximum delegation depth reached. Cannot delegate to {agent_id}"
        
        delegate_agent = self.agent_registry.get_agent(agent_id)
        if not delegate_agent:
            return f"Error: Agent {agent_id} not found"

        # Emit progress event before delegation
        if hasattr(self, '_event_callback') and self._event_callback:
            # Extract reasoning if present in task (look for common reasoning phrases)
            task_preview = task[:200] if len(task) <= 200 else task[:197] + "..."

            self._event_callback("progress_update", {
                "agent_name": self.config.name,
                "delegate_to": delegate_agent.config.name,
                "message": f"🎯 Delegating to **{delegate_agent.config.name}**\n\n{task_preview}",
                "type": "delegation",
                "tool_name": "delegate_to_agent"
            })

        # Execute the delegate agent (pass through event callback, reduce depth, track visited)
        event_callback = getattr(self, '_event_callback', None)
        new_visited = visited_agents | {agent_id}
        result, delegate_trace, delegate_llm_records = delegate_agent.execute(
            task,
            context,
            max_iterations=20,  # Increased from default 10 for more complex operations
            max_depth=max_depth - 1,
            visited_agents=new_visited,
            event_callback=event_callback
        )

        # Merge delegate's LLM call records into ours
        if delegate_llm_records:
            self._llm_call_records.extend(delegate_llm_records)

        # Merge the delegate's trace into ours
        if delegate_trace:
            # Find the delegate agent's main node and update its metadata with the task
            delegate_main_node = None
            for node in delegate_trace.nodes:
                if node.type == "agent":
                    delegate_main_node = node.id
                    # Update metadata to include the delegated task
                    if node.metadata:
                        node.metadata["delegated_task"] = task
                        node.metadata["delegated_from"] = self.config.id
                    else:
                        node.metadata = {
                            "delegated_task": task,
                            "delegated_from": self.config.id
                        }
                    break
            
            # Add edge from this agent to the delegate with task label
            if delegate_main_node:
                self.trace.add_edge(parent_node_id, delegate_main_node, label=f"delegates: {task[:50]}..." if len(task) > 50 else f"delegates: {task}")
            
            self.trace.merge(delegate_trace)
            
            # Emit trace update after delegation completes
            if hasattr(self, '_event_callback') and self._event_callback:
                self._event_callback("trace_update", {
                    "trace": self.trace.to_dict()
                })
        
        return result
    
    def execute(
        self,
        query: str,
        context: Dict[str, Any] = None,
        max_iterations: int = 20,
        max_depth: int = 5,
        visited_agents: set = None,
        event_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None
    ) -> tuple[str, ExecutionTrace, List["LLMCallRecord"]]:
        """
        Execute the agent with the given query.

        Returns:
            tuple: (response_text, execution_trace, llm_call_records)
        """
        context = context or {}
        self.trace = ExecutionTrace()
        self._llm_call_records: List[LLMCallRecord] = []
        self._event_callback = event_callback  # Store for use in _execute_tool
        self._max_depth = max_depth
        self._visited_agents = visited_agents or {self.config.id}  # Track this agent as visited
        
        # Track agent execution start time
        agent_start_time = time.time()
        
        # Add this agent as a node with query/task context
        self.node_id = self.trace.add_node(
            type="agent",
            name=self.config.name,
            metadata={
                "role": self.config.role,
                "query": query,  # Store the query/task this agent is handling
                "agent_id": self.config.id
            }
        )
        
        # Emit agent start event
        if event_callback:
            event_callback("agent_start", {
                "agent_id": self.config.id,
                "agent_name": self.config.name,
                "node_id": self.node_id,
                "query": query
            })
            event_callback("trace_update", {
                "trace": self.trace.to_dict()
            })
        
        # Build messages
        system_message = self._build_system_message(context)
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": query}
        ]
        
        # Get tool definitions
        tools = self._get_tool_definitions()
        
        # Iterative tool calling loop
        for iteration in range(max_iterations):
            # Call OpenAI
            response_kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
            }
            
            if tools:
                response_kwargs["tools"] = tools
                response_kwargs["tool_choice"] = "auto"
            
            # Use LLMClient abstraction if available, otherwise fall back to OpenAI client
            if self.llm_client:
                response = self.llm_client.chat_completions_create(
                    messages=messages,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    temperature=0.7
                )
            else:
                response = self.client.chat.completions.create(**response_kwargs)
            message = response.choices[0].message

            # Capture LLM call for prompt traceability
            response_tool_calls_data = None
            if message.tool_calls:
                response_tool_calls_data = [
                    {
                        "id": tc.id,
                        "type": getattr(tc, 'type', 'function'),
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in message.tool_calls
                ]
            self._llm_call_records.append(LLMCallRecord(
                agent_name=self.config.name,
                agent_id=self.config.id,
                model=self.model,
                iteration=iteration,
                messages=copy.deepcopy(messages),
                tools=copy.deepcopy(tools) if tools else None,
                response_content=message.content,
                response_tool_calls=response_tool_calls_data,
                timestamp=datetime.now().isoformat(),
            ))

            # Check if we need to call tools
            if message.tool_calls:
                # Add assistant message with tool calls
                # Convert to dict to avoid pydantic serialization issues
                message_dict = {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                }
                messages.append(message_dict)

                # Separate delegation calls from regular tool calls
                delegation_calls = []
                regular_calls = []
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    if function_name == "delegate_to_agent":
                        delegation_calls.append(tool_call)
                    else:
                        regular_calls.append(tool_call)

                # Run regular tool calls sequentially (may depend on each other)
                for tool_call in regular_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    result = self._execute_tool(function_name, arguments, self.node_id)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })
                    if event_callback:
                        event_callback("trace_update", {
                            "trace": self.trace.to_dict()
                        })

                # Run delegations in parallel when there are multiple
                if len(delegation_calls) > 1:
                    import concurrent.futures
                    current_visited = getattr(self, '_visited_agents', set())
                    current_depth = getattr(self, '_max_depth', 5)

                    def run_delegation(tc):
                        args = json.loads(tc.function.arguments)
                        result = self._delegate_to_agent(
                            args["agent_id"],
                            args["task"],
                            context,
                            self.node_id,
                            max_depth=current_depth,
                            visited_agents=current_visited
                        )
                        return tc.id, str(result)

                    with concurrent.futures.ThreadPoolExecutor(max_workers=len(delegation_calls)) as executor:
                        futures = {executor.submit(run_delegation, tc): tc for tc in delegation_calls}
                        delegation_results = {}
                        for future in concurrent.futures.as_completed(futures):
                            tc_id, result = future.result()
                            delegation_results[tc_id] = result
                            # Emit trace update as each delegation completes
                            if event_callback:
                                event_callback("trace_update", {
                                    "trace": self.trace.to_dict()
                                })

                    # Add results in original order
                    for tc in delegation_calls:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": delegation_results[tc.id]
                        })
                elif len(delegation_calls) == 1:
                    # Single delegation — run directly (no thread overhead)
                    tool_call = delegation_calls[0]
                    arguments = json.loads(tool_call.function.arguments)
                    current_visited = getattr(self, '_visited_agents', set())
                    current_depth = getattr(self, '_max_depth', 5)
                    result = self._delegate_to_agent(
                        arguments["agent_id"],
                        arguments["task"],
                        context,
                        self.node_id,
                        max_depth=current_depth,
                        visited_agents=current_visited
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })
                    if event_callback:
                        event_callback("trace_update", {
                            "trace": self.trace.to_dict()
                        })
            else:
                # No more tool calls - check if response contains ECharts config for visualizer tool nodes
                if message.content:
                    from ..llm.response_parser import extract_visualizations
                    visualizations = extract_visualizations(message.content)
                    if visualizations:
                        # Find visualizer tool nodes that don't have echarts_config yet
                        visualizer_nodes = [node for node in self.trace.nodes 
                                          if node.type == "tool" and node.name == "visualizer" 
                                          and not node.metadata.get("echarts_config")]
                        # Link visualizations to visualizer nodes
                        for i, viz in enumerate(visualizations):
                            if i < len(visualizer_nodes):
                                viz_node = visualizer_nodes[i]
                                if viz.get("echarts_config"):
                                    if not viz_node.metadata:
                                        viz_node.metadata = {}
                                    viz_node.metadata["echarts_config"] = viz["echarts_config"]
                                    viz_node.metadata["visualization_title"] = viz.get("title", "Visualization")
                                    viz_node.metadata["chart_type"] = viz.get("chart_type", "unknown")
                
                # Calculate agent execution time
                agent_execution_time = time.time() - agent_start_time
                
                # Update agent node metadata with execution time
                for node in self.trace.nodes:
                    if node.id == self.node_id:
                        if not node.metadata:
                            node.metadata = {}
                        node.metadata["execution_time"] = agent_execution_time
                        break
                
                # No more tool calls, return the response
                if event_callback:
                    event_callback("agent_complete", {
                        "agent_id": self.config.id,
                        "agent_name": self.config.name,
                        "response_preview": message.content[:200] + "..." if message.content and len(message.content) > 200 else message.content or "",
                        "execution_time": agent_execution_time
                    })
                    event_callback("trace_update", {
                        "trace": self.trace.to_dict()
                    })
                return message.content, self.trace, self._llm_call_records

        # Max iterations reached
        return "I apologize, but I've reached my processing limit. Please try rephrasing your question.", self.trace, self._llm_call_records
    
    def _build_system_message(self, context: Dict[str, Any]) -> str:
        """Build the system message with context."""
        from datetime import datetime
        
        parts = [self.config.system_prompt]
        
        # Add current date/time context
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.strftime("%B")
        current_date_str = current_date.strftime("%Y-%m-%d")
        parts.append(f"\n\nCURRENT DATE CONTEXT:\nToday's date is {current_date_str} ({current_month} {current_year}). When constructing search queries or referencing dates, use the current year ({current_year}) unless specifically asked about historical data. Always prioritize recent information when searching.")
        
        if context.get("organization"):
            parts.append(f"\n\nORGANIZATION CONTEXT:\n{context['organization']}")
        
        if context.get("conversation_history"):
            parts.append(f"\n\nCONVERSATION HISTORY:\n{context['conversation_history']}")

        if context.get("parent_analysis_context"):
            parts.append(
                f"\n\nPARENT ANALYSIS CONTEXT (this is a deep-dive follow-up question):\n"
                f"The user is asking a follow-up question that builds on a previous analysis. "
                f"Use the detailed findings below to provide deeper insights rather than starting from scratch. "
                f"Reference specific data points, specialist findings, and tool outputs from the parent analysis.\n"
                f"{context['parent_analysis_context']}"
            )

        if context.get("file_content"):
            parts.append(f"\n\nATTACHED FILE CONTENT:\n{context['file_content']}")
        
        # Add thread preferences if available
        thread_prefs = context.get("thread_preferences", {})
        if thread_prefs:
            pref_parts = []
            
            # Budget focus
            budget_focus = thread_prefs.get("budget_focus", 0.5)
            if budget_focus < 0.3:
                pref_parts.append("BUDGET FOCUS: Very budget-conscious - prioritize cost efficiency and minimal spending")
            elif budget_focus < 0.7:
                pref_parts.append("BUDGET FOCUS: Balanced approach between cost and outcomes")
            else:
                pref_parts.append("BUDGET FOCUS: Very outcome-conscious - prioritize results over cost")
            
            # Response length
            response_length = thread_prefs.get("response_length", 0.5)
            if response_length < 0.3:
                pref_parts.append("RESPONSE LENGTH: Brief - provide concise, one-sentence answers when possible")
            elif response_length < 0.7:
                pref_parts.append("RESPONSE LENGTH: Moderate detail - provide balanced explanations")
            else:
                pref_parts.append("RESPONSE LENGTH: Comprehensive - provide full analysis including text summaries, detailed explanations, action plans, visualizations, charts, and all relevant modalities")
            
            # Creativity
            creativity = thread_prefs.get("creativity", 0.5)
            if creativity < 0.3:
                pref_parts.append("CREATIVITY: Off-the-shelf - use standard, proven approaches and conventional solutions")
            elif creativity < 0.7:
                pref_parts.append("CREATIVITY: Balanced - mix of standard and creative approaches")
            else:
                pref_parts.append("CREATIVITY: Innovative - explore creative, unconventional solutions and think outside the box")
            
            if pref_parts:
                parts.append(f"\n\nTHREAD PREFERENCES:\n" + "\n".join(pref_parts))

        # Add answer mode instructions
        answer_mode = context.get("answer_mode", "light")
        if answer_mode == "summary":
            parts.append(f"""

=== ANSWER MODE: SUMMARY (EXECUTIVE BRIEFING) ===
CRITICAL REQUIREMENTS - YOU MUST FOLLOW THESE EXACTLY:
1. LENGTH: Your FINAL response MUST be 2-3 short paragraphs ONLY (maximum 150 words total)
2. STYLE: Executive summary for busy C-level executives - get to the point immediately
3. CONTENT: Focus ONLY on:
   - The single most important conclusion or recommendation
   - 1-2 key supporting facts (no more)
   - One clear next action if applicable
4. SOURCES: Use extract_sources tool to cite 1-3 high-quality sources for critical claims. Quality matters more than hitting a specific number.
5. DELEGATION: Use MINIMAL delegation - only if absolutely critical data is missing
6. IMAGES: NO images unless absolutely essential to convey a key metric
7. AVOID: No background context, no detailed explanations, no comprehensive analysis
8. FORMAT: Short, punchy sentences. No lists, no extensive details.

Example good summary: "Based on market analysis, entering the Asian market now presents significant risk due to regulatory uncertainty [1]. Current cost projections show 40% over budget. Recommendation: Delay market entry 6 months while securing regulatory approvals and renegotiating supplier contracts to reduce costs by 25%."

THIS IS NON-NEGOTIABLE. If your response is longer than 150 words, you have failed.""")
        elif answer_mode == "extended":
            parts.append(f"""

=== ANSWER MODE: EXTENDED (COMPREHENSIVE ANALYSIS) ===
REQUIREMENTS - Provide thorough, detailed analysis:
1. LENGTH: Comprehensive response of 800-1200 words minimum
2. DEPTH: Include detailed examination of all relevant factors:
   - Multiple perspectives and viewpoints
   - Comprehensive data analysis
   - Thorough examination of trade-offs
   - Detailed risk assessment
   - In-depth context and background
3. SOURCES: Use extract_sources tool extensively - aim for 10-20 credible sources including:
   - Industry reports, academic research, case studies
   - Internal documents if relevant
   - Real-world examples with metrics
   - Cite frequently throughout (every major claim should be backed)
   - Use include_case_studies=True for extended mode
   - Quality over quantity - don't pad with weak sources
4. DELEGATION: Delegate to ALL relevant specialists to gather complete information
5. STRUCTURE: Use clear sections with headings
6. DATA: Include specific metrics, statistics, and supporting evidence
7. IMAGES: Generate visualizations to support your analysis - use charts, graphs, and diagrams
8. NUANCE: Explore complexity, edge cases, and contingencies

Provide the level of detail needed for a comprehensive strategic document or full report.""")
        elif answer_mode == "project_plan":
            parts.append(f"""

=== ANSWER MODE: PROJECT_PLAN (30-60-90 DAY STRATEGIC PLAN) ===
REQUIREMENTS - Structure your response as a 30-60-90 day strategic project plan:
1. FORMAT: Organize into three distinct phases:
   ## Day 1-30: Foundation Phase
   - Immediate priorities and quick wins
   - Foundation-building activities
   - Initial resource allocation
   - Key stakeholders to engage

   ## Day 31-60: Build Phase
   - Build on foundation work
   - Expand key initiatives
   - Measure and report early results
   - Adjust based on learnings

   ## Day 61-90: Scale Phase
   - Scale successful initiatives
   - Address any gaps identified
   - Establish long-term processes
   - Set up ongoing measurement

2. CONTENT: Each phase MUST include:
   - 3-5 specific, actionable milestones with deliverables
   - Success metrics and KPIs
   - Resource requirements
   - Dependencies and risks
   - Responsible parties/roles

3. SOURCES: Use extract_sources tool - aim for 8-10 sources focused on best practices, industry benchmarks, and implementation guides
4. DELEGATION: Focus on specialists who can provide actionable insights and implementation expertise
5. IMAGES: Use timeline/Gantt-style visualizations, milestone charts, or project roadmap graphics
6. AVOID: Vague objectives, unmeasurable goals, or activities without clear ownership

This plan should be immediately actionable - someone should be able to start executing on Day 1.""")
        elif answer_mode == "roadmap":
            parts.append(f"""

=== ANSWER MODE: ROADMAP (STRATEGIC FRAMEWORK + ROADMAP) ===
REQUIREMENTS - Provide strategic framework analysis combined with actionable roadmap:

PART 1 - FRAMEWORK ANALYSIS:
Apply relevant strategic frameworks to analyze the situation:
- Porter's Five Forces (competitive dynamics)
- SWOT Analysis (strengths, weaknesses, opportunities, threats)
- BCG Matrix (portfolio analysis if applicable)
- Ansoff Matrix (growth strategies)
- Value Chain Analysis (competitive advantages)
- Blue Ocean Strategy (market creation opportunities)

Select and apply the 2-3 most relevant frameworks for the specific question.

PART 2 - STRATEGIC ROADMAP:
Based on framework analysis, provide:
## Strategic Roadmap

### Phase 1 (Months 1-3): [Phase Name]
- Key initiatives and priorities
- Critical success factors
- Resource requirements

### Phase 2 (Months 4-6): [Phase Name]
- Build-out initiatives
- Scaling activities
- Milestone checkpoints

### Phase 3 (Months 7-12): [Phase Name]
- Long-term strategic moves
- Competitive positioning
- Sustainability measures

Include:
- Dependencies between phases
- Critical path items
- Decision points and gates
- Risk mitigation strategies

3. SOURCES: Use extract_sources tool - aim for 12-15 strategic sources including academic research, industry reports, and case studies
4. DELEGATION: Comprehensive delegation to all relevant specialists for thorough analysis
5. IMAGES: Use strategic framework diagrams, roadmap timelines, and positioning maps
6. DEPTH: This is a strategic planning document - be thorough and analytical

The output should serve as a strategic planning document that combines rigorous analysis with actionable implementation guidance.""")
        else:  # light (default) - One-Pager/Memo
            parts.append(f"""

=== ANSWER MODE: LIGHT (ONE-PAGER/MEMO) ===
REQUIREMENTS - Provide balanced, focused analysis in memo format:
1. LENGTH: 300-500 words - concise but complete, fits on one page
2. CONTENT: Include:
   - Clear answer to the question
   - 3-5 key supporting points with brief evidence
   - Relevant context where needed
   - Practical implications or next steps
3. SOURCES: Use extract_sources tool to back up key claims - aim for 5-8 quality sources:
   - Cite important statistics, benchmarks, and assertions
   - Include internal documents if user provided files
   - Mix of source types (industry reports, news, data)
   - Don't over-cite obvious facts - focus on substantive claims
   - Quality over quantity - 5 good sources better than 8 weak ones
4. DELEGATION: Delegate to key specialists for important information
5. IMAGES: Use visualizations selectively - only when they clarify complex data
6. AVOID: Excessive detail, comprehensive lists, exhaustive analysis

Strike a balance between being thorough and being concise. Provide enough detail to be useful without overwhelming the reader.""")

        # Add custom agent descriptions so the director knows about dynamically-added specialists
        if context.get("custom_agents_info"):
            parts.append(f"\n\nADDITIONAL CUSTOM SPECIALISTS AVAILABLE:\n{context['custom_agents_info']}\n\nYou can delegate tasks to these custom specialists just like built-in agents using the delegate_to_agent tool.")

        return "\n".join(parts)
