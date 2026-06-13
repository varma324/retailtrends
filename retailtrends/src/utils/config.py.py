# Databricks notebook source
"""
config.py  —  re-export shim
════════════════════════════════════════════════════════════════
All configuration now lives in two YAML files:

    config/pipeline.yml  →  keywords, categories, companies,
                             countries, collector settings, output
    config/delta.yml     →  Delta paths, table names, cluster,
                             schedule

Prefer importing directly from settings in new code:

    from src.utils.settings import pipeline, delta

This module re-exports the names that existing code (tests,
notebooks, dlt_pipeline) expects so nothing breaks.
"""

from src.utils.settings import (   # noqa: F401
    pipeline,
    delta,
    GPROPS,
    GOOGLE_CATEGORIES,
    TIMEFRAME_PRESETS,
    RESOLUTIONS,
    TOP_CHARTS_YEARS,
)

# ── Legacy flat names (used by tests + dlt_pipeline) ──────────
RETAIL_CATEGORIES: dict = pipeline.retail_categories
GEO_TARGETS:       dict = pipeline.countries
COMPANY_PROFILES:  dict = pipeline.company_profiles

PIPELINE_CONFIG: dict = {
    "geo":            pipeline.geo,
    "timeframe":      pipeline.timeframe,
    "gprop":          "",
    "cat":            0,
    "sleep_seconds":  pipeline.collector["sleep_seconds"],
    "retries":        pipeline.collector["retries"],
    "backoff_factor": pipeline.collector["backoff_factor"],
}

DELTA_BASE_PATH: str = delta.base_path
CATALOG_NAME:    str = delta.catalog        # "retail_warehouse"
SCHEMA_NAME:     str = delta.schema         # "google_trends"
BRONZE_TABLE:    str = delta.uc_table("bronze")   # retail_warehouse.google_trends.bronze_raw_trends
SILVER_TABLE:    str = delta.uc_table("silver")   # retail_warehouse.google_trends.silver_clean_trends
GOLD_TABLE:      str = delta.uc_table("gold")     # retail_warehouse.google_trends.gold_trade_scale
