# Databricks notebook source
"""
Settings loader
═══════════════════════════════════════════════════════════════
Loads config/pipeline.yml and config/delta.yml once at import
time and exposes two typed singletons:

    pipeline  →  PipelineSettings  (keywords, geo, collector …)
    delta     →  DeltaSettings     (paths, tables, schedule …)

Usage
─────
    from src.utils.settings import pipeline, delta

    # Pass collector kwargs directly from config
    collector = GoogleTrendsCollector(**pipeline.collector)

    # Categorised keyword dict (for DLT pipeline loops)
    for category, kws in pipeline.retail_categories.items():
        df = collector.get_interest_over_time(kws)

    # Flat keyword list (for demo / single-run calls)
    data = collector.get_complete_dataset(
        keywords=pipeline.keywords,
        geo=pipeline.geo,
        multi_countries=pipeline.countries,
        **pipeline.output_options,
    )

    # Delta table helpers
    spark.read.format("delta").table(delta.tables["silver"])
    delta.table_path("bronze")   # -> "/mnt/delta/google_trends/bronze_raw_trends"

Static API constants (values that never change across environments)
are defined at the bottom of this file:  GPROPS, GOOGLE_CATEGORIES,
TIMEFRAME_PRESETS, RESOLUTIONS, TOP_CHARTS_YEARS.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

# ── Locate config directory ───────────────────────────────────
_ROOT       = Path(__file__).resolve().parent.parent.parent
_CONFIG_DIR = _ROOT / "config"


def _load(filename: str) -> Dict[str, Any]:
    """Load and return a YAML file from config/."""
    path = _CONFIG_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path.absolute()}\n"
            "Check that config/ exists at the project root."
        )
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


# ══════════════════════════════════════════════════════════════
# PipelineSettings  —  pipeline.yml
# ══════════════════════════════════════════════════════════════

class PipelineSettings:
    """
    Typed wrapper around config/pipeline.yml.

    All attributes map directly to top-level YAML keys so adding
    a new setting only requires an edit to pipeline.yml.
    """

    def __init__(self, raw: Dict[str, Any]) -> None:
        self._raw = raw

        # ── collector kwargs → passed straight to GoogleTrendsCollector() ──
        col = raw.get("collector", {})
        self.collector: Dict[str, Any] = {
            "geo":            col.get("geo",            "US"),
            "timeframe":      col.get("timeframe",      "today 12-m"),
            "sleep_seconds":  float(col.get("sleep_seconds", 2.0)),
            "retries":        int(col.get("retries",        3)),
            "backoff_factor": int(col.get("backoff_factor",  1)),
        }

        # ── retail_categories: {category: [keywords]} ──────────
        self.retail_categories: Dict[str, List[str]] = raw.get("retail_categories", {})

        # ── company_profiles: {name: {category, keyword}} ──────
        self.company_profiles: Dict[str, Dict[str, str]] = raw.get("company_profiles", {})

        # ── primary geography ───────────────────────────────────
        self.geo: str = raw.get("geo", {}).get("primary", "US")

        # ── countries for multi-country comparison ──────────────
        self.countries: Dict[str, str] = raw.get("countries", {})

        # ── output ─────────────────────────────────────────────
        out = raw.get("output", {})
        self.output_dir: Path = _ROOT / out.get("dir", "demo_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.output_options: Dict[str, Any] = {
            "include_geo_breakdown": bool(out.get("include_geo_breakdown", True)),
            "include_related":       bool(out.get("include_related",       True)),
            "include_worldwide":     bool(out.get("include_worldwide",     True)),
            "resolutions":           list(out.get("resolutions", ["REGION", "CITY"])),
        }

    @property
    def keywords(self) -> List[str]:
        """Flat list of every keyword across all retail_categories."""
        return [kw for kws in self.retail_categories.values() for kw in kws]

    @property
    def timeframe(self) -> str:
        """Convenience shortcut for the collector timeframe."""
        return self.collector["timeframe"]

    def __repr__(self) -> str:
        cats = list(self.retail_categories.keys())
        return (
            f"PipelineSettings("
            f"categories={cats}, "
            f"keywords={len(self.keywords)}, "
            f"geo={self.geo!r}, "
            f"timeframe={self.timeframe!r})"
        )


# ══════════════════════════════════════════════════════════════
# DeltaSettings  —  delta.yml
# ══════════════════════════════════════════════════════════════

class DeltaSettings:
    """
    Typed wrapper around config/delta.yml.

    Unity Catalog coordinates
    ─────────────────────────
    catalog  : retail_warehouse
    schema   : google_trends
    tables   : retail_warehouse.google_trends.<name>

    Helpers
    ───────
    delta.uc_table("bronze")
        → "retail_warehouse.google_trends.bronze_raw_trends"
    delta.storage_path("silver")
        → "/mnt/delta/retail_warehouse/google_trends/silver_clean_trends"
    """

    def __init__(self, raw: Dict[str, Any]) -> None:
        self._raw = raw

        # ── Unity Catalog ──────────────────────────────────────
        uc = raw.get("unity_catalog", {})
        self.catalog: str = uc.get("catalog", "retail_warehouse")
        self.schema:  str = uc.get("schema",  "google_trends")

        # ── Table short names ──────────────────────────────────
        self.tables: Dict[str, str] = raw.get("tables", {
            "bronze": "bronze_raw_trends",
            "silver": "silver_clean_trends",
            "gold":   "gold_trade_scale",
        })

        # ── External storage path (fallback) ──────────────────
        d = raw.get("delta", {})
        self.base_path: str = d.get(
            "base_path",
            f"/mnt/delta/{self.catalog}/{self.schema}",
        )

        self.cluster:  Dict[str, Any] = raw.get("cluster",  {})
        self.schedule: Dict[str, Any] = raw.get("schedule", {})

    def uc_table(self, layer: str) -> str:
        """
        Fully-qualified Unity Catalog table name.
        e.g. delta.uc_table("bronze")
             → "retail_warehouse.google_trends.bronze_raw_trends"
        """
        return f"{self.catalog}.{self.schema}.{self.tables[layer]}"

    def storage_path(self, layer: str) -> str:
        """
        External Delta storage path (used when UC external
        locations are not configured).
        e.g. delta.storage_path("bronze")
             → "/mnt/delta/retail_warehouse/google_trends/bronze_raw_trends"
        """
        return f"{self.base_path}/{self.tables[layer]}"

    # Keep old name as alias for backward compatibility
    def table_path(self, layer: str) -> str:
        return self.storage_path(layer)

    def __repr__(self) -> str:
        return (
            f"DeltaSettings("
            f"catalog={self.catalog!r}, "
            f"schema={self.schema!r}, "
            f"tables={list(self.tables.values())})"
        )


# ══════════════════════════════════════════════════════════════
# Module-level singletons — import these everywhere
# ══════════════════════════════════════════════════════════════

pipeline = PipelineSettings(_load("pipeline.yml"))
delta    = DeltaSettings(_load("delta.yml"))


# ══════════════════════════════════════════════════════════════
# Static API constants
# Values that are fixed by the Google Trends / pytrends API and
# never change across environments. Import from here, not config.py.
# ══════════════════════════════════════════════════════════════

# Google search surfaces
GPROPS: Dict[str, str] = {
    "web":      "",          # Standard web search (default)
    "images":   "images",    # Google Image Search
    "news":     "news",      # Google News
    "youtube":  "youtube",   # YouTube Search
    "shopping": "froogle",   # Google Shopping
}

# Google Trends category IDs (retail-relevant subset)
# Full tree: collector.get_categories()
GOOGLE_CATEGORIES: Dict[str, int] = {
    "all":         0,
    "arts":        3,
    "beauty":      44,
    "business":    12,
    "computers":   5,
    "electronics": 442,
    "fashion":     185,
    "finance":     7,
    "food":        71,
    "games":       8,
    "health":      45,
    "home":        11,
    "movies":      34,
    "music":       35,
    "news":        16,
    "shopping":    18,
    "sports":      20,
    "travel":      67,
}

# Human-friendly timeframe presets → pytrends strings
TIMEFRAME_PRESETS: Dict[str, str] = {
    "1h":  "now 1-H",
    "4h":  "now 4-H",
    "1d":  "now 1-d",
    "7d":  "now 7-d",
    "1m":  "today 1-m",
    "3m":  "today 3-m",
    "12m": "today 12-m",
    "5y":  "today 5-y",
    "all": "all",
}

# Valid geographic resolution levels
RESOLUTIONS: List[str] = ["COUNTRY", "REGION", "CITY", "DMA"]

# Years available in Top Charts
TOP_CHARTS_YEARS: List[int] = [2021, 2022, 2023, 2024, 2025]
