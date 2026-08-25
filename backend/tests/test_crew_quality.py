"""Coverage for crew paths, manifests, bundled plugins, and validation edge cases."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from scripts.validate_all_crews import bundled_crew_dirs, main as validate_all_crews
from src import agent_paths
from src.agents.crew_manifest import (
    DEFAULT_OUTPUT_COMPOSITION,
    CrewManifest,
    clear_crew_manifest_cache,
    composition_prompt_block,
    get_crew_manifest,
    load_crew_manifest,
    normalize_output_composition,
)
from src.agents.crew_validator import validate_crew_directory


def _write_agent(
    crew_dir: Path,
    agent_id: str,
    *,
    tools: list[str] | None = None,
    delegates: list[str] | None = None,
    **overrides: Any,
) -> Path:
    agents_dir = crew_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    document = {
        "id": agent_id,
        "name": agent_id.title(),
        "role": f"Role for {agent_id}",
        "tools": tools or [],
        "can_delegate_to": delegates or [],
        "system_prompt": "Perform the assigned crew role carefully and report evidence. " * 3,
        **overrides,
    }
    path = agents_dir / f"{agent_id}.yaml"
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return path


def _minimal_crew(tmp_path: Path) -> Path:
    _write_agent(tmp_path, "director", delegates=["synthesizer"])
    _write_agent(tmp_path, "synthesizer")
    return tmp_path


def _load_tool(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestAgentPaths:
    def test_relative_and_absolute_config_overrides(self, monkeypatch, tmp_path):
        monkeypatch.setenv("AGENT_CONFIG_DIR", "crews/active/agents")
        assert (
            agent_paths.get_agent_config_dir()
            == (agent_paths.BACKEND_ROOT / "crews/active/agents").resolve()
        )

        monkeypatch.setenv("AGENT_CONFIG_DIR", str(tmp_path))
        assert agent_paths.get_agent_config_dir() == tmp_path

    def test_plugin_overrides_are_split_resolved_and_deduplicated(self, monkeypatch, tmp_path):
        relative = "crews/active/tools"
        monkeypatch.setenv(
            "AGENT_PLUGINS_DIR",
            os.pathsep.join(
                [
                    str(agent_paths.DEFAULT_PLUGINS_DIR),
                    relative,
                    "",
                    str(tmp_path),
                    relative,
                ]
            ),
        )

        assert agent_paths.get_agent_plugins_dirs() == [
            agent_paths.DEFAULT_PLUGINS_DIR,
            (agent_paths.BACKEND_ROOT / relative).resolve(),
            tmp_path,
        ]

    @pytest.mark.parametrize("value", ["0", "false", "FALSE", "no"])
    def test_common_prompt_false_values(self, monkeypatch, value):
        monkeypatch.setenv("INJECT_COMMON_PROMPTS", value)
        assert agent_paths.should_inject_common_prompts() is False


class TestCrewValidationEdges:
    def test_valid_plugin_is_imported_and_can_be_referenced(self, tmp_path):
        crew_dir = _minimal_crew(tmp_path)
        tools_dir = crew_dir / "tools"
        tools_dir.mkdir()
        (tools_dir / "custom_score.py").write_text(
            """
TOOL_DEFINITION = {"function": {"name": "custom_score"}}
def custom_score(value=0):
    return {"score": value}
