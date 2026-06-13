# Databricks notebook source
# MAGIC %md
# MAGIC # 🥉 Bronze Layer — Raw Google Trends Ingestion
# MAGIC This notebook installs dependencies, fetches raw Google Trends data using **pytrends**, and writes it to the **Bronze Delta table**.
# MAGIC
# MAGIC **Pipeline**: `Bronze → Silver → Gold`
# MAGIC
# MAGIC | Layer | Purpose |
# MAGIC |---|---|
# MAGIC | 🥉 **Bronze** | Raw ingestion — this notebook |
# MAGIC | 🥈 **Silver** | Cleaning & validation |
# MAGIC | 🥇 **Gold**   | Aggregations for trade-scale analysis |
# MAGIC

# COMMAND ----------

# Install required packages (Databricks cluster-scoped)
%pip install pytrends==4.9.2 pandas==2.2.2 delta-spark==3.2.0 --quiet


# COMMAND ----------

import sys
import time
import pandas as pd

from pytrends.request import TrendReq
from pyspark.sql.functions import current_timestamp, lit
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, TimestampType,
)

# ── Databricks: spark & dbutils are auto-provided by the runtime ──
print(f"Spark version : {spark.version}")
print(f"Python version: {sys.version}")


# COMMAND ----------

# ── Configuration — sourced entirely from config/delta.yml + config/pipeline.yml ──
dbutils.widgets.text("geo",       "US",         "Primary Geo")
dbutils.widgets.text("timeframe", "today 12-m", "Timeframe")

import yaml
from pathlib import Path

_CONF = Path("/Workspace/Shared/databricksontos/config")

_pipeline = yaml.safe_load((_CONF / "pipeline.yml").read_text())
_delta    = yaml.safe_load((_CONF / "delta.yml").read_text())

RETAIL_CATEGORIES = _pipeline.get("retail_categories", {})
GEO               = dbutils.widgets.get("geo")       or _pipeline["geo"]["primary"]
TIMEFRAME         = dbutils.widgets.get("timeframe") or _pipeline["collector"]["timeframe"]
SLEEP_SECONDS     = float(_pipeline["collector"].get("sleep_seconds", 2.0))

# ── Unity Catalog detection ────────────────────────────────────
def _uc_enabled(spark):
    try:
        spark.sql("SHOW CATALOGS")
        return True
    except Exception:
        return False

UC_ENABLED = _uc_enabled(spark)

UC         = _delta["unity_catalog"]
UC_CATALOG = UC["catalog"]
UC_SCHEMA  = UC["schema"]
BASE_PATH  = _delta["delta"]["base_path"]

if UC_ENABLED:
    BRONZE_TABLE = f"{UC_CATALOG}.{UC_SCHEMA}.{_delta['tables']['bronze']}"
    BRONZE_PATH  = None
    print("✅ Unity Catalog enabled — using 3-part table name")
else:
    BRONZE_TABLE = f"default.{_delta['tables']['bronze']}"
    BRONZE_PATH  = f"{BASE_PATH}/{_delta['tables']['bronze']}"
    print("⚠️  Unity Catalog NOT enabled — using Hive metastore + path-based Delta")

print(f"✅ Config loaded")
print(f"   UC enabled : {UC_ENABLED}")
print(f"   Table      : {BRONZE_TABLE}")
print(f"   Categories : {list(RETAIL_CATEGORIES.keys())}")
print(f"   Geo / TF   : {GEO} / {TIMEFRAME}")


# COMMAND ----------

