#!/usr/bin/env python3
"""CLI: validate a crew directory. Exit 1 on failure."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from repo root or backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.agents.crew_validator import validate_crew_directory  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a CrewDefine / agent crew directory.")
    parser.add_argument("crew_dir", type=Path, help="Crew root or agents/ directory")
    parser.add_argument(
        "--tools-dir",
        type=Path,
        default=None,
        help="Plugin tools directory (default: <crew>/tools if present)",
    )
    parser.add_argument(
        "--require-manifest",
        action="store_true",
        help="Require crew.yaml manifest",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only print errors/warnings on failure",
    )
    args = parser.parse_args()

    report = validate_crew_directory(
        args.crew_dir,
        tools_dir=args.tools_dir,
        require_manifest=args.require_manifest,
    )

    if report.warnings and not args.quiet:
        for w in report.warnings:
            print(f"warning: {w}", file=sys.stderr)

    if report.ok:
        if not args.quiet:
            print(f"OK: {args.crew_dir.resolve()}")
        return 0

    for err in report.errors:
        print(f"error: {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
