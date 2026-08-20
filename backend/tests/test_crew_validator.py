"""Tests for crew directory validation."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import pytest
import yaml

from src.agents.crew_validator import (
    CrewValidationError,
    validate_crew_directory,
    validate_or_raise,
)

FIXTURE_CREW = Path(__file__).parent / "fixtures" / "minimal_crew"
VALID_AGENTS = FIXTURE_CREW / "agents"


def _write_agent(tmp_path: Path, agent_id: str, delegates: Optional[List[str]] = None) -> Path:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    doc = {
        "id": agent_id,
        "name": agent_id.replace("_", " ").title(),
        "role": f"Role for {agent_id} in validation tests",
        "tools": [],
        "can_delegate_to": delegates or [],
        "system_prompt": "You are an agent. " * 20,
    }
    path = agents_dir / f"{agent_id}.yaml"
    path.write_text(yaml.dump(doc), encoding="utf-8")
    return agents_dir


class TestCrewValidator:
    def test_valid_minimal_fixture(self):
        report = validate_crew_directory(FIXTURE_CREW)
        assert report.ok, report.errors

    def test_rejects_missing_director(self, tmp_path):
        agents_dir = _write_agent(tmp_path, "synthesizer")
        report = validate_crew_directory(agents_dir)
        assert not report.ok
        assert any("director" in e for e in report.errors)

    def test_rejects_unknown_delegation_target(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        for name, delegates in [
            ("director", ["synthesizer", "ghost_agent"]),
            ("synthesizer", []),
        ]:
            _write_agent(tmp_path, name, delegates)
        report = validate_crew_directory(tmp_path)
        assert not report.ok
        assert any("ghost_agent" in e for e in report.errors)

    def test_rejects_unknown_tool_reference(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        for name in ("director", "synthesizer"):
            _write_agent(tmp_path, name, ["synthesizer"] if name == "director" else [])
        director_file = agents_dir / "director.yaml"
        raw = yaml.safe_load(director_file.read_text())
        raw["tools"] = ["not_a_real_tool"]
        director_file.write_text(yaml.dump(raw), encoding="utf-8")
        report = validate_crew_directory(tmp_path)
        assert not report.ok
        assert any("not_a_real_tool" in e for e in report.errors)

    def test_rejects_invalid_yaml(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        (agents_dir / "broken.yaml").write_text("id: [unclosed", encoding="utf-8")
        report = validate_crew_directory(tmp_path)
        assert not report.ok
        assert any("YAML parse error" in e for e in report.errors)

    def test_rejects_unknown_agent_fields(self, tmp_path):
        _write_agent(tmp_path, "director", ["synthesizer"])
        _write_agent(tmp_path, "synthesizer")
        director = tmp_path / "agents" / "director.yaml"
        raw = yaml.safe_load(director.read_text())
        raw["extra_field"] = "nope"
        director.write_text(yaml.dump(raw), encoding="utf-8")
        report = validate_crew_directory(tmp_path)
        assert not report.ok
        assert any("unknown fields" in e for e in report.errors)

    def test_rejects_self_delegation(self, tmp_path):
        _write_agent(tmp_path, "director", ["director", "synthesizer"])
        _write_agent(tmp_path, "synthesizer")
        report = validate_crew_directory(tmp_path)
        assert not report.ok
        assert any("cannot delegate to itself" in e for e in report.errors)

    def test_rejects_short_system_prompt(self, tmp_path):
        _write_agent(tmp_path, "director", ["synthesizer"])
        _write_agent(tmp_path, "synthesizer")
        synth = tmp_path / "agents" / "synthesizer.yaml"
        raw = yaml.safe_load(synth.read_text())
        raw["system_prompt"] = "too short"
        synth.write_text(yaml.dump(raw), encoding="utf-8")
        report = validate_crew_directory(tmp_path)
        assert not report.ok
        assert any("system_prompt" in e for e in report.errors)

    def test_validates_plugin_tool_module(self, tmp_path):
        _write_agent(tmp_path, "director", ["synthesizer"])
        _write_agent(tmp_path, "synthesizer")
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "bad_tool.py").write_text("def broken(", encoding="utf-8")
        report = validate_crew_directory(tmp_path, tools_dir=tools_dir)
        assert not report.ok
        assert any("syntax error" in e.lower() for e in report.errors)

    def test_validates_crew_manifest_answer_modes(self, tmp_path):
        _write_agent(tmp_path, "director", ["synthesizer"])
        _write_agent(tmp_path, "synthesizer")
        (tmp_path / "crew.yaml").write_text(
            yaml.dump(
                {
                    "name": "test-crew",
                    "answer_modes": [{"id": "not_valid", "label": "Bad"}],
                }
            ),
            encoding="utf-8",
        )
        report = validate_crew_directory(tmp_path)
        assert not report.ok
        assert any("not_valid" in e for e in report.errors)

    def test_raise_if_failed(self, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir()
        with pytest.raises(CrewValidationError):
            validate_or_raise(agents_dir)

    def test_labz_default_crew_passes(self):
        from src.agent_paths import DEFAULT_CONFIG_DIR

        report = validate_crew_directory(DEFAULT_CONFIG_DIR)
        assert report.ok, report.errors
