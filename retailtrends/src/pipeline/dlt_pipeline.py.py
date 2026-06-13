# Databricks notebook source
"""
Databricks Delta Live Tables (DLT) Pipeline
Declarative Bronze → Silver → Gold pipeline using @dlt.table decorators.
All table names and config sourced from config/pipeline.yml + config/delta.yml.
Deploy this file as a DLT pipeline source in Databricks.

Unity Catalog target:
    retail_warehouse.google_trends.bronze_raw_trends
    retail_warehouse.google_trends.silver_clean_trends
    retail_warehouse.google_trends.gold_trade_scale
"""

import dlt
import time
import pandas as pd
from pytrends.request import TrendReq
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

# ── Config from YAML files ────────────────────────────────────
from src.utils.settings import pipeline, delta

RETAIL_CATEGORIES = pipeline.retail_categories   # {category: [keywords]}
GEO               = pipeline.geo
TIMEFRAME         = pipeline.timeframe

# ── Unity Catalog coordinates ─────────────────────────────────
UC_CATALOG = delta.catalog   # "retail_warehouse"
UC_SCHEMA  = delta.schema    # "google_trends"
BRONZE     = delta.tables["bronze"]   # short name for dlt.read()
SILVER     = delta.tables["silver"]
GOLD       = delta.tables["gold"]


# ── Helper ─────────────────────────────────────────────────────
def _fetch_trends(keywords: list, geo=GEO, timeframe=TIMEFRAME) -> pd.DataFrame:
    """Fetch interest_over_time in chunks of 5 (Google API limit)."""
    client = TrendReq(hl="en-US", tz=360, timeout=(10, 25), retries=3, backoff_factor=1)
    frames = []
    for i in range(0, len(keywords), 5):
        chunk = keywords[i : i + 5]
        try:
            client.build_payload(chunk, cat=0, timeframe=timeframe, geo=geo)
            df = client.interest_over_time()
            if not df.empty:
                df = (
                    df.drop(columns=["isPartial"], errors="ignore")
                      .reset_index()
                      .melt(id_vars=["date"], var_name="keyword", value_name="interest_value")
                )
                df["geo"] = geo
                frames.append(df)
        except Exception as exc:
            print(f"  ⚠️  {chunk}: {exc}")
            time.sleep(6)
        time.sleep(2)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ══════════════════════════════════════════════════════════════
# BRONZE — Raw ingestion
# Target: retail_warehouse.google_trends.bronze_raw_trends
# ══════════════════════════════════════════════════════════════
@dlt.table(
    name=BRONZE,
    catalog=UC_CATALOG,
    database=UC_SCHEMA,
    comment=f"Raw Google Trends data — {UC_CATALOG}.{UC_SCHEMA}.{BRONZE}",
    table_properties={
        "quality":                    "bronze",
        "pipelines.reset.allowed":    "true",
    },
)
def bronze_raw_trends():
    all_records = []
    for category, keywords in RETAIL_CATEGORIES.items():
        df = _fetch_trends(keywords)
        if not df.empty:
            df["category"] = category
            all_records.append(df)
        time.sleep(3)

    combined = pd.concat(all_records, ignore_index=True)
    combined["date"] = combined["date"].astype(str)
    return (
        spark.createDataFrame(combined)
             .withColumn("ingested_at", F.current_timestamp())
    )


# ══════════════════════════════════════════════════════════════
# SILVER — Cleaned & validated
# Target: retail_warehouse.google_trends.silver_clean_trends
# ══════════════════════════════════════════════════════════════
@dlt.table(
    name=SILVER,
    catalog=UC_CATALOG,
    database=UC_SCHEMA,
    comment=f"Cleaned Google Trends data — {UC_CATALOG}.{UC_SCHEMA}.{SILVER}",
    table_properties={"quality": "silver"},
)
@dlt.expect_or_drop("valid_interest", "interest_value >= 0")
@dlt.expect_or_drop("valid_keyword",  "keyword IS NOT NULL")
@dlt.expect_or_drop("valid_date",     "date IS NOT NULL")
def silver_clean_trends():
    return (
        dlt.read(BRONZE)
           .withColumn("date",           F.to_date(F.col("date")))
           .withColumn("interest_value", F.col("interest_value").cast("int"))
           .withColumn("keyword",        F.trim(F.lower(F.col("keyword"))))
           .filter(F.col("interest_value") > 0)
           .dropDuplicates(["date", "keyword", "geo"])
           .withColumn("cleaned_at", F.current_timestamp())
    )


# ══════════════════════════════════════════════════════════════
# GOLD — Trade scale aggregations
# Target: retail_warehouse.google_trends.gold_trade_scale
# ══════════════════════════════════════════════════════════════
@dlt.table(
    name=GOLD,
    catalog=UC_CATALOG,
    database=UC_SCHEMA,
    comment=f"Monthly retail trend aggregations — {UC_CATALOG}.{UC_SCHEMA}.{GOLD}",
    table_properties={"quality": "gold"},
)
def gold_trade_scale():
    window_yoy = Window.partitionBy("keyword", "geo").orderBy("month")

    return (
        dlt.read(SILVER)
           .withColumn("month", F.date_trunc("month", F.col("date")))
           .groupBy("month", "category", "keyword", "geo")
           .agg(
               F.round(F.avg("interest_value"), 2).alias("avg_interest"),
               F.max("interest_value").alias("peak_interest"),
               F.min("interest_value").alias("min_interest"),
               F.count("*").alias("data_points"),
           )
           .withColumn(
               "prev_year_interest",
               F.lag("avg_interest", 12).over(window_yoy)
           )
           .withColumn(
               "yoy_growth_pct",
               F.round(
                   (F.col("avg_interest") - F.col("prev_year_interest"))
                   / F.col("prev_year_interest") * 100, 2
               )
           )
           .withColumn("updated_at", F.current_timestamp())
           .orderBy("month", "category")
    )