# ── Google Trends Collector Class ─────────────────────────────
class GoogleTrendsCollector:
    """
    Fetches Google Trends data via pytrends.
    - Auto-chunks keywords (max 5 per request)
    - Handles rate limiting with configurable sleep
    - Returns tidy pandas DataFrames
    """

    MAX_KW = 5

    def __init__(self, geo="US", timeframe="today 5-y", sleep=2.0, retries=3):
        self.geo       = geo
        self.timeframe = timeframe
        self.sleep     = sleep
        self.client    = TrendReq(
            hl="en-US", tz=360,
            timeout=(10, 25),
            retries=retries,
            backoff_factor=1,
        )

    # ── helpers ────────────────────────────────────────────────
    def _chunks(self, lst):
        for i in range(0, len(lst), self.MAX_KW):
            yield lst[i : i + self.MAX_KW]

    # ── interest over time ─────────────────────────────────────
    def get_interest_over_time(self, keywords: list) -> pd.DataFrame:
        """Fetch weekly interest for each keyword."""
        frames = []
        for chunk in self._chunks(keywords):
            try:
                self.client.build_payload(
                    chunk, cat=0,
                    timeframe=self.timeframe, geo=self.geo
                )
                df = self.client.interest_over_time()
                if not df.empty:
                    df = (
                        df.drop(columns=["isPartial"], errors="ignore")
                          .reset_index()
                          .melt(id_vars=["date"],
                                var_name="keyword",
                                value_name="interest_value")
                    )
                    df["geo"] = self.geo
                    frames.append(df)
            except Exception as exc:
                print(f"  ⚠️  Chunk {chunk}: {exc}")
                time.sleep(self.sleep * 3)
            finally:
                time.sleep(self.sleep)

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # ── trending searches ──────────────────────────────────────
    def get_trending_searches(self, country="united_states") -> pd.DataFrame:
        """Fetch today's top trending searches."""
        try:
            return self.client.trending_searches(pn=country)
        except Exception as exc:
            print(f"  ⚠️  Trending: {exc}")
            return pd.DataFrame()

    # ── related queries ────────────────────────────────────────
    def get_related_queries(self, keywords: list) -> dict:
        """Fetch rising + top related queries."""
        try:
            self.client.build_payload(
                keywords[:self.MAX_KW],
                timeframe=self.timeframe, geo=self.geo
            )
            return self.client.related_queries()
        except Exception as exc:
            print(f"  ⚠️  Related queries: {exc}")
            return {}


print("✅ GoogleTrendsCollector class defined")


# COMMAND ----------

# ── Fetch All Retail Categories ────────────────────────────────
collector   = GoogleTrendsCollector(geo=GEO, timeframe=TIMEFRAME, sleep=SLEEP_SECONDS)
raw_frames  = []

for category, keywords in RETAIL_CATEGORIES.items():
    print(f"📥 Fetching category: {category!r}  keywords: {keywords}")
    df = collector.get_interest_over_time(keywords)

    if not df.empty:
        df["category"] = category
        raw_frames.append(df)
        print(f"   ✔  {len(df):,} rows fetched")
    else:
        print(f"   ⚠️  No data returned for {category!r}")

    time.sleep(3)   # courtesy pause between categories

combined_df = pd.concat(raw_frames, ignore_index=True) if raw_frames else pd.DataFrame()
print(f"\n📊 Total raw rows: {len(combined_df):,}")
combined_df.head(10)


# COMMAND ----------

# ── Bootstrap Catalog/Schema and Write Bronze ─────────────────
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType
from pyspark.sql.functions import current_timestamp

if UC_ENABLED:
    spark.sql(f"CREATE CATALOG  IF NOT EXISTS `{UC_CATALOG}`")
    spark.sql(f"CREATE SCHEMA   IF NOT EXISTS `{UC_CATALOG}`.`{UC_SCHEMA}`")
    spark.sql(f"USE CATALOG `{UC_CATALOG}`")
    spark.sql(f"USE SCHEMA  `{UC_SCHEMA}`")
    print(f"✅ Using UC: {UC_CATALOG}.{UC_SCHEMA}")
else:
    spark.sql("USE DATABASE default")
    print("✅ Using Hive metastore: default")

if not combined_df.empty:
    combined_df["date"] = combined_df["date"].astype(str)

    bronze_spark_df = (
        spark.createDataFrame(combined_df)
             .withColumn("ingested_at", current_timestamp())
    )

    if UC_ENABLED:
        (
            bronze_spark_df.write
            .format("delta")
            .mode("append")
            .option("mergeSchema", "true")
            .saveAsTable(BRONZE_TABLE)
        )
    else:
        # Write to path first, then register in Hive metastore
        (
            bronze_spark_df.write
            .format("delta")
            .mode("append")
            .option("mergeSchema", "true")
            .save(BRONZE_PATH)
        )
        spark.sql(f"""
            CREATE TABLE IF NOT EXISTS {BRONZE_TABLE}
            USING DELTA LOCATION '{BRONZE_PATH}'
        """)

    print(f"✅ Written → {BRONZE_TABLE}")
    print(f"   Rows   : {bronze_spark_df.count():,}")
else:
    print("⚠️  No data to write — check pytrends connectivity")


# COMMAND ----------

# DBTITLE 1,Verify Bronze Table
# ── Verify Bronze Table ────────────────────────────────────────
bronze_df = spark.table(BRONZE_TABLE)

print(f"📋 Bronze table row count : {bronze_df.count():,}")
print(f"   Schema:")
bronze_df.printSchema()

display(
    bronze_df
    .groupBy("category", "geo")
    .count()
    .orderBy("category")
)
