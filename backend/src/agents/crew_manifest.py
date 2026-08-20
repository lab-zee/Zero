"""Load crew.yaml manifest (metadata + configurable answer modes)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

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

DEFAULT_MANIFEST: dict[str, Any] = {
    "name": "labz-strategy",
    "display_name": "Business Strategy",
    "description": "Multi-agent strategic advisory crew (LabZ default)",
    "default_answer_mode": "light",
    "answer_modes": DEFAULT_ANSWER_MODES,
}


@dataclass
class CrewManifest:
    name: str
    display_name: str
    description: str
    default_answer_mode: str
    answer_modes: list[dict[str, str]]

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "default_answer_mode": self.default_answer_mode,
            "answer_modes": self.answer_modes,
        }


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
            )
    return CrewManifest(**DEFAULT_MANIFEST)  # type: ignore[arg-type]


@lru_cache(maxsize=1)
def get_crew_manifest() -> CrewManifest:
    return load_crew_manifest()


def clear_crew_manifest_cache() -> None:
    get_crew_manifest.cache_clear()