""".strip(),
            encoding="utf-8",
        )
        director = crew_dir / "agents" / "director.yaml"
        document = yaml.safe_load(director.read_text(encoding="utf-8"))
        document["tools"] = ["custom_score"]
        director.write_text(yaml.safe_dump(document), encoding="utf-8")

        report = validate_crew_directory(crew_dir)

        assert report.ok, report.errors
        assert not report.warnings

    @pytest.mark.parametrize(
        ("source", "expected"),
        [
            ("raise RuntimeError('boom')", "import failed"),
            ("def orphan():\n    return None", "missing TOOL_DEFINITION"),
            (
                "TOOL_DEFINITION = {'function': {'name': 'missing_callable'}}",
                "no callable",
            ),
        ],
    )
    def test_rejects_plugins_that_cannot_load(self, tmp_path, source, expected):
        crew_dir = _minimal_crew(tmp_path)
        tools_dir = crew_dir / "tools"
        tools_dir.mkdir()
        (tools_dir / "broken.py").write_text(source, encoding="utf-8")

        report = validate_crew_directory(crew_dir)

        assert not report.ok
        assert any(expected in error for error in report.errors)

    def test_warns_for_unreferenced_plugin(self, tmp_path):
        crew_dir = _minimal_crew(tmp_path)
        tools_dir = crew_dir / "tools"
        tools_dir.mkdir()
        (tools_dir / "unused_tool.py").write_text(
            """
TOOL_DEFINITION = {"function": {"name": "unused_tool"}}
def unused_tool():
    return {}
