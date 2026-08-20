"""Load crew.yaml manifest (metadata + answer modes + output composition)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

from ..agent_paths import get_agent_config_dir

DEFAULT_ANSWER_MODES: list[dict[str, str]] = [
    {
        "id": "summary",
        "label": "Summary",
        "description": "Concise executive briefing",
    },
    {
        "id": "light",
        "label": "One-Pager",
        "description": "Balanced memo with key evidence",
    },
    {
        "id": "extended",
        "label": "Report",
        "description": "Comprehensive analysis",
    },
    {
        "id": "project_plan",
        "label": "30-60-90",
        "description": "Structured project plan",
    },
    {
        "id": "roadmap",
        "label": "Roadmap",
        "description": "Framework with actionable roadmap",
    },
]

DEFAULT_OUTPUT_COMPOSITION: dict[str, Any] = {
    "tabs": ["summary", "raw_data", "visualizations", "references"],
    "citations": "required",
    "charts": "when_quantitative",
    "tables": "when_structured",
    "images": "synthesizer_summary",
    "synthesizer_tools": [
        "visualizer",
        "extract_citations_structured",
        "swot",
        "generate_recommendations",
        "image_generator",
    ],
}

DEFAULT_MANIFEST: dict[str, Any] = {
    "name": "labz-strategy",
    "display_name": "Business Strategy",
    "description": "Multi-agent strategic advisory crew (LabZ default)",
    "default_answer_mode": "light",
    "answer_modes": DEFAULT_ANSWER_MODES,
    "output_composition": DEFAULT_OUTPUT_COMPOSITION,
}

COMPOSITION_KEYS = (
    "tabs",
    "citations",
    "charts",
    "tables",
    "images",
    "synthesizer_tools",
)


def normalize_output_composition(raw: Any) -> dict[str, Any]:
    """Normalize a raw output_composition mapping to a stable dict."""
    if not isinstance(raw, dict):
        return dict(DEFAULT_OUTPUT_COMPOSITION)
    out: dict[str, Any] = {}
    for key in COMPOSITION_KEYS:
        if key in raw and raw[key] is not None:
            out[key] = raw[key]
        elif key in DEFAULT_OUTPUT_COMPOSITION:
            out[key] = DEFAULT_OUTPUT_COMPOSITION[key]
    if not isinstance(out.get("tabs"), list):
        out["tabs"] = list(DEFAULT_OUTPUT_COMPOSITION["tabs"])
    if not isinstance(out.get("synthesizer_tools"), list):
        out["synthesizer_tools"] = list(DEFAULT_OUTPUT_COMPOSITION["synthesizer_tools"])
    return out


@dataclass
class CrewManifest:
    name: str
    display_name: str
    description: str
    default_answer_mode: str
    answer_modes: list[dict[str, str]]
    output_composition: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_OUTPUT_COMPOSITION))

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "default_answer_mode": self.default_answer_mode,
            "answer_modes": self.answer_modes,
            "output_composition": self.output_composition,
        }

    def mode_label(self, mode_id: str) -> str:
        for mode in self.answer_modes:
            if mode.get("id") == mode_id:
                return str(mode.get("label") or mode_id)
        return mode_id

    def synthesizer_tools(self) -> list[str]:
        tools = self.output_composition.get("synthesizer_tools") or []
        return [t for t in tools if isinstance(t, str) and t.strip()]


def _manifest_search_paths(config_dir: Path) -> list[Path]:
    return [
        config_dir / "crew.yaml",
        config_dir.parent / "crew.yaml",
    ]


def load_crew_manifest(config_dir: Path | None = None) -> CrewManifest:
    config_dir = config_dir or get_agent_config_dir()
    for path in _manifest_search_paths(config_dir):
        if path.is_file():
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            modes = raw.get("answer_modes") or DEFAULT_ANSWER_MODES
            composition = normalize_output_composition(
                raw.get("output_composition") or DEFAULT_OUTPUT_COMPOSITION
            )
            # Lightweight crews often omit strategy tools — keep empty list if explicitly set
            if isinstance(raw.get("output_composition"), dict) and "synthesizer_tools" in raw["output_composition"]:
                tools = raw["output_composition"]["synthesizer_tools"]
                composition["synthesizer_tools"] = tools if isinstance(tools, list) else []

            return CrewManifest(
                name=str(raw.get("name") or DEFAULT_MANIFEST["name"]),
                display_name=str(raw.get("display_name") or DEFAULT_MANIFEST["display_name"]),
                description=str(raw.get("description") or DEFAULT_MANIFEST["description"]),
                default_answer_mode=str(
                    raw.get("default_answer_mode") or DEFAULT_MANIFEST["default_answer_mode"]
                ),
                answer_modes=[
                    {
                        "id": str(m["id"]),
                        "label": str(m.get("label") or m["id"]),
                        "description": str(m.get("description") or ""),
                    }
                    for m in modes
                    if isinstance(m, dict) and m.get("id")
                ],
                output_composition=composition,
            )
    return CrewManifest(
        name=str(DEFAULT_MANIFEST["name"]),
        display_name=str(DEFAULT_MANIFEST["display_name"]),
        description=str(DEFAULT_MANIFEST["description"]),
        default_answer_mode=str(DEFAULT_MANIFEST["default_answer_mode"]),
        answer_modes=list(DEFAULT_ANSWER_MODES),
        output_composition=dict(DEFAULT_OUTPUT_COMPOSITION),
    )


@lru_cache(maxsize=1)
def get_crew_manifest() -> CrewManifest:
    return load_crew_manifest()


def clear_crew_manifest_cache() -> None:
    get_crew_manifest.cache_clear()


def composition_prompt_block(composition: Optional[dict[str, Any]] = None) -> str:
    """Build system-prompt guidance from output_composition for agents."""
    oc = composition or get_crew_manifest().output_composition
    tabs = ", ".join(oc.get("tabs") or ["summary"])
    tools = oc.get("synthesizer_tools") or []
    tool_line = ", ".join(f"`{t}`" for t in tools) if tools else "(none specified — use tools on your agent config)"

    lines = [
        "",
        "=== OUTPUT COMPOSITION (crew manifest) ===",
        f"- Preferred UI tabs: {tabs}",
        f"- Citations: {oc.get('citations', 'optional')}",
        f"- Charts: {oc.get('charts', 'none')}",
        f"- Tables: {oc.get('tables', 'when_structured')}",
        f"- Images: {oc.get('images', 'none')}",
        f"- Preferred synthesizer tools: {tool_line}",
    ]
    if oc.get("tables") in ("when_structured", "always"):
        lines.append(
            "- For structured lists/tables, emit `[DATA_START]` … `[DATA_END]` JSON "
            "blocks (array of row objects or `{label, type, value}`) so the Data tab populates."
        )
    if oc.get("charts") in ("when_quantitative", "always"):
        lines.append(
            "- For quantitative comparisons, use the `visualizer` tool so charts appear "
            "in the Visualizations tab."
        )
    if oc.get("citations") == "required":
        lines.append(
            "- Citations are required: use `extract_citations_structured` / inline `[n]` "
            "and a `## References` section."
        )
    elif oc.get("citations") == "none":
        lines.append("- Do not prioritize citation machinery for this crew.")
    if oc.get("images") in ("when_requested", "synthesizer_summary"):
        lines.append("- Use `image_generator` only when it materially helps the answer.")
    elif oc.get("images") == "none":
        lines.append("- Do not generate images for this crew.")
    return "\n".join(lines)
