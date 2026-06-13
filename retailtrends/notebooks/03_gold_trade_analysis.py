# Databricks notebook source
# MAGIC %md
# MAGIC # 🥇 Gold Layer — Retail Trade Scale Analysis
# MAGIC Reads from the **Silver Delta table**, produces aggregated analytical views, and writes the **Gold Delta table**.
# MAGIC
# MAGIC **Analyses included:**
# MAGIC 1. 📅 Monthly trend index per keyword & category
# MAGIC 2. 🗺️ Regional interest breakdown (trade scale heatmap)
# MAGIC 3. 🏆 Top-performing keywords by category
# MAGIC 4. 📈 Year-over-year growth signals
# MAGIC 5. 📊 Interactive Plotly visualisations
# MAGIC

# COMMAND ----------

# MAGIC %pip install plotly==5.22.0 --quiet
# MAGIC
# MAGIC import pandas as pd
# MAGIC import plotly.express as px
# MAGIC import plotly.graph_objects as go
# MAGIC from plotly.subplots import make_subplots
# MAGIC from pyspark.sql import functions as F
# MAGIC from pyspark.sql.window import Window
# MAGIC import yaml
# MAGIC from pathlib import Path
# MAGIC
# MAGIC # ── Unity Catalog coordinates (from config/delta.yml) ──────────
# MAGIC _delta    = yaml.safe_load(Path("/Workspace/Shared/databricksontos/config/delta.yml").read_text())
# MAGIC UC        = _delta["unity_catalog"]
# MAGIC UC_CATALOG = UC["catalog"]
# MAGIC UC_SCHEMA  = UC["schema"]
# MAGIC BASE_PATH  = _delta["delta"]["base_path"]
# MAGIC
# MAGIC # ── UC detection ───────────────────────────────────────────────
# MAGIC def _uc_enabled(spark):
# MAGIC     try:
# MAGIC         spark.sql("SHOW CATALOGS")
# MAGIC         return True
# MAGIC     except Exception:
# MAGIC         return False
# MAGIC
# MAGIC UC_ENABLED = _uc_enabled(spark)
# MAGIC
# MAGIC if UC_ENABLED:
# MAGIC     SILVER_TABLE = f"{UC_CATALOG}.{UC_SCHEMA}.{_delta['tables']['silver']}"
# MAGIC     GOLD_TABLE   = f"{UC_CATALOG}.{UC_SCHEMA}.{_delta['tables']['gold']}"
# MAGIC     SILVER_PATH  = None
# MAGIC     GOLD_PATH    = None
# MAGIC     spark.sql(f"USE CATALOG `{UC_CATALOG}`")
# MAGIC     spark.sql(f"USE SCHEMA  `{UC_SCHEMA}`")
# MAGIC     print("✅ Unity Catalog enabled")
# MAGIC else:
# MAGIC     SILVER_TABLE = f"default.{_delta['tables']['silver']}"
# MAGIC     GOLD_TABLE   = f"default.{_delta['tables']['gold']}"
# MAGIC     SILVER_PATH  = f"{BASE_PATH}/{_delta['tables']['silver']}"
# MAGIC     GOLD_PATH    = f"{BASE_PATH}/{_delta['tables']['gold']}"
# MAGIC     spark.sql("USE DATABASE default")
# MAGIC     print("⚠️  Unity Catalog NOT enabled — using Hive metastore + path-based Delta")
# MAGIC
# MAGIC print(f"UC enabled    : {UC_ENABLED}")
# MAGIC print(f"Silver source : {SILVER_TABLE}")
# MAGIC print(f"Gold   target : {GOLD_TABLE}")
# MAGIC

# COMMAND ----------

# DBTITLE 1,Read Silver Table
# ── Read Silver Table ──────────────────────────────────────────
if UC_ENABLED:
    silver_df = spark.table(SILVER_TABLE)
else:
    silver_df = spark.read.format("delta").load(SILVER_PATH)

print(f"📥 Silver rows loaded: {silver_df.count():,}")

# ── 1. Monthly Trend Index ─────────────────────────────────────
monthly_df = (
    silver_df
    .withColumn("month", F.date_trunc("month", F.col("date")))
    .groupBy("month", "category", "keyword", "geo")
    .agg(
        F.round(F.avg("interest_value"), 2).alias("avg_interest"),
        F.max("interest_value").alias("peak_interest"),
        F.min("interest_value").alias("min_interest"),
        F.count("*").alias("data_points"),
    )
    .orderBy("month", "category", F.desc("avg_interest"))
)

print(f"📅 Monthly aggregation rows: {monthly_df.count():,}")
display(monthly_df.limit(10))


# COMMAND ----------

