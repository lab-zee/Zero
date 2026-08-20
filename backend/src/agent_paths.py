"""
Resolve agent YAML config and plugin tool directories.

Supports swapping entire crews via AGENT_CONFIG_DIR / AGENT_PLUGINS_DIR
(see scripts/load-crew.sh).
"""

from __future__ import annotations

import os
from pathlib import Path

# backend/ (parent of src/)
BACKEND_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CONFIG_DIR = BACKEND_ROOT / "src" / "agents" / "config"
DEFAULT_PLUGINS_DIR = BACKEND_ROOT / "src" / "agents" / "tools" / "plugins"


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = (BACKEND_ROOT / path).resolve()
    return path


def get_agent_config_dir() -> Path:
    """Directory containing agent *.yaml configs."""
    override = os.getenv("AGENT_CONFIG_DIR", "").strip()
    if override:
        return _resolve_path(override)
    return DEFAULT_CONFIG_DIR


def get_agent_plugins_dirs() -> list[Path]:
    """
    Directories scanned for plugin tool modules.

    When AGENT_PLUGINS_DIR is set, that directory is scanned in addition to the
    built-in plugins folder (crew-specific tools layer on top of builtins).
    """
    dirs: list[Path] = [DEFAULT_PLUGINS_DIR]
    override = os.getenv("AGENT_PLUGINS_DIR", "").strip()
    if override:
        for part in override.split(os.pathsep):
            part = part.strip()
            if part:
                extra = _resolve_path(part)
                if extra not in dirs:
                    dirs.append(extra)
    return dirs


def should_inject_common_prompts() -> bool:
    """Whether to splice LabZ _common_prompts.yaml into agent system prompts."""
    return os.getenv("INJECT_COMMON_PROMPTS", "true").lower() not in (
        "0",
        "false",
        "no",
    )
