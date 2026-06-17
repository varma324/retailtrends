"""
analyze_serpapi_trends.py
═══════════════════════════════════════════════════════════════
Analyze SerpAPI trending data to extract insights.

Usage:
    python analyze_serpapi_trends.py
    
    # Analyze specific file
    python analyze_serpapi_trends.py --file demo_output/serpapi_trending/serpapi_trending_US_20260617_141638.json
═══════════════════════════════════════════════════════════════
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Any


def load_trending_data(filepath: Path) -> List[Dict[str, Any]]:
    """Load trending data from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_categories(data: List[Dict[str, Any]]) -> None:
    """Analyze trending searches by category."""
    print("\n" + "=" * 70)
    print("📊 CATEGORY ANALYSIS")
    print("=" * 70)
    
    category_counts = Counter()
    category_searches = defaultdict(list)
    
    for day_data in data:
        trending = day_data['data'].get('trending_searches', [])
        
        for search in trending:
            categories = search.get('categories', [])
            for cat in categories:
                cat_name = cat.get('name', 'Unknown')
                category_counts[cat_name] += 1
                category_searches[cat_name].append(search.get('query', ''))
    
    print(f"\nTotal categories: {len(category_counts)}")
    print(f"\nTop 10 Categories by Number of Trends:\n")
    
    for idx, (category, count) in enumerate(category_counts.most_common(10), 1):
        print(f"{idx}. {category}: {count} trending searches")
        # Show sample searches
        samples = category_searches[category][:3]
        for sample in samples:
            print(f"   • {sample}")
        print()


def analyze_search_volumes(data: List[Dict[str, Any]]) -> None:
    """Analyze search volumes and growth rates."""
    print("\n" + "=" * 70)
    print("🔥 TOP TRENDING SEARCHES")
    print("=" * 70)
    
    all_searches = []
    
    for day_data in data:
        trending = day_data['data'].get('trending_searches', [])
        all_searches.extend(trending)
    
    # Sort by search volume
    all_searches.sort(key=lambda x: x.get('search_volume', 0), reverse=True)
    
    print(f"\nTop 20 Searches by Volume:\n")
    
    for idx, search in enumerate(all_searches[:20], 1):
        query = search.get('query', 'N/A')
        volume = search.get('search_volume', 0)
        increase = search.get('increase_percentage', 0)
        
        print(f"{idx}. {query}")
        print(f"   Volume: {volume:,} | Growth: +{increase}%")


def analyze_related_queries(data: List[Dict[str, Any]]) -> None:
    """Analyze most common related queries."""
    print("\n" + "=" * 70)
    print("🔗 RELATED QUERY PATTERNS")
    print("=" * 70)
    
    all_queries = []
    
    for day_data in data:
        trending = day_data['data'].get('trending_searches', [])
        
        for search in trending:
            breakdown = search.get('trend_breakdown', [])
            all_queries.extend(breakdown)
    
    query_counts = Counter(all_queries)
    
    print(f"\nTotal related queries: {len(all_queries)}")
    print(f"Unique queries: {len(query_counts)}")
    print(f"\nMost Common Related Queries:\n")
    
    for idx, (query, count) in enumerate(query_counts.most_common(15), 1):
        print(f"{idx}. {query} ({count} occurrences)")


def find_retail_trends(data: List[Dict[str, Any]]) -> None:
    """Find retail and shopping related trends."""
    print("\n" + "=" * 70)
    print("🛍️ RETAIL & SHOPPING TRENDS")
    print("=" * 70)
    
    retail_keywords = [
        'buy', 'shop', 'sale', 'price', 'store', 'amazon', 'walmart',
        'deal', 'discount', 'product', 'shopping', 'purchase', 'order',
        'nike', 'adidas', 'apple', 'samsung', 'iphone', 'playstation'
    ]
    
    retail_trends = []
    
    for day_data in data:
        trending = day_data['data'].get('trending_searches', [])
        
        for search in trending:
            query = search.get('query', '').lower()
            breakdown = ' '.join(search.get('trend_breakdown', [])).lower()
            
            # Check if any retail keyword appears
            if any(keyword in query or keyword in breakdown for keyword in retail_keywords):
                retail_trends.append(search)
    
    if retail_trends:
        print(f"\nFound {len(retail_trends)} retail-related trends:\n")
        
        for idx, search in enumerate(retail_trends[:10], 1):
            query = search.get('query', 'N/A')
            volume = search.get('search_volume', 0)
            categories = ', '.join([c.get('name', '') for c in search.get('categories', [])])
            
            print(f"{idx}. {query}")
            print(f"   Volume: {volume:,} | Categories: {categories}")
    else:
        print("\nNo retail-related trends found in this dataset.")


def generate_summary(data: List[Dict[str, Any]]) -> None:
    """Generate overall summary statistics."""
    print("\n" + "=" * 70)
    print("📈 SUMMARY STATISTICS")
    print("=" * 70)
    
    total_searches = 0
    total_volume = 0
    avg_increase = []
    
    for day_data in data:
        trending = day_data['data'].get('trending_searches', [])
        total_searches += len(trending)
        
        for search in trending:
            total_volume += search.get('search_volume', 0)
            avg_increase.append(search.get('increase_percentage', 0))
    
    avg_increase_pct = sum(avg_increase) / len(avg_increase) if avg_increase else 0
    
    print(f"\nTotal trending searches: {total_searches}")
    print(f"Total search volume: {total_volume:,}")
    print(f"Average increase: +{avg_increase_pct:.0f}%")
    print(f"Date range: {data[0]['date']}" if data else "N/A")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Analyze SerpAPI trending data"
    )
    parser.add_argument(
        "--file",
        help="Path to JSON file to analyze"
    )
    
    args = parser.parse_args()
    
    # Find the most recent file if not specified
    if args.file:
        filepath = Path(args.file)
    else:
        output_dir = Path(__file__).parent / "demo_output" / "serpapi_trending"
        json_files = list(output_dir.glob("*.json"))
        
        if not json_files:
            print("❌ No trending data files found!")
            print(f"   Run: python get_serpapi_trending.py --last-7-days --save json")
            return
        
        # Get most recent file
        filepath = max(json_files, key=lambda p: p.stat().st_mtime)
    
    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return
    
    print(f"\n📂 Analyzing: {filepath.name}")
    
    # Load data
    data = load_trending_data(filepath)
    
    # Run analyses
    generate_summary(data)
    analyze_search_volumes(data)
    analyze_categories(data)
    analyze_related_queries(data)
    find_retail_trends(data)
    
    print("\n✨ Analysis complete!\n")


if __name__ == "__main__":
    main()