# ── 2. Year-over-Year Growth Signal ───────────────────────────
window_yoy = Window.partitionBy("keyword", "geo").orderBy("month")

yoy_df = (
    monthly_df
    .withColumn(
        "prev_year_interest",
        F.lag("avg_interest", 12).over(window_yoy)
    )
    .withColumn(
        "yoy_growth_pct",
        F.round(
            (F.col("avg_interest") - F.col("prev_year_interest"))
            / F.col("prev_year_interest") * 100,
            2
        )
    )
    .filter(F.col("prev_year_interest").isNotNull())
)

print(f"📈 YoY growth rows: {yoy_df.count():,}")
display(
    yoy_df
    .orderBy(F.desc("yoy_growth_pct"))
    .select("month", "category", "keyword", "avg_interest", "yoy_growth_pct")
    .limit(20)
)


# COMMAND ----------

# ── 3. Top Keywords by Category (Trade Scale Ranking) ─────────
window_rank = Window.partitionBy("category").orderBy(F.desc("overall_avg"))

top_keywords_df = (
    silver_df
    .groupBy("category", "keyword")
    .agg(
        F.round(F.avg("interest_value"), 2).alias("overall_avg"),
        F.max("interest_value").alias("all_time_peak"),
        F.countDistinct("date").alias("active_weeks"),
    )
    .withColumn("rank", F.rank().over(window_rank))
    .filter(F.col("rank") <= 5)
    .orderBy("category", "rank")
)

print("🏆 Top 5 Keywords per Category:")
display(top_keywords_df)


# COMMAND ----------

# ── Write Gold Delta Table ─────────────────────────────────────
gold_df = (
    yoy_df
    .withColumn("updated_at", F.current_timestamp())
    .select(
        "month", "category", "keyword", "geo",
        "avg_interest", "peak_interest", "min_interest",
        "data_points", "yoy_growth_pct", "updated_at"
    )
)

if UC_ENABLED:
    (
        gold_df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(GOLD_TABLE)
    )
else:
    (
        gold_df.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .save(GOLD_PATH)
    )
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {GOLD_TABLE}
        USING DELTA LOCATION '{GOLD_PATH}'
    """)

print(f"✅ Gold table written : {GOLD_TABLE}")
print(f"   Rows               : {gold_df.count():,}")


# COMMAND ----------

# MAGIC %md
# MAGIC ## 📊 Visualisations
# MAGIC

# COMMAND ----------

# DBTITLE 1,Chart 1: Monthly Interest Trend Lines by Category
# ── Chart 1: Monthly Interest Trend Lines by Category ──────────
if UC_ENABLED:
    gold_pd = spark.table(GOLD_TABLE).toPandas()
else:
    gold_pd = spark.read.format("delta").load(GOLD_PATH).toPandas()

gold_pd["month"] = pd.to_datetime(gold_pd["month"])

fig = px.line(
    gold_pd,
    x="month",
    y="avg_interest",
    color="keyword",
    facet_col="category",
    facet_col_wrap=2,
    title="📈 Google Trends — Monthly Interest by Retail Category",
    labels={"avg_interest": "Avg Interest (0–100)", "month": "Month"},
    height=700,
)
fig.update_layout(
    legend_title_text="Keyword",
    hovermode="x unified",
    template="plotly_white",
)
fig.show()


# COMMAND ----------

# ── Chart 2: Year-over-Year Growth Heatmap ─────────────────────
latest_yoy = (
    gold_pd.dropna(subset=["yoy_growth_pct"])
    .sort_values("month")
    .groupby(["category", "keyword"], as_index=False)
    .last()
)

fig2 = px.bar(
    latest_yoy.sort_values("yoy_growth_pct", ascending=False),
    x="keyword",
    y="yoy_growth_pct",
    color="category",
    barmode="group",
    title="📊 Year-over-Year Growth % — Latest Period",
    labels={"yoy_growth_pct": "YoY Growth (%)", "keyword": "Keyword"},
    height=500,
    template="plotly_white",
)
fig2.add_hline(y=0, line_dash="dot", line_color="grey")
fig2.show()

# ── Chart 3: Trade Scale Bubble Chart ─────────────────────────
top_kw_pd = top_keywords_df.toPandas()

fig3 = px.scatter(
    top_kw_pd,
    x="overall_avg",
    y="all_time_peak",
    size="active_weeks",
    color="category",
    hover_name="keyword",
    text="keyword",
    title="🌐 Trade Scale — Interest vs Peak vs Active Weeks",
    labels={
        "overall_avg":   "Avg Interest (0–100)",
        "all_time_peak": "All-time Peak Interest",
        "active_weeks":  "Active Weeks",
    },
    height=550,
    template="plotly_white",
)
fig3.update_traces(textposition="top center")
fig3.show()
