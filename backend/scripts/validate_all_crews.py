#!/usr/bin/env python3
"""Validate the built-in crew and every bundled example, including plugin imports."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.agent_paths import DEFAULT_CONFIG_DIR  # noqa: E402
from src.agents.crew_validator import validate_crew_directory  # noqa: E402


def bundled_crew_dirs() -> list[Path]:
    examples_dir = BACKEND_ROOT / "crews" / "examples"
    return sorted(path.parent for path in examples_dir.glob("*/crew.yaml"))


def main() -> int:
    crew_dirs = [DEFAULT_CONFIG_DIR, *bundled_crew_dirs()]
    failed = False

    for crew_dir in crew_dirs:
        report = validate_crew_directory(crew_dir, require_manifest=True)
        for warning in report.warnings:
            print(f"warning: {crew_dir.name}: {warning}", file=sys.stderr)
        if report.ok:
            print(f"OK: {crew_dir.resolve()}")
            continue
        failed = True
        for error in report.errors:
            print(f"error: {crew_dir.name}: {error}", file=sys.stderr)

    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
