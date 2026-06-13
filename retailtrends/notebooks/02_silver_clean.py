# Databricks notebook source
# MAGIC %md
# MAGIC # 🥈 Silver Layer — Cleaning & Validation
# MAGIC Reads from the **Bronze Delta table**, applies data quality rules, casts types, removes duplicates, and writes clean data to the **Silver Delta table**.
# MAGIC
# MAGIC **Quality rules applied:**
# MAGIC - Drop rows where `interest_value` is NULL or < 0
# MAGIC - Drop rows where `keyword` or `date` is NULL
# MAGIC - Cast `date` from string → `DateType`
# MAGIC - Deduplicate on `(date, keyword, geo)`
# MAGIC - Add `cleaned_at` audit timestamp
# MAGIC

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import DateType, IntegerType
import yaml
from pathlib import Path

# ── Unity Catalog coordinates (from config/delta.yml) ──────────
_delta    = yaml.safe_load(Path("/Workspace/Shared/databricksontos/config/delta.yml").read_text())
UC        = _delta["unity_catalog"]
UC_CATALOG = UC["catalog"]
UC_SCHEMA  = UC["schema"]
BASE_PATH  = _delta["delta"]["base_path"]

# ── UC detection ───────────────────────────────────────────────
def _uc_enabled(spark):
    try:
        spark.sql("SHOW CATALOGS")
        return True
    except Exception:
        return False

UC_ENABLED = _uc_enabled(spark)

if UC_ENABLED:
    BRONZE_TABLE = f"{UC_CATALOG}.{UC_SCHEMA}.{_delta['tables']['bronze']}"
    SILVER_TABLE = f"{UC_CATALOG}.{UC_SCHEMA}.{_delta['tables']['silver']}"
    BRONZE_PATH  = None
    SILVER_PATH  = None
    spark.sql(f"USE CATALOG `{UC_CATALOG}`")
    spark.sql(f"USE SCHEMA  `{UC_SCHEMA}`")
    print("✅ Unity Catalog enabled")
else:
    BRONZE_TABLE = f"default.{_delta['tables']['bronze']}"
    SILVER_TABLE = f"default.{_delta['tables']['silver']}"
    BRONZE_PATH  = f"{BASE_PATH}/{_delta['tables']['bronze']}"
    SILVER_PATH  = f"{BASE_PATH}/{_delta['tables']['silver']}"
    spark.sql("USE DATABASE default")
    print("⚠️  Unity Catalog NOT enabled — using Hive metastore + path-based Delta")

print(f"UC enabled    : {UC_ENABLED}")
print(f"Bronze source : {BRONZE_TABLE}")
print(f"Silver target : {SILVER_TABLE}")


# COMMAND ----------

# DBTITLE 1,Read Bronze Table
# ── Read Bronze Table ──────────────────────────────────────────
if UC_ENABLED:
    bronze_df = spark.table(BRONZE_TABLE)
else:
    bronze_df = spark.read.format("delta").load(BRONZE_PATH)

print(f"📥 Bronze rows (raw)  : {bronze_df.count():,}")
bronze_df.printSchema()
display(bronze_df.limit(5))


# COMMAND ----------

# ── Data Quality Checks ────────────────────────────────────────
total_rows     = bronze_df.count()
null_keyword   = bronze_df.filter(F.col("keyword").isNull()).count()
null_date      = bronze_df.filter(F.col("date").isNull()).count()
null_interest  = bronze_df.filter(F.col("interest_value").isNull()).count()
neg_interest   = bronze_df.filter(F.col("interest_value") < 0).count()
duplicates     = total_rows - bronze_df.dropDuplicates(["date", "keyword", "geo"]).count()

print("📋 Data Quality Report — Bronze")
print(f"   Total rows          : {total_rows:,}")
print(f"   Null keyword        : {null_keyword:,}")
print(f"   Null date           : {null_date:,}")
print(f"   Null interest_value : {null_interest:,}")
print(f"   Negative interest   : {neg_interest:,}")
print(f"   Duplicates          : {duplicates:,}")
print(f"   Expected silver rows: {total_rows - null_keyword - null_date - null_interest - neg_interest - duplicates:,}")


# COMMAND ----------

# ── Apply Transformations ──────────────────────────────────────
silver_df = (
    bronze_df
    # 1. Cast date string → DateType
    .withColumn("date", F.to_date(F.col("date")))
    # 2. Cast interest_value → IntegerType (handles string edge cases)
    .withColumn("interest_value", F.col("interest_value").cast(IntegerType()))
    # 3. Normalise keyword: trim whitespace, lowercase
    .withColumn("keyword", F.trim(F.lower(F.col("keyword"))))
    # 4. Drop nulls on critical columns
    .filter(F.col("date").isNotNull())
    .filter(F.col("keyword").isNotNull())
    .filter(F.col("interest_value").isNotNull())
    .filter(F.col("interest_value") >= 0)
    # 5. Deduplicate
    .dropDuplicates(["date", "keyword", "geo"])
    # 6. Add audit column
    .withColumn("cleaned_at", F.current_timestamp())
    # 7. Select final columns
    .select(
        "date", "keyword", "interest_value",
        "geo", "category", "ingested_at", "cleaned_at"
    )
)

print(f"✅ Silver rows after cleaning: {silver_df.count():,}")
display(silver_df.limit(10))


# COMMAND ----------

# ── Upsert to Silver Delta Table ───────────────────────────────
from delta.tables import DeltaTable

def upsert_silver(new_df, table_name: str, table_path: str = None):
    """
    Upsert into a Delta table.
    Uses table name for UC, or path + Hive registration for non-UC.
    Merge key: (date, keyword, geo).
    """
    # Determine if the table already exists as a Delta table
    if table_path:
        exists = DeltaTable.isDeltaTable(spark, table_path)
    else:
        exists = DeltaTable.isDeltaTable(spark, table_name)

    if exists:
        tbl = DeltaTable.forName(spark, table_name) if not table_path else DeltaTable.forPath(spark, table_path)
        (
            tbl.alias("target")
            .merge(
                new_df.alias("source"),
                "target.date = source.date AND target.keyword = source.keyword AND target.geo = source.geo"
            )
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
        print(f"🔄 Upserted → {table_name}")
    else:
        if table_path:
            new_df.write.format("delta").mode("overwrite").save(table_path)
            spark.sql(f"""
                CREATE TABLE IF NOT EXISTS {table_name}
                USING DELTA LOCATION '{table_path}'
            """)
        else:
            new_df.write.format("delta").mode("overwrite").saveAsTable(table_name)
        print(f"✅ Created  → {table_name}")

upsert_silver(silver_df, SILVER_TABLE, SILVER_PATH)


# COMMAND ----------

# DBTITLE 1,Verify Silver Table
# ── Verify Silver Table ────────────────────────────────────────
if UC_ENABLED:
    silver_verify = spark.table(SILVER_TABLE)
else:
    silver_verify = spark.read.format("delta").load(SILVER_PATH)

print(f"📋 Silver table row count : {silver_verify.count():,}")

display(
    silver_verify
    .groupBy("category")
    .agg(
        F.count("*").alias("rows"),
        F.countDistinct("keyword").alias("unique_keywords"),
        F.min("date").alias("earliest_date"),
        F.max("date").alias("latest_date"),
        F.avg("interest_value").alias("avg_interest"),
    )
    .orderBy("category")
)
