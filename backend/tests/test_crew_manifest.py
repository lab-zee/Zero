"""Tests for crew.yaml manifest loading."""

from pathlib import Path

from src.agents.crew_manifest import load_crew_manifest, DEFAULT_MANIFEST


class TestCrewManifest:
    def test_default_labz_manifest(self):
        from src.agent_paths import DEFAULT_CONFIG_DIR

        manifest = load_crew_manifest(DEFAULT_CONFIG_DIR)
        assert manifest.name == "labz-strategy"
        assert len(manifest.answer_modes) >= 3
        assert manifest.default_answer_mode == "light"

    def test_fixture_without_manifest_uses_defaults(self, tmp_path):
        agents = tmp_path / "agents"
        agents.mkdir()
        manifest = load_crew_manifest(agents)
        assert manifest.display_name == DEFAULT_MANIFEST["display_name"]

    def test_custom_manifest(self, tmp_path):
        import yaml

        agents = tmp_path / "agents"
        agents.mkdir()
        (tmp_path / "crew.yaml").write_text(
            yaml.dump(
                {
                    "name": "dinner",
                    "display_name": "Dinner Planner",
                    "default_answer_mode": "summary",
                    "answer_modes": [
                        {"id": "summary", "label": "Quick", "description": "Short plan"},
                        {"id": "light", "label": "Full", "description": "Full plan"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        manifest = load_crew_manifest(agents)
        assert manifest.display_name == "Dinner Planner"
        assert len(manifest.answer_modes) == 2
