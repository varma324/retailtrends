"""
example_serpapi_integration.py
═══════════════════════════════════════════════════════════════
Example: Integrate SerpAPI trending data with existing pipeline

This shows how to combine SerpAPI trending data with your
existing PyTrends data and Delta Lake pipeline.
═══════════════════════════════════════════════════════════════
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd
from dotenv import load_dotenv

# Import the SerpAPI collector
from get_serpapi_trending import SerpAPITrendingCollector

# Load environment
_HERE = Path(__file__).resolve().parent
_ENV_FILE = _HERE / "retailtrends" / "config" / ".env"
load_dotenv(_ENV_FILE)
SERPAPI_KEY = os.getenv("serpAPIkey")


def collect_serpapi_trends(regions: List[str] = ["US", "GB"]) -> pd.DataFrame:
    """
    Collect trending data from multiple regions using SerpAPI.
    
    Args:
        regions: List of country codes
        
    Returns:
        DataFrame with combined trending data
    """
    all_trends = []
    
    for region in regions:
        print(f"\n📍 Collecting {region} trends...")
        
        collector = SerpAPITrendingCollector(api_key=SERPAPI_KEY, geo=region)
        data = collector.get_trending_now()
        
        if data and "trending_searches" in data:
            for search in data["trending_searches"]:
                # Extract key fields
                trend_record = {
                    "timestamp": datetime.now().isoformat(),
                    "region": region,
                    "query": search.get("query", ""),
                    "search_volume": search.get("search_volume", 0),
                    "increase_percentage": search.get("increase_percentage", 0),
                    "active": search.get("active", False),
                    "categories": ", ".join([c.get("name", "") for c in search.get("categories", [])]),
                    "related_queries": ", ".join(search.get("trend_breakdown", [])[:5]),
                }
                all_trends.append(trend_record)
    
    return pd.DataFrame(all_trends)


def enrich_pytrends_with_serpapi(
    pytrends_df: pd.DataFrame,
    serpapi_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Enrich PyTrends data with SerpAPI absolute volumes.
    
    Args:
        pytrends_df: DataFrame from PyTrends (relative interest)
        serpapi_df: DataFrame from SerpAPI (absolute volumes)
        
    Returns:
        Enriched DataFrame
    """
    # Merge on keyword/query
    enriched = pytrends_df.merge(
        serpapi_df[["query", "search_volume", "increase_percentage"]],
        left_on="keyword",
        right_on="query",
        how="left"
    )
    
    return enriched


def filter_retail_trends(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter for retail-related trending searches.
    
    Args:
        df: Trending data DataFrame
        
    Returns:
        Filtered DataFrame
    """
    retail_keywords = [
        "buy", "shop", "sale", "price", "store", "amazon", "walmart",
        "deal", "discount", "product", "shopping", "purchase", "order",
        "nike", "adidas", "apple", "samsung", "iphone", "playstation",
        "xbox", "best buy", "target", "ebay", "etsy"
    ]
    
    retail_mask = df["query"].str.lower().str.contains(
        "|".join(retail_keywords), 
        case=False, 
        na=False
    )
    
    return df[retail_mask]


def save_to_delta(df: pd.DataFrame, table_name: str = "serpapi_trends") -> None:
    """
    Save DataFrame to Delta Lake table.
    
    Args:
        df: DataFrame to save
        table_name: Name of Delta table
    """
    # This is a placeholder - adapt to your existing Delta pipeline
    print(f"\n💾 Saving {len(df)} records to Delta table: {table_name}")
    
    # Example with Delta Lake (requires delta-spark)
    # df.write.format("delta").mode("append").save(f"delta/{table_name}")
    
    # For now, save as CSV for demonstration
    output_dir = Path("demo_output/integrated")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"{table_name}_{timestamp}.csv"
    
    df.to_csv(csv_path, index=False)
    print(f"   ✓ Saved to: {csv_path}")


def example_1_basic_collection():
    """Example 1: Basic data collection from multiple regions."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Multi-Region Collection")
    print("=" * 70)
    
    regions = ["US", "GB", "DE"]
    df = collect_serpapi_trends(regions)
    
    print(f"\n✓ Collected {len(df)} trending searches")
    print(f"\nTop 5 by search volume:")
    print(df.nlargest(5, "search_volume")[["region", "query", "search_volume", "categories"]])
    
    return df


def example_2_retail_focus():
    """Example 2: Focus on retail trends."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Retail Trend Analysis")
    print("=" * 70)
    
    # Collect US trends
    df = collect_serpapi_trends(["US"])
    
    # Filter for retail
    retail_df = filter_retail_trends(df)
    
    print(f"\n✓ Found {len(retail_df)} retail-related trends")
    
    if not retail_df.empty:
        print(f"\nTop retail trends:")
        print(retail_df.nlargest(10, "search_volume")[
            ["query", "search_volume", "increase_percentage"]
        ])
    
    return retail_df


def example_3_category_analysis():
    """Example 3: Category breakdown analysis."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Category Analysis")
    print("=" * 70)
    
    df = collect_serpapi_trends(["US"])
    
    # Category distribution
    category_counts = df["categories"].value_counts()
    
    print(f"\nTop 10 categories:")
    for idx, (category, count) in enumerate(category_counts.head(10).items(), 1):
        print(f"{idx}. {category}: {count} trends")
    
    return df


def example_4_save_to_pipeline():
    """Example 4: Integrate with data pipeline."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Save to Data Pipeline")
    print("=" * 70)
    
    # Collect from multiple regions
    df = collect_serpapi_trends(["US", "GB"])
    
    # Save full dataset
    save_to_delta(df, "serpapi_trends_full")
    
    # Save retail subset
    retail_df = filter_retail_trends(df)
    if not retail_df.empty:
        save_to_delta(retail_df, "serpapi_trends_retail")
    
    return df


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("🔥 SERPAPI INTEGRATION EXAMPLES")
    print("=" * 70)
    
    # Run examples
    df1 = example_1_basic_collection()
    df2 = example_2_retail_focus()
    df3 = example_3_category_analysis()
    df4 = example_4_save_to_pipeline()
    
    print("\n" + "=" * 70)
    print("✨ All examples complete!")
    print("=" * 70)
    
    # Summary
    print(f"\nTotal records collected: {len(df1)}")
    print(f"Retail trends found: {len(df2)}")
    print(f"Regions covered: US, GB, DE")
    print(f"\nCheck 'demo_output/integrated/' for saved files")


if __name__ == "__main__":
    main()
