"""
Validate agent crew directories (CrewDefine output or hand-edited YAML).

Checks schema, delegation graph, tool references, plugin stubs, and crew manifest.
Used by load-crew.sh, AgentRegistry startup, and pytest.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

AGENT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
TOOL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")

AGENT_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "name",
        "role",
        "tools",
        "can_delegate_to",
        "system_prompt",
        "model",
        "data_extraction_note",
    }
)
REQUIRED_AGENT_FIELDS: frozenset[str] = frozenset(
    {"id", "name", "role", "tools", "can_delegate_to", "system_prompt"}
)

MANIFEST_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "display_name",
        "description",
        "default_answer_mode",
        "answer_modes",
    }
)

KNOWN_ANSWER_MODE_IDS: frozenset[str] = frozenset(
    {"summary", "light", "extended", "project_plan", "roadmap"}
)

INFRASTRUCTURE_AGENTS: frozenset[str] = frozenset({"director", "synthesizer"})


class CrewValidationError(Exception):
    """Raised when crew validation fails."""

    def __init__(self, errors: list[str], warnings: list[str] | None = None):
        self.errors = errors
        self.warnings = warnings or []
        message = "; ".join(errors) if errors else "Crew validation failed"
        super().__init__(message)


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def raise_if_failed(self) -> None:
        if self.errors:
            raise CrewValidationError(self.errors, self.warnings)


def _load_yaml(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_agent_document(raw: Any, label: str, report: ValidationReport) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        report.errors.append(f"{label}: top-level must be a mapping, got {type(raw).__name__}.")
        return None

    extra = set(raw) - AGENT_FIELDS
    if extra:
        report.errors.append(
            f"{label}: unknown fields {sorted(extra)} — LabZ will ignore these silently."
        )

    missing = REQUIRED_AGENT_FIELDS - set(raw)
    if missing:
        report.errors.append(f"{label}: missing required fields {sorted(missing)}.")
        return None

    agent_id = raw.get("id")
    if not isinstance(agent_id, str) or not AGENT_ID_PATTERN.match(agent_id):
        report.errors.append(f"{label}: id must be snake_case, got {agent_id!r}.")
        return None

    for text_field in ("name", "role"):
        val = raw.get(text_field)
        if not isinstance(val, str) or not val.strip():
            report.errors.append(f"{label}: {text_field} must be a non-empty string.")

    prompt = raw.get("system_prompt")
    if not isinstance(prompt, str) or len(prompt.strip()) < 80:
        report.errors.append(
            f"{label}: system_prompt must be a string with at least 80 characters."
        )

    tools = raw.get("tools")
    if not isinstance(tools, list):
        report.errors.append(f"{label}: tools must be a list.")
    else:
        for tool_id in tools:
            if not isinstance(tool_id, str) or not TOOL_ID_PATTERN.match(tool_id):
                report.errors.append(f"{label}: invalid tool id {tool_id!r}.")

    delegates = raw.get("can_delegate_to")
    if not isinstance(delegates, list):
        report.errors.append(f"{label}: can_delegate_to must be a list.")
    else:
        for target in delegates:
            if not isinstance(target, str) or not AGENT_ID_PATTERN.match(target):
                report.errors.append(f"{label}: invalid delegation target {target!r}.")
        if agent_id in delegates:
            report.errors.append(f"{label}: agent cannot delegate to itself.")

    if raw.get("model") is not None and not isinstance(raw.get("model"), str):
        report.errors.append(f"{label}: model must be a string when set.")

    return raw


def _collect_builtin_tool_ids() -> set[str]:
    from .tools import TOOL_IMPLEMENTATIONS

    return set(TOOL_IMPLEMENTATIONS.keys())


def _collect_plugin_tool_ids(tools_dir: Path | None) -> set[str]:
    if tools_dir is None or not tools_dir.is_dir():
        return set()

    ids: set[str] = set()
    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.stem.startswith("_"):
            continue
        tool_id = _inspect_plugin_tool(py_file, report=None)
        if tool_id:
            ids.add(tool_id)
    return ids


def _inspect_plugin_tool(py_file: Path, report: ValidationReport | None) -> str | None:
    try:
        source = py_file.read_text(encoding="utf-8")
        ast.parse(source, filename=str(py_file))
    except SyntaxError as e:
        if report is not None:
            report.errors.append(f"{py_file.name}: Python syntax error: {e}")
        return None

    spec = importlib.util.spec_from_file_location(f"crew_plugin_check_{py_file.stem}", py_file)
    if spec is None or spec.loader is None:
        if report is not None:
            report.errors.append(f"{py_file.name}: could not load module spec.")
        return None

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        if report is not None:
            report.errors.append(f"{py_file.name}: import failed: {e}")
        return None

    definition = getattr(module, "TOOL_DEFINITION", None)
    if not isinstance(definition, dict):
        if report is not None:
            report.errors.append(f"{py_file.name}: missing TOOL_DEFINITION dict.")
        return None

    tool_name = definition.get("function", {}).get("name") or py_file.stem
    impl = getattr(module, tool_name, None)
    if not callable(impl):
        if report is not None:
            report.errors.append(f"{py_file.name}: no callable named {tool_name!r}.")
        return None

    return tool_name


def _validate_manifest(raw: Any, report: ValidationReport) -> dict[str, Any] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        report.errors.append("crew.yaml: top-level must be a mapping.")
        return None

    extra = set(raw) - MANIFEST_FIELDS
    if extra:
        report.warnings.append(f"crew.yaml: unknown fields {sorted(extra)} will be ignored.")

    modes = raw.get("answer_modes")
    if modes is not None:
        if not isinstance(modes, list) or not modes:
            report.errors.append("crew.yaml: answer_modes must be a non-empty list when set.")
        else:
            seen: set[str] = set()
            for i, mode in enumerate(modes):
                if not isinstance(mode, dict):
                    report.errors.append(f"crew.yaml: answer_modes[{i}] must be a mapping.")
                    continue
                mode_id = mode.get("id")
                if not isinstance(mode_id, str) or mode_id not in KNOWN_ANSWER_MODE_IDS:
                    report.errors.append(
                        f"crew.yaml: answer_modes[{i}].id {mode_id!r} is not a supported mode. "
                        f"Allowed: {sorted(KNOWN_ANSWER_MODE_IDS)}."
                    )
                elif mode_id in seen:
                    report.errors.append(f"crew.yaml: duplicate answer mode id {mode_id!r}.")
                else:
                    seen.add(mode_id)
                if not isinstance(mode.get("label"), str) or not mode.get("label", "").strip():
                    report.errors.append(f"crew.yaml: answer_modes[{i}] requires a non-empty label.")

    default_mode = raw.get("default_answer_mode")
    if default_mode is not None and default_mode not in KNOWN_ANSWER_MODE_IDS:
        report.errors.append(
            f"crew.yaml: default_answer_mode {default_mode!r} is not supported."
        )

    return raw


def validate_crew_directory(
    crew_dir: Path,
    *,
    tools_dir: Path | None = None,
    require_manifest: bool = False,
) -> ValidationReport:
    """
    Validate a crew directory.

    Accepts either:
      - CrewDefine layout: <crew>/agents/*.yaml [+ tools/*.py]
      - Runtime layout: flat agents dir (pass tools_dir separately)
    """
    report = ValidationReport()
    crew_dir = crew_dir.resolve()

    agents_dir = crew_dir / "agents" if (crew_dir / "agents").is_dir() else crew_dir
    if not agents_dir.is_dir():
        report.errors.append(f"No agents directory at {agents_dir}.")
        return report

    if tools_dir is None:
        candidate = crew_dir / "tools"
        tools_dir = candidate if candidate.is_dir() else None

    yaml_files = sorted(
        p for p in agents_dir.glob("*.yaml")
        if not p.name.startswith("_") and p.name != "crew.yaml"
    )
    if not yaml_files:
        report.errors.append(f"No agent YAML files in {agents_dir}.")
        return report

    agents: list[dict[str, Any]] = []
    agent_ids: set[str] = set()

    for path in yaml_files:
        try:
            raw = _load_yaml(path)
        except yaml.YAMLError as e:
            report.errors.append(f"{path.name}: YAML parse error: {e}")
            continue

        doc = _validate_agent_document(raw, path.name, report)
        if doc:
            if doc["id"] in agent_ids:
                report.errors.append(f"{path.name}: duplicate agent id {doc['id']!r}.")
            else:
                agent_ids.add(doc["id"])
                agents.append(doc)

    if report.errors:
        return report

    missing_infra = INFRASTRUCTURE_AGENTS - agent_ids
    if missing_infra:
        report.errors.append(
            f"Crew must include infrastructure agents: {sorted(missing_infra)}."
        )

    builtin_tools = _collect_builtin_tool_ids()
    plugin_tools: set[str] = set()
    if tools_dir and tools_dir.is_dir():
        for py_file in sorted(tools_dir.glob("*.py")):
            if py_file.stem.startswith("_"):
                continue
            tool_id = _inspect_plugin_tool(py_file, report)
            if tool_id:
                if tool_id in plugin_tools:
                    report.errors.append(f"{py_file.name}: duplicate plugin tool id {tool_id!r}.")
                plugin_tools.add(tool_id)

    known_tools = builtin_tools | plugin_tools

    for agent in agents:
        for tool_id in agent.get("tools") or []:
            if tool_id not in known_tools:
                report.errors.append(
                    f"{agent['id']}: references unknown tool {tool_id!r}. "
                    "Use a built-in tool or add a plugin under tools/."
                )
        for target in agent.get("can_delegate_to") or []:
            if target not in agent_ids:
                report.errors.append(
                    f"{agent['id']}: can_delegate_to includes {target!r}, "
                    "which is not a defined agent id."
                )

    manifest_path = agents_dir / "crew.yaml"
    if not manifest_path.exists():
        manifest_path = agents_dir.parent / "crew.yaml"
    if manifest_path.exists():
        try:
            _validate_manifest(_load_yaml(manifest_path), report)
        except yaml.YAMLError as e:
            report.errors.append(f"crew.yaml: YAML parse error: {e}")
    elif require_manifest:
        report.errors.append("crew.yaml manifest is required but missing.")

    referenced_plugin_tools: set[str] = set()
    for agent in agents:
        for tool_id in agent.get("tools") or []:
            if tool_id in plugin_tools:
                referenced_plugin_tools.add(tool_id)
    for tool_id in plugin_tools - referenced_plugin_tools:
        report.warnings.append(
            f"Plugin tool {tool_id!r} is defined but no agent references it."
        )

    return report


def validate_agent_config_dir(config_dir: Path, plugins_dir: Path | None = None) -> ValidationReport:
    """Validate the runtime agent config directory (flat YAML layout)."""
    plugins = plugins_dir
    if plugins is None:
        from ..agent_paths import get_agent_plugins_dirs

        dirs = get_agent_plugins_dirs()
        plugins = next((d for d in dirs if d.name != "plugins"), None)
    return validate_crew_directory(config_dir, tools_dir=plugins)


def validate_or_raise(config_dir: Path, plugins_dir: Path | None = None) -> ValidationReport:
    report = validate_agent_config_dir(config_dir, plugins_dir)
    report.raise_if_failed()
    return report
