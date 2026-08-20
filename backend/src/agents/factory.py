"""
Factory for AgentRegistry using environment-driven crew paths.
"""

from __future__ import annotations

from typing import Optional, Union

import os
from openai import OpenAI

from ..agent_paths import get_agent_config_dir, should_inject_common_prompts
from ..llm_client import LLMClient
from .registry import AgentRegistry


def create_agent_registry(
    client: Union[OpenAI, LLMClient],
    tool_registry: Optional[dict] = None,
    default_model: Optional[str] = None,
    *,
    skip_validation: bool = False,
) -> AgentRegistry:
    """Build an AgentRegistry from AGENT_CONFIG_DIR / INJECT_COMMON_PROMPTS env vars."""
    from ..agent_paths import get_agent_config_dir, get_agent_plugins_dirs
    from .crew_validator import validate_agent_config_dir

    config_dir = get_agent_config_dir()
    if not skip_validation and os.getenv("TESTING") != "1":
        plugin_dirs = get_agent_plugins_dirs()
        extra_plugins = next((d for d in plugin_dirs if d.name != "plugins"), None)
        report = validate_agent_config_dir(config_dir, extra_plugins)
        report.raise_if_failed()
        for warning in report.warnings:
            print(f"[crew] warning: {warning}")

    # Always reload manifest when building a registry (load-crew / restart)
    from .crew_manifest import clear_crew_manifest_cache

    clear_crew_manifest_cache()

    return AgentRegistry(
        config_dir,
        client,
        tool_registry=tool_registry or {},
        default_model=default_model,
        inject_common_prompts=should_inject_common_prompts(),
    )
