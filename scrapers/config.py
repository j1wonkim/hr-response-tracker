"""Pipeline-wide configuration, loaded from config/pipeline.yaml.

Config over code (CLAUDE.md's fork-friendly design goal): operational
values -- feed URLs, cache TTLs, and eventually ministry source
declarations (CLAUDE.md stage 2) -- live in a YAML file instead of being
hardcoded in scrapers, so forkers can retune or redirect the pipeline
without touching code. This is a hard requirement of the project's
design, not a one-off feature: see DECISIONS.md, "Restore the config
system after an over-scoped removal".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "pipeline.yaml"


@dataclass
class HRWConfig:
    feed_url: str
    feed_cache_ttl_hours: float
    article_cache_ttl_hours: float


@dataclass
class PipelineConfig:
    hrw: HRWConfig


def load_pipeline_config(path: Path = DEFAULT_CONFIG_PATH) -> PipelineConfig:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    hrw_raw = raw["hrw"]
    hrw_config = HRWConfig(
        feed_url=hrw_raw["feed_url"],
        feed_cache_ttl_hours=hrw_raw["feed_cache_ttl_hours"],
        article_cache_ttl_hours=hrw_raw["article_cache_ttl_hours"],
    )
    return PipelineConfig(hrw=hrw_config)
