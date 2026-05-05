"""
Agent registry - loads agents from YAML configs and provides lookup.
"""

import yaml
from pathlib import Path
from typing import Dict, Optional, Union
from .base import Agent, AgentConfig
from openai import OpenAI
from ..llm_client import LLMClient


class AgentRegistry:
    """Registry for managing agents loaded from YAML configs."""
    
    def __init__(
        self, 
        config_dir: Path, 
        client: Union[OpenAI, LLMClient], 
        tool_registry: Dict = None,
        default_model: Optional[str] = None
    ):
        """
        Initialize agent registry.
        
        Args:
            config_dir: Directory containing agent YAML configs
            client: Default LLM client (used if agent doesn't specify model)
            tool_registry: Registry of available tools
            default_model: Default model to use if agent doesn't specify (falls back to client's model)
        """
        self.config_dir = config_dir
        self.default_client = client
        self.tool_registry = tool_registry or {}
        self.agents: Dict[str, Agent] = {}
        # Get default model from client if it's an LLMClient, otherwise use provided default
        if isinstance(client, LLMClient):
            self.default_model = default_model or client.model
        else:
            self.default_model = default_model or "gemini-3-flash-preview"
        self._load_agents()
    
    def _load_common_prompts(self) -> Dict[str, str]:
        """Load common prompt sections from _common_prompts.yaml if it exists."""
        common_file = self.config_dir / "_common_prompts.yaml"
        if common_file.exists():
            try:
                with open(common_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load common prompts: {e}")
        return {}
    
    def _load_agents(self):
        """Load all agents from YAML config files."""
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Agent config directory not found: {self.config_dir}")
        
        # Load common prompts once
        common_prompts = self._load_common_prompts()
        data_driven_base = common_prompts.get('data_driven_decision_making_base', '')
        
        for yaml_file in self.config_dir.glob("*.yaml"):
            # Skip common prompts file and any file starting with _
            if yaml_file.name.startswith('_'):
                continue
                
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                # Inject common data-driven section if base exists
                system_prompt = config_data['system_prompt']
                if data_driven_base:
                    # Check if agent has agent-specific data extraction instruction
                    agent_specific = config_data.get('data_extraction_note', '')
                    
                    # Build the complete section
                    agent_specific = agent_specific.strip() if agent_specific else ''
                    if agent_specific:
                        data_driven_section = f"{data_driven_base}\n  - {agent_specific}"
                    else:
                        data_driven_section = data_driven_base
                    
                    # Remove existing data-driven section if present (to avoid duplication)
                    import re
                    if 'CRITICAL: DATA-DRIVEN DECISION MAKING' in system_prompt:
                        # Find and remove the old section
                        pattern = r'CRITICAL: DATA-DRIVEN DECISION MAKING.*?(?=\n\n|\n  [A-Z]|\Z)'
                        system_prompt = re.sub(pattern, '', system_prompt, flags=re.DOTALL)
                        # Clean up extra blank lines
                        system_prompt = re.sub(r'\n\n\n+', '\n\n', system_prompt)
                    
                    # Insert after first line (agent introduction)
                    lines = system_prompt.split('\n')
                    if len(lines) > 1:
                        # Find first non-empty line after the intro
                        insert_pos = 1
                        for i, line in enumerate(lines[1:], 1):
                            if line.strip() and not line.strip().startswith('Your') and not line.strip().startswith('IMPORTANT'):
                                insert_pos = i + 1
                                break
                        # Insert blank line and data-driven section
                        lines.insert(insert_pos, '')
                        lines.insert(insert_pos + 1, data_driven_section)
                        system_prompt = '\n'.join(lines)
                    else:
                        system_prompt = f"{system_prompt}\n\n{data_driven_section}"
                
                config = AgentConfig(
                    id=config_data['id'],
                    name=config_data['name'],
                    role=config_data['role'],
                    tools=config_data.get('tools', []),
                    can_delegate_to=config_data.get('can_delegate_to', []),
                    system_prompt=system_prompt,
                    model=config_data.get('model')  # Optional per-agent model override
                )
                
                # Determine which client/model to use for this agent
                # Priority: agent config model > default model
                agent_model = config.model or self.default_model
                
                # Create LLMClient for this agent
                # If agent specifies a model or default_client is not an LLMClient, create new client
                if config.model or not isinstance(self.default_client, LLMClient):
                    from ..llm_client import get_llm_client
                    agent_client = get_llm_client(model=agent_model)
                elif agent_model == self.default_model:
                    # Use default client if model matches and it's an LLMClient
                    agent_client = self.default_client
                else:
                    # Model changed, create new client
                    from ..llm_client import get_llm_client
                    agent_client = get_llm_client(model=agent_model)
                
                agent = Agent(
                    config=config,
                    client=agent_client,
                    tool_registry=self.tool_registry,
                    agent_registry=self,
                    model=agent_model
                )
                
                self.agents[config.id] = agent
                
            except Exception as e:
                print(f"Error loading agent from {yaml_file}: {e}")
                continue
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def get_all_agents(self) -> Dict[str, Agent]:
        """Get all registered agents."""
        return self.agents.copy()

    def get_director(self) -> Optional[Agent]:
        """Get the Strategic Director agent."""
        return self.agents.get('director')

    def register_custom_agent(self, custom_agent_record) -> Optional[Agent]:
        """Register a custom agent from a database CustomAgent record.

        Converts a DB CustomAgent into an AgentConfig + Agent instance
        and adds it to the registry.
        """
        agent_id = f"custom_{custom_agent_record.id}"

        # Skip if already registered
        if agent_id in self.agents:
            return self.agents[agent_id]

        config = AgentConfig(
            id=agent_id,
            name=custom_agent_record.name,
            role=custom_agent_record.role or custom_agent_record.description or "",
            tools=custom_agent_record.tools or [],
            can_delegate_to=custom_agent_record.can_delegate_to or [],
            system_prompt=custom_agent_record.system_prompt,
            model=custom_agent_record.model,
        )

        # Determine client/model
        agent_model = config.model or self.default_model
        from ..llm_client import get_llm_client
        agent_client = get_llm_client(model=agent_model)

        agent = Agent(
            config=config,
            client=agent_client,
            tool_registry=self.tool_registry,
            agent_registry=self,
            model=agent_model,
        )

        self.agents[agent_id] = agent
        return agent

    def get_filtered_registry(self, allowed_agent_ids: list = None) -> "AgentRegistry":
        """Return a view of this registry filtered to only the specified agent IDs.

        If allowed_agent_ids is None, returns self (all agents).
        The director and synthesizer are always included as infrastructure agents.
        """
        if allowed_agent_ids is None:
            return self

        # Always include infrastructure agents
        infrastructure_ids = {"director", "synthesizer"}
        allowed = set(allowed_agent_ids) | infrastructure_ids

        # Create a shallow copy with filtered agents
        filtered = AgentRegistry.__new__(AgentRegistry)
        filtered.config_dir = self.config_dir
        filtered.default_client = self.default_client
        filtered.tool_registry = self.tool_registry
        filtered.default_model = self.default_model
        filtered.agents = {
            aid: agent for aid, agent in self.agents.items()
            if aid in allowed
        }

        # Update agent_registry reference on all agents so delegation resolves within the filtered set
        for agent in filtered.agents.values():
            agent.agent_registry = filtered

        return filtered
