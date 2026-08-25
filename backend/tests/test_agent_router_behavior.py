"""Behavioral tests for crew/tool discovery and custom-agent router decisions."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src import agent_paths, llm_client, schemas
from src.agents import crew_manifest
from src.agents import tools as agent_tools
from src.routers import agents as router


@pytest.mark.asyncio
async def test_active_crew_and_tool_catalog(monkeypatch):
    manifest = MagicMock()
    manifest.to_api_dict.return_value = {"name": "crew"}
    monkeypatch.setattr(crew_manifest, "get_crew_manifest", lambda: manifest)
    assert await router.get_active_crew() == {"name": "crew"}

    monkeypatch.setattr(
        agent_tools,
        "TOOL_DEFINITIONS",
        {
            "lookup": {
                "function": {
                    "name": "lookup",
                    "description": "Find evidence",
                    "parameters": {"type": "object"},
                }
            }
        },
    )
    assert await router.get_tools() == {
        "tools": [
            {
                "id": "lookup",
                "name": "lookup",
                "description": "Find evidence",
                "parameters": {"type": "object"},
            }
        ]
    }


def test_validate_agent_tools_accepts_known_and_rejects_unknown(monkeypatch):
    monkeypatch.setattr(agent_tools, "TOOL_IMPLEMENTATIONS", {"calculator": object()})
    router._validate_agent_tools(None)
    router._validate_agent_tools(["calculator"])
    with pytest.raises(HTTPException) as exc:
        router._validate_agent_tools(["missing"])
    assert exc.value.status_code == 400
    assert "missing" in exc.value.detail


@pytest.mark.asyncio
async def test_get_agents_combines_builtin_and_custom(monkeypatch, tmp_path):
    monkeypatch.setattr(agent_paths, "get_agent_config_dir", lambda: tmp_path)
    monkeypatch.setattr(llm_client, "missing_chat_api_key_message", lambda: None)
    monkeypatch.setattr(llm_client, "get_llm_client", lambda: "client")
    builtin = SimpleNamespace(
        config=SimpleNamespace(
            name="Director",
            role="Coordinates",
            system_prompt="Direct",
            tools=["calculator"],
            can_delegate_to=["synthesizer"],
        )
    )
    registry = SimpleNamespace(get_all_agents=lambda: {"director": builtin})
    monkeypatch.setattr(router, "create_agent_registry", lambda *_args, **_kwargs: registry)
    custom = SimpleNamespace(
        id=9,
        name="Custom",
        description=None,
        use_cases=None,
        style=None,
        system_prompt="Custom",
        user_id=2,
        tools=None,
        can_delegate_to=None,
        role=None,
        is_agentic=True,
        organization_id=3,
        shared_with_org=True,
    )
    monkeypatch.setattr(
        router.crud,
        "get_custom_agents_by_user",
        lambda _db, _user_id: [custom],
    )

    result = await router.get_agents(user_id=2, db=object())

    assert [agent.id for agent in result.agents] == ["director", "custom_9"]
    assert result.agents[0].is_custom is False
    assert result.agents[1].role == ""


@pytest.mark.asyncio
async def test_get_agents_reports_missing_provider_key(monkeypatch, tmp_path):
    monkeypatch.setattr(agent_paths, "get_agent_config_dir", lambda: tmp_path)
    monkeypatch.setattr(
        llm_client,
        "missing_chat_api_key_message",
        lambda: "Gemini API key not configured",
    )
    with pytest.raises(HTTPException) as exc:
        await router.get_agents(user_id=2, db=object())
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_custom_agent_create_enforces_org_write_access(monkeypatch):
    create = schemas.CustomAgentCreate(
        name="Custom",
        system_prompt="Prompt",
        tools=[],
        organization_id=3,
    )
    monkeypatch.setattr(
        router.crud,
        "check_org_permission",
        lambda *_args, **_kwargs: False,
    )
    with pytest.raises(HTTPException) as exc:
        await router.create_custom_agent_endpoint(create, user_id=2, db=object())
    assert exc.value.status_code == 403

    stored = object()
    monkeypatch.setattr(
        router.crud,
        "check_org_permission",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(router.crud, "create_custom_agent", lambda *_args: stored)
    assert await router.create_custom_agent_endpoint(create, user_id=2, db=object()) is stored


@pytest.mark.asyncio
async def test_custom_agent_read_update_delete_success_and_not_found(monkeypatch):
    stored = object()
    monkeypatch.setattr(
        router.crud,
        "get_custom_agents_by_user",
        lambda _db, _user_id: [stored],
    )
    assert await router.get_custom_agents_endpoint(user_id=2, db=object()) == [stored]

    monkeypatch.setattr(
        router.crud,
        "get_custom_agent",
        lambda *_args: stored,
    )
    assert await router.get_custom_agent_endpoint(1, user_id=2, db=object()) is stored
    monkeypatch.setattr(router.crud, "get_custom_agent", lambda *_args: None)
    with pytest.raises(HTTPException) as exc:
        await router.get_custom_agent_endpoint(1, user_id=2, db=object())
    assert exc.value.status_code == 404

    update = schemas.CustomAgentUpdate(name="Updated", tools=[])
    monkeypatch.setattr(
        router.crud,
        "update_custom_agent",
        lambda *_args: stored,
    )
    assert await router.update_custom_agent_endpoint(1, update, user_id=2, db=object()) is stored
    monkeypatch.setattr(router.crud, "update_custom_agent", lambda *_args: None)
    with pytest.raises(HTTPException) as exc:
        await router.update_custom_agent_endpoint(1, update, user_id=2, db=object())
    assert exc.value.status_code == 404

    monkeypatch.setattr(router.crud, "delete_custom_agent", lambda *_args: True)
    assert await router.delete_custom_agent_endpoint(1, user_id=2, db=object()) is None
    monkeypatch.setattr(router.crud, "delete_custom_agent", lambda *_args: False)
    with pytest.raises(HTTPException) as exc:
        await router.delete_custom_agent_endpoint(1, user_id=2, db=object())
    assert exc.value.status_code == 404
