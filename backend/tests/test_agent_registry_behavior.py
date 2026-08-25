"""Registry loading, model selection, manifest, custom-agent, and filtering behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import yaml

from src.agents import registry as module
from src.llm_client import LLMClient


def _llm(model: str = "gemini-default") -> LLMClient:
    client = object.__new__(LLMClient)
    client.model = model
    return client


def _write_agent(path, agent_id: str, **overrides):
    document = {
        "id": agent_id,
        "name": agent_id.title(),
        "role": f"{agent_id} role",
        "tools": [],
        "can_delegate_to": [],
        "system_prompt": "Intro line\nYour mission\nPerform evidence-based analysis.",
        **overrides,
    }
    (path / f"{agent_id}.yaml").write_text(yaml.safe_dump(document), encoding="utf-8")


def test_registry_loads_agents_injects_common_prompts_and_applies_manifest(
    monkeypatch,
    tmp_path,
):
    (tmp_path / "_common_prompts.yaml").write_text(
        yaml.safe_dump(
            {
                "data_driven_decision_making_base": (
                    "CRITICAL: DATA-DRIVEN DECISION MAKING\nUse evidence."
                )
            }
        ),
        encoding="utf-8",
    )
    _write_agent(
        tmp_path,
        "director",
        data_extraction_note="Extract revenue.",
        system_prompt=(
            "Intro\nCRITICAL: DATA-DRIVEN DECISION MAKING\nOld text\n\n"
            "Your mission\nAnalyze."
        ),
    )
    _write_agent(tmp_path, "synthesizer")
    (tmp_path / "crew.yaml").write_text(
        yaml.safe_dump(
            {
                "output_composition": {
                    "synthesizer_tools": ["calculator", "visualizer"]
                }
            }
        ),
        encoding="utf-8",
    )
    created: list[SimpleNamespace] = []

    def agent_factory(**kwargs):
        agent = SimpleNamespace(**kwargs)
        created.append(agent)
        return agent

    monkeypatch.setattr(module, "Agent", agent_factory)
    client = _llm()
    registry = module.AgentRegistry(tmp_path, client, tool_registry={"calculator": object()})

    assert set(registry.get_all_agents()) == {"director", "synthesizer"}
    director = registry.get_director()
    assert director.client is client
    assert director.config.system_prompt.count("CRITICAL: DATA-DRIVEN") == 1
    assert "Extract revenue." in director.config.system_prompt
    assert registry.get_agent("missing") is None
    assert registry.get_agent("synthesizer").config.tools == ["calculator", "visualizer"]


def test_registry_uses_agent_model_and_non_llm_default_client(monkeypatch, tmp_path):
    _write_agent(tmp_path, "director", model="gpt-custom")
    created_clients = MagicMock(return_value="per-agent-client")
    monkeypatch.setattr("src.llm_client.get_llm_client", created_clients)
    monkeypatch.setattr(
        module,
        "Agent",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )

    registry = module.AgentRegistry(
        tmp_path,
        object(),
        default_model="fallback-model",
        inject_common_prompts=False,
    )

    assert registry.default_model == "fallback-model"
    assert registry.get_director().client == "per-agent-client"
    created_clients.assert_called_once_with(model="gpt-custom")


def test_registry_reports_missing_directory_and_invalid_yaml(monkeypatch, tmp_path):
    with pytest.raises(FileNotFoundError):
        module.AgentRegistry(tmp_path / "missing", _llm())

    (tmp_path / "broken.yaml").write_text("id: [", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Error loading agent"):
        module.AgentRegistry(tmp_path, _llm())


def test_common_prompt_loader_tolerates_parse_error(monkeypatch, tmp_path):
    _write_agent(tmp_path, "director")
    common = tmp_path / "_common_prompts.yaml"
    common.write_text("broken: [", encoding="utf-8")
    monkeypatch.setattr(
        module,
        "Agent",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    registry = module.AgentRegistry(tmp_path, _llm())
    assert registry.get_director().config.id == "director"


def test_register_custom_agent_is_idempotent_and_uses_model(monkeypatch, tmp_path):
    _write_agent(tmp_path, "director")
    monkeypatch.setattr(
        module,
        "Agent",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    registry = module.AgentRegistry(tmp_path, _llm("default"))
    get_client = MagicMock(return_value="custom-client")
    monkeypatch.setattr("src.llm_client.get_llm_client", get_client)
    record = SimpleNamespace(
        id=42,
        name="Custom",
        role=None,
        description="Custom role",
        tools=["calculator"],
        can_delegate_to=["director"],
        system_prompt="Custom system prompt",
        model="gpt-custom",
    )

    first = registry.register_custom_agent(record)
    second = registry.register_custom_agent(record)

    assert first is second
    assert first.config.id == "custom_42"
    assert first.config.role == "Custom role"
    assert first.client == "custom-client"
    get_client.assert_called_once_with(model="gpt-custom")


def test_filtered_registry_keeps_infrastructure_and_rebinds_agents(monkeypatch, tmp_path):
    for agent_id in ("director", "synthesizer", "risk", "market"):
        _write_agent(tmp_path, agent_id)
    monkeypatch.setattr(
        module,
        "Agent",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    registry = module.AgentRegistry(tmp_path, _llm())

    assert registry.get_filtered_registry(None) is registry
    filtered = registry.get_filtered_registry(["risk"])

    assert set(filtered.agents) == {"director", "synthesizer", "risk"}
    assert set(registry.agents) == {"director", "synthesizer", "risk", "market"}
    assert all(agent.agent_registry is filtered for agent in filtered.agents.values())
