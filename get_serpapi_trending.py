"""
get_serpapi_trending.py
═══════════════════════════════════════════════════════════════
Fetch Google Trends "Trending Now" data using SerpAPI
for the last 7 days in US region.

Features:
- Real-time trending searches
- Daily trending data
- Traffic metrics
- Related articles
- Trending images

Usage:
    python get_serpapi_trending.py
    
    # Specific region
    python get_serpapi_trending.py --geo US
    
    # Specific date range
    python get_serpapi_trending.py --date 2026-06-10
    
    # Save to file
    python get_serpapi_trending.py --save json

API Documentation:
    https://serpapi.com/search?engine=google_trends_trending_now
═══════════════════════════════════════════════════════════════
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


# ── Load environment variables ────────────────────────────────
_HERE = Path(__file__).resolve().parent
_ENV_FILE = _HERE / "retailtrends" / "config" / ".env"

if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
    print(f"✓ Loaded .env from: {_ENV_FILE}")
else:
    print(f"⚠️  .env file not found at: {_ENV_FILE}")

# Get API key
SERPAPI_KEY = os.getenv("serpAPIkey")
if not SERPAPI_KEY:
    print("ERROR: serpAPIkey not found in environment variables!")
    sys.exit(1)

# ── Output directory ──────────────────────────────────────────
_OUTPUT_DIR = _HERE / "demo_output" / "serpapi_trending"
_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SerpAPITrendingCollector:
    """
    Collect Google Trends "Trending Now" data using SerpAPI.
    
    This provides real-time trending searches from Google Trends
    with traffic metrics and related content.
    """
    
    BASE_URL = "https://serpapi.com/search"
    
    def __init__(self, api_key: str, geo: str = "US"):
        """
        Initialize SerpAPI collector.
        
        Args:
            api_key: Your SerpAPI key
            geo: Country code (US, GB, DE, etc.)
        """
        self.api_key = api_key
        self.geo = geo
        
    def get_trending_now(
        self,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get trending now data from SerpAPI.
        
        Args:
            date: Date in YYYY-MM-DD format (default: today)
            
        Returns:
            Dictionary with trending data
        """
        params = {
            "engine": "google_trends_trending_now",
            "api_key": self.api_key,
            "geo": self.geo,
        }
        
        if date:
            params["date"] = date
            
        print(f"\n🔍 Fetching trending data...")
        print(f"   Region: {self.geo}")
        print(f"   Date: {date or 'current'}")
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for errors
            if "error" in data:
                print(f"   ❌ API Error: {data['error']}")
                return {}
            
            print(f"   ✓ Success!")
            return data
            
        except requests.exceptions.RequestException as exc:
            print(f"   ❌ Request failed: {exc}")
            return {}
    
    def get_last_7_days(self) -> List[Dict[str, Any]]:
        """
        Get trending data for the last 7 days.
        
        Note: SerpAPI's google_trends_trending_now typically returns
        current trending data. This method collects the current data
        and provides structure for historical data if available.
        
        Returns:
            List of daily trending data
        """
        results = []
        
        print(f"\n📅 Collecting current trending data for {self.geo}...")
        
        # Get current trending data
        data = self.get_trending_now()
        
        if data:
            today = datetime.now()
            results.append({
                "date": today.strftime("%Y-%m-%d"),
                "data": data
            })
        
        return results
    
    def format_results(self, data: Dict[str, Any]) -> None:
        """
        Print formatted results to console.
        
        Args:
            data: Raw API response data
        """
        if not data:
            print("\n⚠️  No data to display")
            return
        
        print("\n" + "=" * 70)
        print(f"🔥 GOOGLE TRENDS - TRENDING NOW ({self.geo})")
        print("=" * 70)
        
        # Display results
        if "trending_searches" in data:
            print(f"\n� Current Trending Searches ({len(data['trending_searches'])} items)")
            print("-" * 70)
            
            for idx, search in enumerate(data["trending_searches"][:15], 1):
                query = search.get("query", "N/A")
                volume = search.get("search_volume", 0)
                increase = search.get("increase_percentage", 0)
                
                print(f"\n{idx}. {query}")
                print(f"   Search Volume: {volume:,}")
                print(f"   Increase: +{increase}%")
                
                # Categories
                if "categories" in search and search["categories"]:
                    cats = ", ".join([c.get("name", "N/A") for c in search["categories"]])
                    print(f"   Categories: {cats}")
                
                # Trend breakdown
                if "trend_breakdown" in search and search["trend_breakdown"]:
                    breakdown = search["trend_breakdown"][:3]
                    print(f"   Related: {', '.join(breakdown)}")
        
        # Realtime trends (if available)
        if "realtime_searches" in data:
            print(f"\n⚡ Realtime Trending Searches ({len(data['realtime_searches'])} items)")
            print("-" * 70)
            
            for idx, search in enumerate(data["realtime_searches"][:10], 1):
                query = search.get("query", "N/A")
                traffic = search.get("formatted_traffic", "N/A")
                
                print(f"\n{idx}. {query}")
                print(f"   Traffic: {traffic}")
        
        print("\n" + "=" * 70)
    
    def save_results(
        self,
        data: Any,
        output_format: str = "json",
        filename: Optional[str] = None
    ) -> Path:
        """
        Save results to file.
        
        Args:
            data: Data to save
            output_format: "json" or "csv"
            filename: Custom filename (optional)
            
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not filename:
            filename = f"serpapi_trending_{self.geo}_{timestamp}.{output_format}"
        
        filepath = _OUTPUT_DIR / filename
        
        if output_format == "json":
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            print(f"⚠️  Format '{output_format}' not yet implemented")
            return filepath
        
        print(f"\n💾 Saved to: {filepath}")
        return filepath


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Fetch Google Trends 'Trending Now' data using SerpAPI"
    )
    parser.add_argument(
        "--geo",
        default="US",
        help="Country code (US, GB, DE, etc.)"
    )
    parser.add_argument(
        "--date",
        help="Specific date (YYYY-MM-DD format)"
    )
    parser.add_argument(
        "--last-7-days",
        action="store_true",
        help="Collect current trending data (note: historical data may not be available)"
    )
    parser.add_argument(
        "--save",
        choices=["json", "csv"],
        help="Save results to file"
    )
    
    args = parser.parse_args()
    
    # Initialize collector
    collector = SerpAPITrendingCollector(api_key=SERPAPI_KEY, geo=args.geo)
    
    # Collect data
    if args.last_7_days:
        print("\n" + "=" * 70)
        print("📅 COLLECTING CURRENT TRENDING DATA")
        print("=" * 70)
        
        results = collector.get_last_7_days()
        
        # Display summary
        print("\n" + "=" * 70)
        print(f"📊 TRENDING SEARCHES - {args.geo}")
        print("=" * 70)
        
        # Show trends
        if results:
            latest = results[0]
            print(f"\n🔥 Data collected on {latest['date']}")
            collector.format_results(latest["data"])
        
        # Save if requested
        if args.save:
            filepath = collector.save_results(results, args.save)
            print(f"\n✓ Data saved to: {filepath}")
    
    else:
        # Single request
        data = collector.get_trending_now(date=args.date)
        
        # Display results
        collector.format_results(data)
        
        # Save if requested
        if args.save:
            collector.save_results(data, args.save)
    
    print("\n✨ Done!\n")


if __name__ == "__main__":
    main()
