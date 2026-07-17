from datetime import date
from pathlib import Path

from scrapers.config import DEFAULT_CONFIG_PATH, load_pipeline_config


def test_default_config_sets_ingest_start_date_to_2026_01_01():
    config = load_pipeline_config()
    assert config.ingest_start_date == date(2026, 1, 1)


def test_default_config_path_points_at_repo_config_file():
    assert DEFAULT_CONFIG_PATH.name == "pipeline.yaml"
    assert DEFAULT_CONFIG_PATH.parent.name == "config"


def test_load_pipeline_config_from_custom_path(tmp_path):
    custom = tmp_path / "custom.yaml"
    custom.write_text("ingest_start_date: \"2025-06-15\"\n", encoding="utf-8")

    config = load_pipeline_config(custom)

    assert config.ingest_start_date == date(2025, 6, 15)
