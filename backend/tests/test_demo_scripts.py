"""Non-mutating CLI tests for crew selection and path validation."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / script), *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("slug", ["../technical-due-diligence", "/tmp/crew", "Bad_Crew"])
def test_demo_rejects_unsafe_crew_slugs(slug):
    result = _run("demo.sh", slug)
    assert result.returncode == 1
    assert "crew must be a directory name" in result.stderr


def test_demo_rejects_unknown_bundled_crew():
    result = _run("demo.sh", "not-a-bundled-crew")
    assert result.returncode == 1
    assert "unknown bundled crew" in result.stderr


def test_load_crew_help_is_non_mutating():
    result = _run("load-crew.sh", "--help")
    assert result.returncode == 0
    assert "Load a CrewDefine crew directory" in result.stdout


def test_load_crew_rejects_unknown_options():
    result = _run("load-crew.sh", "--unknown")
    assert result.returncode == 1
    assert "unknown option" in result.stderr


def test_load_crew_rejects_missing_directory():
    missing = REPO_ROOT / "definitely-missing-crew"
    result = _run("load-crew.sh", str(missing))
    assert result.returncode == 1
    assert f"crew directory does not exist: {missing}" in result.stderr
