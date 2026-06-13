# Databricks notebook source
"""
Delta Lake helpers: schema definitions, upsert/merge utilities.
All table references use Unity Catalog three-part names:
    retail_warehouse.google_trends.<table>
sourced from config/delta.yml via src.utils.settings.delta
"""

import pandas as pd
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import current_timestamp
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DateType, TimestampType,
)

# ── Schemas ───────────────────────────────────────────────────

BRONZE_SCHEMA = StructType([
    StructField("date",           StringType(),    True),
    StructField("keyword",        StringType(),    True),
    StructField("interest_value", IntegerType(),   True),
    StructField("geo",            StringType(),    True),
    StructField("category",       StringType(),    True),
    StructField("ingested_at",    TimestampType(), True),
])

SILVER_SCHEMA = StructType([
    StructField("date",           DateType(),      True),
    StructField("keyword",        StringType(),    True),
    StructField("interest_value", IntegerType(),   True),
    StructField("geo",            StringType(),    True),
    StructField("category",       StringType(),    True),
    StructField("ingested_at",    TimestampType(), True),
    StructField("cleaned_at",     TimestampType(), True),
])

GOLD_SCHEMA = StructType([
    StructField("month",               DateType(),      True),
    StructField("category",            StringType(),    True),
    StructField("keyword",             StringType(),    True),
    StructField("geo",                 StringType(),    True),
    StructField("avg_interest",        IntegerType(),   True),
    StructField("peak_interest",       IntegerType(),   True),
    StructField("min_interest",        IntegerType(),   True),
    StructField("data_points",         IntegerType(),   True),
    StructField("prev_year_interest",  IntegerType(),   True),
    StructField("yoy_growth_pct",      IntegerType(),   True),
    StructField("updated_at",          TimestampType(), True),
])

# ── Catalog helpers ───────────────────────────────────────────

def ensure_catalog(spark: SparkSession, catalog: str, schema: str) -> None:
    """
    Create the Unity Catalog catalog + schema if they do not exist.
    Idempotent — safe to call at the start of every notebook.
    """
    spark.sql(f"CREATE CATALOG IF NOT EXISTS `{catalog}`")
    spark.sql(f"CREATE SCHEMA  IF NOT EXISTS `{catalog}`.`{schema}`")
    spark.sql(f"USE CATALOG `{catalog}`")
    spark.sql(f"USE SCHEMA  `{schema}`")
    print(f"✅ Using catalog: {catalog}.{schema}")


# ── Pandas → Spark ────────────────────────────────────────────

def pandas_to_spark(
    spark:    SparkSession,
    df:       pd.DataFrame,
    category: str,
) -> DataFrame:
    """Convert pandas DataFrame to Spark, adding metadata columns."""
    from pyspark.sql.functions import lit
    spark_df = spark.createDataFrame(df)
    if "category" not in df.columns:
        spark_df = spark_df.withColumn("category", lit(category))
    return spark_df.withColumn("ingested_at", current_timestamp())


# ── Unity Catalog write helpers ───────────────────────────────

def write_to_uc_table(
    spark:      SparkSession,
    df:         pd.DataFrame,
    category:   str,
    uc_table:   str,          # e.g. "retail_warehouse.google_trends.bronze_raw_trends"
    mode:       str = "append",
) -> None:
    """
    Write a pandas DataFrame to a Unity Catalog Delta table.

    Args:
        uc_table: three-part name  catalog.schema.table
        mode:     "append" (default) or "overwrite"
    """
    spark_df = pandas_to_spark(spark, df, category)
    (
        spark_df.write
        .format("delta")
        .mode(mode)
        .option("mergeSchema", "true")
        .saveAsTable(uc_table)
    )
    print(f"  ✅ {spark_df.count():,} rows written → {uc_table}")


def upsert_to_uc_table(
    spark:      SparkSession,
    new_df:     DataFrame,
    uc_table:   str,          # e.g. "retail_warehouse.google_trends.silver_clean_trends"
    merge_keys: list,
) -> None:
    """
    Merge (upsert) a Spark DataFrame into a Unity Catalog Delta table.
    Creates the table on first run.

    Args:
        uc_table:   three-part UC name
        merge_keys: columns used as the merge condition
    """
    from delta.tables import DeltaTable

    if DeltaTable.isDeltaTable(spark, uc_table):
        delta_tbl = DeltaTable.forName(spark, uc_table)
        condition = " AND ".join(
            f"target.{k} = source.{k}" for k in merge_keys
        )
        (
            delta_tbl.alias("target")
            .merge(new_df.alias("source"), condition)
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
        print(f"  🔄 Upserted → {uc_table}")
    else:
        new_df.write.format("delta").mode("overwrite").saveAsTable(uc_table)
        print(f"  ✅ Created  → {uc_table}")


# ── Legacy path-based helpers (kept for backward compatibility) ──

def write_to_delta(
    spark:      SparkSession,
    df:         pd.DataFrame,
    category:   str,
    table_path: str,
    mode:       str = "append",
) -> None:
    """Write pandas DataFrame to Delta path (non-UC). Use write_to_uc_table for new code."""
    spark_df = pandas_to_spark(spark, df, category)
    (
        spark_df.write
        .format("delta")
        .mode(mode)
        .option("mergeSchema", "true")
        .save(table_path)
    )
    print(f"  ✅ Written {spark_df.count()} rows → {table_path}")


def upsert_to_delta(
    spark:      SparkSession,
    new_df:     DataFrame,
    table_path: str,
    merge_keys: list,
) -> None:
    """Upsert to Delta path (non-UC). Use upsert_to_uc_table for new code."""
    from delta.tables import DeltaTable

    if DeltaTable.isDeltaTable(spark, table_path):
        delta_table = DeltaTable.forPath(spark, table_path)
        condition   = " AND ".join(
            f"target.{k} = source.{k}" for k in merge_keys
        )
        (
            delta_table.alias("target")
            .merge(new_df.alias("source"), condition)
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
        print(f"  🔄 Upserted → {table_path}")
    else:
        new_df.write.format("delta").mode("overwrite").save(table_path)
        print(f"  ✅ Created  → {table_path}")
