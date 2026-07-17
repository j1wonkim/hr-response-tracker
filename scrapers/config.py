"""Pipeline-wide configuration, loaded from config/pipeline.yaml.

Config over code (CLAUDE.md's fork-friendly design goal): values that
shape ingestion behavior -- starting with ingest_start_date -- live in a
YAML file instead of being hardcoded in scrapers, so forkers can retune
them without touching code. See "Bound initial HRW ingestion with a
config-driven ingest_start_date" in DECISIONS.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "pipeline.yaml"


@dataclass
class PipelineConfig:
    ingest_start_date: date


def load_pipeline_config(path: Path = DEFAULT_CONFIG_PATH) -> PipelineConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    ingest_start_date = datetime.strptime(raw["ingest_start_date"], "%Y-%m-%d").date()
    return PipelineConfig(ingest_start_date=ingest_start_date)