""".strip(),
            encoding="utf-8",
        )

        report = validate_crew_directory(crew_dir)

        assert report.ok
        assert report.warnings == [
            "Plugin tool 'unused_tool' is defined but no agent references it."
        ]

    def test_requires_manifest_when_requested(self, tmp_path):
        crew_dir = _minimal_crew(tmp_path)
        report = validate_crew_directory(crew_dir, require_manifest=True)
        assert report.errors == ["crew.yaml manifest is required but missing."]

    @pytest.mark.parametrize(
        ("composition", "expected"),
        [
            ("not-a-map", "must be a mapping"),
            ({"tabs": []}, "tabs must be a non-empty list"),
            ({"tabs": ["unknown"]}, "contains unknown tab"),
            ({"citations": "sometimes"}, "citations"),
            ({"synthesizer_tools": "calculator"}, "synthesizer_tools must be a list"),
            ({"synthesizer_tools": ["Bad Tool"]}, "invalid synthesizer_tools"),
        ],
    )
    def test_rejects_invalid_output_composition(self, tmp_path, composition, expected):
        crew_dir = _minimal_crew(tmp_path)
        (crew_dir / "crew.yaml").write_text(
            yaml.safe_dump({"output_composition": composition}),
            encoding="utf-8",
        )

        report = validate_crew_directory(crew_dir)

        assert any(expected in error for error in report.errors)

    def test_rejects_duplicate_answer_modes(self, tmp_path):
        crew_dir = _minimal_crew(tmp_path)
        (crew_dir / "crew.yaml").write_text(
            yaml.safe_dump(
                {
                    "answer_modes": [
                        {"id": "summary", "label": "Brief"},
                        {"id": "summary", "label": "Duplicate"},
                    ]
                }
            ),
            encoding="utf-8",
        )
        report = validate_crew_directory(crew_dir)
        assert any("duplicate answer mode" in error for error in report.errors)


class TestCrewManifestBehavior:
    def test_normalizes_invalid_collection_values(self):
        normalized = normalize_output_composition(
            {"tabs": "summary", "synthesizer_tools": "calculator", "citations": "none"}
        )
        assert normalized["tabs"] == DEFAULT_OUTPUT_COMPOSITION["tabs"]
        assert normalized["synthesizer_tools"] == DEFAULT_OUTPUT_COMPOSITION["synthesizer_tools"]
        assert normalized["citations"] == "none"

    def test_explicit_empty_synthesizer_tools_are_preserved(self, tmp_path):
        agents = tmp_path / "agents"
        agents.mkdir()
        (tmp_path / "crew.yaml").write_text(
            yaml.safe_dump({"output_composition": {"synthesizer_tools": []}}),
            encoding="utf-8",
        )
        assert load_crew_manifest(agents).synthesizer_tools() == []

    def test_api_helpers_filter_tools_and_fallback_labels(self):
        manifest = CrewManifest(
            name="test",
            display_name="Test",
            description="Test crew",
            default_answer_mode="summary",
            answer_modes=[{"id": "summary", "label": "Brief"}],
            output_composition={"synthesizer_tools": ["calculator", "", 42]},
        )
        assert manifest.mode_label("summary") == "Brief"
        assert manifest.mode_label("unknown") == "unknown"
        assert manifest.synthesizer_tools() == ["calculator"]
        assert manifest.to_api_dict()["name"] == "test"

    @pytest.mark.parametrize(
        ("composition", "expected"),
        [
            (
                {
                    "tabs": ["summary"],
                    "tables": "always",
                    "charts": "always",
                    "citations": "required",
                    "images": "when_requested",
                    "synthesizer_tools": ["visualizer"],
                },
                ["[DATA_START]", "`visualizer`", "Citations are required", "image_generator"],
            ),
            (
                {
                    "tabs": ["summary"],
                    "tables": "none",
                    "charts": "none",
                    "citations": "none",
                    "images": "none",
                    "synthesizer_tools": [],
                },
                ["(none specified", "Do not prioritize citation", "Do not generate images"],
            ),
        ],
    )
    def test_composition_prompt_includes_policy_guidance(self, composition, expected):
        prompt = composition_prompt_block(composition)
        for text in expected:
            assert text in prompt

    def test_manifest_cache_can_be_cleared(self):
        first = get_crew_manifest()
        clear_crew_manifest_cache()
        second = get_crew_manifest()
        assert first is not second
        assert first.name == second.name


class TestBundledCrewsAndDemoTools:
    def test_all_bundled_crews_and_plugins_validate(self):
        crews = bundled_crew_dirs()
        assert {crew.name for crew in crews} == {
            "business-coaching-crew",
            "technical-due-diligence",
        }
        assert validate_all_crews() == 0

    def test_dependency_risk_matrix_orders_and_explains_risk(self):
        tool = _load_tool(
            agent_paths.BACKEND_ROOT
            / "crews/examples/technical-due-diligence/tools/dependency_risk_matrix.py"
        )
        result = tool.dependency_risk_matrix(
            [
                {
                    "name": "safe",
                    "known_vulnerability_severity": "none",
                    "maintenance_status": "active",
                    "license": "mit",
                    "latest_release_age_days": 20,
                },
                {
                    "name": "risky",
                    "known_vulnerability_severity": "critical",
                    "maintenance_status": "abandoned",
                    "license": "agpl-3.0",
                    "latest_release_age_days": "not-a-number",
                },
            ]
        )
        assert result["total"] == 2
        assert result["dependencies"][0]["name"] == "risky"
        assert result["counts_by_tier"] == {
            "low": 1,
            "medium": 0,
            "high": 0,
            "critical": 1,
        }
        assert "invalid release-age value" in result["dependencies"][0]["reasons"]

    def test_evidence_coverage_flags_unsupported_high_severity_findings(self):
        tool = _load_tool(
            agent_paths.BACKEND_ROOT
            / "crews/examples/technical-due-diligence/tools/evidence_coverage_score.py"
        )
        result = tool.evidence_coverage_score(
            [
                {
                    "id": "SEC-1",
                    "claim": "Supported",
                    "severity": "high",
                    "confidence": "high",
                    "evidence_refs": ["artifact://report"],
                },
                {
                    "id": "SEC-2",
                    "claim": "",
                    "severity": "critical",
                    "confidence": "certain",
                    "evidence_refs": [],
                    "inference": True,
                },
            ]
        )
        assert result["evidence_coverage"] == 0.5
        assert result["unsupported_high_severity"] == ["SEC-2"]
        assert result["confidence_distribution"] == {
            "high": 1,
            "medium": 0,
            "low": 0,
            "unspecified": 1,
        }
        assert {flag["flag"] for flag in result["audit_flags"]} == {
            "unrecognized confidence value",
            "missing claim",
            "unsupported inference",
            "no evidence reference",
        }
