from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Optional, List
from .. import models, schemas

def create_custom_agent(
    db: Session,
    agent: schemas.CustomAgentCreate,
    user_id: int
) -> models.CustomAgent:
    """Create a new custom agent for a user"""
    db_agent = models.CustomAgent(
        user_id=user_id,
        name=agent.name,
        description=agent.description,
        role=agent.role,
        system_prompt=agent.system_prompt,
        tools=agent.tools or [],
        can_delegate_to=agent.can_delegate_to or [],
        model=agent.model,
        use_cases=agent.use_cases or [],
        style=agent.style,
        is_agentic=agent.is_agentic or False,
        organization_id=agent.organization_id,
        shared_with_org=agent.shared_with_org or False,
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

def get_custom_agent(db: Session, agent_id: int, user_id: int) -> Optional[models.CustomAgent]:
    """Get a custom agent by ID (only if owned by user)"""
    return db.query(models.CustomAgent).filter(
        models.CustomAgent.id == agent_id,
        models.CustomAgent.user_id == user_id
    ).first()

def get_custom_agents_by_user(db: Session, user_id: int) -> List[models.CustomAgent]:
    """Get all custom agents for a user"""
    return db.query(models.CustomAgent).filter(
        models.CustomAgent.user_id == user_id
    ).order_by(models.CustomAgent.created_at.desc()).all()

def get_custom_agents_for_crew(
    db: Session,
    user_id: int,
    organization_id: int
) -> List[models.CustomAgent]:
    """Get all agentic custom agents available to a user in an org context.

    Returns agents that are marked as agentic AND are either:
    1. Owned by the user, OR
    2. Shared with the organization
    """
    return db.query(models.CustomAgent).filter(
        models.CustomAgent.is_agentic == True,
        or_(
            models.CustomAgent.user_id == user_id,
            and_(
                models.CustomAgent.organization_id == organization_id,
                models.CustomAgent.shared_with_org == True
            )
        )
    ).all()

def update_custom_agent(
    db: Session,
    agent_id: int,
    user_id: int,
    agent_update: schemas.CustomAgentUpdate
) -> Optional[models.CustomAgent]:
    """Update a custom agent (only if owned by user)"""
    db_agent = get_custom_agent(db, agent_id, user_id)
    if not db_agent:
        return None

    update_data = agent_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_agent, field, value)

    db.commit()
    db.refresh(db_agent)
    return db_agent

def delete_custom_agent(db: Session, agent_id: int, user_id: int) -> bool:
    """Delete a custom agent (only if owned by user)"""
    db_agent = get_custom_agent(db, agent_id, user_id)
    if not db_agent:
        return False

    db.delete(db_agent)
    db.commit()
    return True
