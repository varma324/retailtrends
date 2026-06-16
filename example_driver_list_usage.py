"""
Example: Using the Trends Driver List
═════════════════════════════════════════════════════════════
This script demonstrates how to use trend_categories.py
programmatically to build automated trend analysis pipelines.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from retailtrends.src.collectors.trend_categories import (
    fetch_trending_searches,
    fetch_categories,
    fetch_realtime_trending,
    build_dataframe,
    build_driver_list,
    filter_retail_relevant,
)


def example_1_get_trending_searches():
    """Example 1: Get trending searches from multiple countries."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Trending Searches from Multiple Countries")
    print("="*60)
    
    countries = ["United States", "Germany", "Japan"]
    trending_df = fetch_trending_searches(countries=countries)
    
    if not trending_df.empty:
        print(f"\n✅ Collected {len(trending_df)} trending searches")
        print("\nTop 5 trends per country:")
        for country in countries:
            country_trends = trending_df[trending_df['country'] == country].head(5)
            print(f"\n{country}:")
            for _, row in country_trends.iterrows():
                print(f"  {int(row['rank']):>2}. {row['search_term']}")
    
    return trending_df


def example_2_get_retail_categories():
    """Example 2: Get only retail-relevant categories."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Retail-Relevant Categories")
    print("="*60)
    
    raw = fetch_categories()
    if raw:
        all_cats = build_dataframe(raw)
        retail_cats = filter_retail_relevant(all_cats)
        
        print(f"\n✅ Found {len(retail_cats)} retail categories")
        print("\nTop 10 retail categories:")
        for _, row in retail_cats.head(10).iterrows():
            cat_id = int(row['id'])  # type: ignore[arg-type]
            print(f"  [{cat_id:>5}] {row['full_path']}")
        
        return retail_cats
    
    return None


def example_3_build_complete_driver_list():
    """Example 3: Build a complete driver list."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Complete Driver List")
    print("="*60)
    
    # Fetch all data
    print("\n📊 Fetching all trend data...")
    trending_df = fetch_trending_searches(countries=["United States", "United Kingdom"])
    realtime_df = fetch_realtime_trending(geo="US")
    
    raw_cats = fetch_categories()
    categories_df = build_dataframe(raw_cats) if raw_cats else pd.DataFrame()
    
    # Build driver list
    driver_list = build_driver_list(trending_df, categories_df, realtime_df)
    
    # Print summary
    print("\n" + "="*60)
    print("DRIVER LIST SUMMARY")
    print("="*60)
    print(f"Generated at:        {driver_list['generated_at']}")
    print(f"Trending searches:   {driver_list['summary']['total_trending_searches']}")
    print(f"Real-time trends:    {driver_list['summary']['total_realtime_trends']}")
    print(f"Categories:          {driver_list['summary']['total_categories']}")
    print(f"Countries covered:   {', '.join(driver_list['summary']['countries_covered'])}")
    print("="*60)
    
    return driver_list


def example_4_save_driver_list(driver_list):
    """Example 4: Save driver list to JSON."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Saving Driver List")
    print("="*60)
    
    import json
    from datetime import datetime
    
    output_dir = Path(__file__).parent / "demo_output" / "examples"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"driver_list_example_{ts}.json"
    
    with open(output_file, "w") as f:
        json.dump(driver_list, f, indent=2)
    
    print(f"\n✅ Saved driver list to: {output_file}")
    print(f"   File size: {output_file.stat().st_size:,} bytes")


def example_5_analyze_trends(trending_df):
    """Example 5: Simple trend analysis."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Trend Analysis")
    print("="*60)
    
    if trending_df.empty:
        print("No data available")
        return
    
    # Count trends per country
    country_counts = trending_df.groupby('country').size()
    print("\nTrends per country:")
    for country, count in country_counts.items():
        print(f"  {country:<20} {count:>3} trends")
    
    # Find common words in trends
    all_terms = ' '.join(trending_df['search_term'].str.lower())
    words = all_terms.split()
    from collections import Counter
    common_words = Counter(words).most_common(10)
    
    print("\nMost common words in trending searches:")
    for word, count in common_words:
        if len(word) > 3:  # Filter short words
            print(f"  {word:<15} {count:>3} times")


def main():
    """Run all examples."""
    print("\n" + "="*60)
    print("GOOGLE TRENDS DRIVER LIST - USAGE EXAMPLES")
    print("="*60)
    print("\nThis script demonstrates programmatic usage of")
    print("trend_categories.py functions.\n")
    
    try:
        # Example 1: Get trending searches
        trending_df = example_1_get_trending_searches()
        
        # Example 2: Get retail categories
        retail_cats = example_2_get_retail_categories()
        
        # Example 3: Build complete driver list
        driver_list = example_3_build_complete_driver_list()
        
        # Example 4: Save driver list
        if driver_list:
            example_4_save_driver_list(driver_list)
        
        # Example 5: Analyze trends
        if trending_df is not None and not trending_df.empty:
            example_5_analyze_trends(trending_df)
        
        print("\n" + "="*60)
        print("✅ ALL EXAMPLES COMPLETED")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have installed the required packages:")
        print("  pip install pytrends pandas pyyaml")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
