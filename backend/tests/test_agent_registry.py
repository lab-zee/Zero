"""Tests for agent registry and crew loading from YAML."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.agents import AgentRegistry, Crew, create_agent_registry
from src.agent_paths import (
    get_agent_config_dir,
    get_agent_plugins_dirs,
    should_inject_common_prompts,
)

FIXTURE_CREW = Path(__file__).parent / "fixtures" / "minimal_crew" / "agents"


@pytest.fixture
def mock_llm_client():
    client = MagicMock()
    client.model = "gemini-3-flash-preview"
    return client


class TestAgentPaths:
    def test_default_config_dir(self, monkeypatch):
        monkeypatch.delenv("AGENT_CONFIG_DIR", raising=False)
        config_dir = get_agent_config_dir()
        assert config_dir.name == "config"
        assert config_dir.parent.name == "agents"

    def test_override_config_dir(self, monkeypatch):
        monkeypatch.setenv("AGENT_CONFIG_DIR", str(FIXTURE_CREW))
        assert get_agent_config_dir() == FIXTURE_CREW.resolve()

    def test_inject_common_prompts_flag(self, monkeypatch):
        monkeypatch.setenv("INJECT_COMMON_PROMPTS", "false")
        assert should_inject_common_prompts() is False
        monkeypatch.setenv("INJECT_COMMON_PROMPTS", "true")
        assert should_inject_common_prompts() is True

    def test_plugins_dirs_include_builtin(self):
        dirs = get_agent_plugins_dirs()
        assert any(d.name == "plugins" for d in dirs)


class TestAgentRegistry:
    def test_loads_fixture_crew(self, mock_llm_client):
        registry = AgentRegistry(
            FIXTURE_CREW,
            mock_llm_client,
            inject_common_prompts=False,
        )
        assert "director" in registry.agents
        assert "synthesizer" in registry.agents
        assert registry.get_director() is not None

    def test_skips_common_prompt_injection_when_disabled(self, mock_llm_client, tmp_path):
        agent_file = tmp_path / "specialist.yaml"
        agent_file.write_text(
            "id: specialist\n"
            "name: Specialist\n"
            "role: Test\n"
            "tools: []\n"
            "can_delegate_to: []\n"
            "system_prompt: |\n  Original prompt only.\n",
            encoding="utf-8",
        )
        common = tmp_path / "_common_prompts.yaml"
        common.write_text(
            "data_driven_decision_making_base: CRITICAL INJECTED SECTION\n",
            encoding="utf-8",
        )

        registry = AgentRegistry(
            tmp_path,
            mock_llm_client,
            inject_common_prompts=False,
        )
        prompt = registry.agents["specialist"].config.system_prompt
        assert "CRITICAL INJECTED SECTION" not in prompt
        assert "Original prompt only." in prompt

    def test_create_agent_registry_uses_env(self, mock_llm_client, monkeypatch):
        monkeypatch.setenv("AGENT_CONFIG_DIR", str(FIXTURE_CREW))
        monkeypatch.setenv("INJECT_COMMON_PROMPTS", "false")
        registry = create_agent_registry(mock_llm_client)
        assert "director" in registry.agents


class TestCrew:
    def test_crew_requires_director(self, mock_llm_client):
        registry = AgentRegistry(
            FIXTURE_CREW,
            mock_llm_client,
            inject_common_prompts=False,
        )
        crew = Crew(registry)
        assert crew.director is not None
        assert crew.director.config.id == "director"

    def test_crew_raises_without_director(self, mock_llm_client, tmp_path):
        (tmp_path / "synthesizer.yaml").write_text(
            FIXTURE_CREW.joinpath("synthesizer.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        registry = AgentRegistry(tmp_path, mock_llm_client, inject_common_prompts=False)
        with pytest.raises(ValueError, match="Strategic Director"):
            Crew(registry)


class TestDinnerPlanningCrew:
    """Optional integration against a real CrewDefine output if present locally."""

    CREW_PATH = (
        Path(__file__).resolve().parents[2]
        / "CrewDefine"
        / "crews"
        / "dinner-planning-crew"
        / "agents"
    )

    @pytest.mark.skipif(
        not CREW_PATH.is_dir(),
        reason="CrewDefine dinner-planning-crew not found beside Zero repo",
    )
    def test_loads_dinner_planning_crew(self, mock_llm_client):
        registry = AgentRegistry(
            self.CREW_PATH,
            mock_llm_client,
            inject_common_prompts=False,
        )
        assert registry.get_director() is not None
        assert "synthesizer" in registry.agents
        assert len(registry.agents) >= 4
