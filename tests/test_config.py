from pathlib import Path

from scrapers.config import DEFAULT_CONFIG_PATH, load_pipeline_config


def test_default_config_sets_hrw_feed_settings():
    config = load_pipeline_config()
    assert config.hrw.feed_url == "https://www.hrw.org/rss/news"
    assert config.hrw.feed_cache_ttl_hours == 4
    assert config.hrw.article_cache_ttl_hours == 168


def test_default_config_path_points_at_repo_config_file():
    assert DEFAULT_CONFIG_PATH.name == "pipeline.yaml"
    assert DEFAULT_CONFIG_PATH.parent.name == "config"


def test_load_pipeline_config_from_custom_path(tmp_path):
    custom = tmp_path / "custom.yaml"
    custom.write_text(
        "hrw:\n"
        '  feed_url: "https://example.org/rss"\n'
        "  feed_cache_ttl_hours: 2\n"
        "  article_cache_ttl_hours: 48\n",
        encoding="utf-8",
    )

    config = load_pipeline_config(custom)

    assert config.hrw.feed_url == "https://example.org/rss"
    assert config.hrw.feed_cache_ttl_hours == 2
    assert config.hrw.article_cache_ttl_hours == 48
