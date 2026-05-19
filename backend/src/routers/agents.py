from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pathlib import Path
import os

from openai import OpenAI

from ..database import get_db
from ..api_auth import authenticated_user_id
from .. import schemas, crud
from ..agents import AgentRegistry

router = APIRouter(tags=["agents"])


def _validate_agent_tools(tools: Optional[list[str]]) -> None:
    """Validate that tool IDs reference real tools."""
    if not tools:
        return
    from ..agents.tools import TOOL_IMPLEMENTATIONS
    invalid_tools = [t for t in tools if t not in TOOL_IMPLEMENTATIONS]
    if invalid_tools:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tool IDs: {invalid_tools}. Available: {list(TOOL_IMPLEMENTATIONS.keys())}"
        )


@router.get("/api/tools")
async def get_tools():
    """Get all available tools in the system."""
    from ..agents.tools import TOOL_DEFINITIONS

    tools = []
    for tool_id, tool_def in TOOL_DEFINITIONS.items():
        tools.append({
            "id": tool_id,
            "name": tool_def["function"]["name"],
            "description": tool_def["function"]["description"],
            "parameters": tool_def["function"].get("parameters", {})
        })

    return {"tools": tools}


@router.get("/api/agents", response_model=schemas.AgentRegistryResponse)
async def get_agents(
    user_id: int = Depends(authenticated_user_id),
    db: Session = Depends(get_db)
):
    """Get all available agent/prompt systems (built-in + the authenticated user's custom agents)"""
    agents = []

    # Load agents from YAML configs
    config_dir = Path(__file__).parent.parent / "agents" / "config"
    if config_dir.exists():
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        registry = AgentRegistry(config_dir, client, tool_registry={})

        for agent_id, agent in registry.get_all_agents().items():
            agents.append(
                schemas.AgentInfo(
                    id=agent_id,
                    name=agent.config.name,
                    description=agent.config.role,
                    use_cases=[],
                    style="",
                    system_prompt=agent.config.system_prompt,
                    is_custom=False,
                    user_id=None,
                    tools=agent.config.tools,
                    can_delegate_to=agent.config.can_delegate_to,
                    role=agent.config.role,
                    is_agentic=True,  # Built-in agents are always agentic
                )
            )

    # Add user's custom agents if user_id is provided
    if user_id:
        custom_agents = crud.get_custom_agents_by_user(db, user_id)
        for custom_agent in custom_agents:
            agents.append(
                schemas.AgentInfo(
                    id=f"custom_{custom_agent.id}",
                    name=custom_agent.name,
                    description=custom_agent.description or "",
                    use_cases=custom_agent.use_cases or [],
                    style=custom_agent.style or "",
                    system_prompt=custom_agent.system_prompt,
                    is_custom=True,
                    user_id=custom_agent.user_id,
                    tools=custom_agent.tools or [],
                    can_delegate_to=custom_agent.can_delegate_to or [],
                    role=custom_agent.role or custom_agent.description or "",
                    is_agentic=custom_agent.is_agentic,
                    organization_id=custom_agent.organization_id,
                    shared_with_org=custom_agent.shared_with_org,
                )
            )

    return schemas.AgentRegistryResponse(agents=agents)


# Custom Agent endpoints
@router.post("/api/agents/custom", response_model=schemas.CustomAgentResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_agent_endpoint(
    agent: schemas.CustomAgentCreate,
    user_id: int = Depends(authenticated_user_id),
    db: Session = Depends(get_db)
):
    """Create a new custom agent"""
    _validate_agent_tools(agent.tools)
    # If agent is scoped to an org, verify user has write access
    if agent.organization_id:
        if not crud.check_org_permission(db, agent.organization_id, user_id, require_write=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have write access to this organization"
            )
    db_agent = crud.create_custom_agent(db, agent, user_id)
    return db_agent


@router.get("/api/agents/custom", response_model=List[schemas.CustomAgentResponse])
async def get_custom_agents_endpoint(
    user_id: int = Depends(authenticated_user_id),
    db: Session = Depends(get_db)
):
    """Get all custom agents for a user"""
    agents = crud.get_custom_agents_by_user(db, user_id)
    return agents


@router.get("/api/agents/custom/{agent_id}", response_model=schemas.CustomAgentResponse)
async def get_custom_agent_endpoint(
    agent_id: int,
    user_id: int = Depends(authenticated_user_id),
    db: Session = Depends(get_db)
):
    """Get a specific custom agent"""
    agent = crud.get_custom_agent(db, agent_id, user_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom agent not found"
        )
    return agent


@router.put("/api/agents/custom/{agent_id}", response_model=schemas.CustomAgentResponse)
async def update_custom_agent_endpoint(
    agent_id: int,
    agent_update: schemas.CustomAgentUpdate,
    user_id: int = Depends(authenticated_user_id),
    db: Session = Depends(get_db)
):
    """Update a custom agent"""
    _validate_agent_tools(agent_update.tools)
    agent = crud.update_custom_agent(db, agent_id, user_id, agent_update)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom agent not found"
        )
    return agent


@router.delete("/api/agents/custom/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_agent_endpoint(
    agent_id: int,
    user_id: int = Depends(authenticated_user_id),
    db: Session = Depends(get_db)
):
    """Delete a custom agent"""
    success = crud.delete_custom_agent(db, agent_id, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom agent not found"
        )
    return None
