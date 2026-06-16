"""
trend_categories.py
═══════════════════════════════════════════════════════════════
Standalone program to fetch ALL trending searches and category
information from Google Trends using pytrends.

Returns a comprehensive driver list of:
  1. Real-time trending searches (today's hot topics)
  2. Daily trending searches by country
  3. Category hierarchy with IDs
  4. Top charts data

Run:
    python retailtrends/src/collectors/trend_categories.py

    # Get trending searches only
    python retailtrends/src/collectors/trend_categories.py --trends-only

    # Get trends for specific countries
    python retailtrends/src/collectors/trend_categories.py --countries US GB DE

    # Filter categories by keyword
    python retailtrends/src/collectors/trend_categories.py --filter fashion

    # Save to CSV / JSON
    python retailtrends/src/collectors/trend_categories.py --save csv
    python retailtrends/src/collectors/trend_categories.py --save json

    # Retail-relevant categories only
    python retailtrends/src/collectors/trend_categories.py --retail

    # Get everything (trends + categories)
    python retailtrends/src/collectors/trend_categories.py --all --save both
═══════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from pytrends.request import TrendReq

# ── Output directory (project-relative) ──────────────────────
_HERE       = Path(__file__).resolve().parent
_PROJECT    = _HERE.parent.parent          # retailtrends/
_OUTPUT_DIR = _PROJECT / "demo_output" / "categories"

# ── Retail-relevant top-level category names ──────────────────
RETAIL_KEYWORDS = {
    "shopping",
    "retail",
    "fashion",
    "apparel",
    "beauty",
    "food",
    "grocery",
    "home",
    "garden",
    "electronics",
    "computer",
    "consumer",
    "sport",
    "toy",
    "game",
    "travel",
    "automotive",
    "finance",
    "health",
    "fitness",
    "lifestyle",
    "luxury",
    "discount",
    "deal",
}


# ══════════════════════════════════════════════════════════════
# Trending searches fetcher
# ══════════════════════════════════════════════════════════════

# Country codes for trending searches (pytrends format)
TRENDING_COUNTRIES = {
    "United States": "united_states",
    "United Kingdom": "united_kingdom",
    "Germany": "germany",
    "France": "france",
    "Canada": "canada",
    "Australia": "australia",
    "Japan": "japan",
    "Brazil": "brazil",
    "India": "india",
    "South Korea": "south_korea",
    "Italy": "italy",
    "Spain": "spain",
    "Mexico": "mexico",
    "Netherlands": "netherlands",
    "Sweden": "sweden",
}


def fetch_trending_searches(
    countries: Optional[list] = None,
    retries: int = 3,
    sleep_seconds: float = 2.0,
) -> pd.DataFrame:
    """
    Fetch daily trending searches for multiple countries.

    Args:
        countries: List of country names (e.g., ["United States", "Germany"])
                   If None, fetches from all available countries.
        retries: Number of retry attempts per country
        sleep_seconds: Sleep time between requests

    Returns:
        DataFrame with columns: rank, search_term, country, collected_at
    """
    pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25),
                        retries=retries, backoff_factor=1)
    
    if countries is None:
        countries = list(TRENDING_COUNTRIES.keys())
    
    all_trends = []
    collected_at = datetime.now().isoformat()
    
    for country_name in countries:
        country_code = TRENDING_COUNTRIES.get(country_name)
        if not country_code:
            print(f"  ⚠️  Unknown country: {country_name}")
            continue
        
        for attempt in range(1, retries + 1):
            try:
                print(f"  🔥  Fetching trending searches for {country_name} (attempt {attempt})...")
                df = pytrends.trending_searches(pn=country_code)
                
                if df is not None and not df.empty:
                    df = df.reset_index(drop=True)
                    df.columns = ["search_term"]
                    df["rank"] = df.index + 1
                    df["country"] = country_name
                    df["country_code"] = country_code
                    df["collected_at"] = collected_at
                    all_trends.append(df)
                    print(f"      ✓ Got {len(df)} trending searches")
                    break
                else:
                    print(f"      ⚠️  No data for {country_name}")
                    break
                    
            except Exception as exc:
                print(f"      ⚠️  Attempt {attempt} failed: {exc}")
                if attempt < retries:
                    time.sleep(sleep_seconds * attempt)
        
        time.sleep(sleep_seconds)  # Rate limiting between countries
    
    if all_trends:
        result = pd.concat(all_trends, ignore_index=True)
        result = pd.DataFrame(result[["rank", "search_term", "country", "country_code", "collected_at"]])
        return result
    
    return pd.DataFrame()


def fetch_realtime_trending(
    geo: str = "US",
    retries: int = 3,
) -> pd.DataFrame:
    """
    Fetch real-time trending searches (last few hours).

    Args:
        geo: Country code (e.g., "US", "GB", "DE")
        retries: Number of retry attempts

    Returns:
        DataFrame with trending topics and metadata
    """
    pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25),
                        retries=retries, backoff_factor=1)
    
    for attempt in range(1, retries + 1):
        try:
            print(f"  ⚡  Fetching real-time trends for {geo} (attempt {attempt})...")
            trends = pytrends.realtime_trending_searches(pn=geo)
            
            if trends is not None and not trends.empty:
                print(f"      ✓ Got {len(trends)} real-time trends")
                trends["geo"] = geo
                trends["collected_at"] = datetime.now().isoformat()
                return trends
            else:
                print(f"      ⚠️  No real-time data for {geo}")
                return pd.DataFrame()
                
        except Exception as exc:
            print(f"      ⚠️  Attempt {attempt} failed: {exc}")
            if attempt < retries:
                time.sleep(2 * attempt)
    
    return pd.DataFrame()


def build_driver_list(
    trending_df: pd.DataFrame,
    categories_df: pd.DataFrame,
    realtime_df: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Build a comprehensive driver list combining all trend sources.

    Returns:
        {
            "trending_searches": [...],
            "realtime_trends": [...],
            "categories": [...],
            "summary": {...},
        }
    """
    driver_list = {
        "generated_at": datetime.now().isoformat(),
        "trending_searches": [],
        "realtime_trends": [],
        "categories": [],
        "summary": {
            "total_trending_searches": 0,
            "total_realtime_trends": 0,
            "total_categories": 0,
            "countries_covered": [],
        }
    }
    
    # Trending searches
    if not trending_df.empty:
        driver_list["trending_searches"] = trending_df.to_dict(orient="records")
        driver_list["summary"]["total_trending_searches"] = len(trending_df)
        driver_list["summary"]["countries_covered"] = trending_df["country"].unique().tolist()
    
    # Real-time trends
    if realtime_df is not None and not realtime_df.empty:
        driver_list["realtime_trends"] = realtime_df.to_dict(orient="records")
        driver_list["summary"]["total_realtime_trends"] = len(realtime_df)
    
    # Categories
    if not categories_df.empty:
        driver_list["categories"] = categories_df.to_dict(orient="records")
        driver_list["summary"]["total_categories"] = len(categories_df)
    
    return driver_list


# ══════════════════════════════════════════════════════════════
# Core fetcher
# ══════════════════════════════════════════════════════════════

def fetch_categories(
    retries: int = 3,
    sleep_seconds: float = 2.0,
) -> dict:
    """
    Fetch the full Google Trends category tree via pytrends.

    Returns the raw dict returned by pytrends.categories() which
    has the shape:
        {
            "children": [
                {
                    "id":       <int>,
                    "name":     <str>,
                    "children": [ ... ]   # nested subcategories
                },
                ...
            ]
        }
    """
    pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25),
                        retries=retries, backoff_factor=1)
    for attempt in range(1, retries + 1):
        try:
            print(f"  ⏳  Fetching category tree from Google Trends (attempt {attempt})…")
            cats = pytrends.categories()
            print("  ✅  Category tree received.\n")
            return cats
        except Exception as exc:
            print(f"  ⚠️   Attempt {attempt} failed: {exc}")
            if attempt < retries:
                time.sleep(sleep_seconds * attempt)
    print("  ❌  All attempts failed. Returning empty tree.")
    return {}


# ══════════════════════════════════════════════════════════════
# Tree flattening helpers
# ══════════════════════════════════════════════════════════════

def _flatten(
    node: dict,
    parent_name: str = "",
    parent_id: Optional[int] = None,
    depth: int = 0,
    max_depth: Optional[int] = None,
    rows: Optional[list] = None,
) -> list:
    """
    Recursively walk the category tree and produce a flat list of dicts.

    Each row:
        id, name, full_path, depth, parent_id, parent_name
    """
    if rows is None:
        rows = []

    children = node.get("children", [])
    for child in children:
        cid   = child.get("id")
        cname = child.get("name", "")
        path  = f"{parent_name} > {cname}".lstrip(" > ") if parent_name else cname

        rows.append(
            {
                "id":          cid,
                "name":        cname,
                "full_path":   path,
                "depth":       depth,
                "parent_id":   parent_id,
                "parent_name": parent_name or "(root)",
            }
        )

        if max_depth is None or depth < max_depth:
            _flatten(
                child,
                parent_name=path,
                parent_id=cid,
                depth=depth + 1,
                max_depth=max_depth,
                rows=rows,
            )

    return rows


def build_dataframe(
    raw: dict,
    max_depth: Optional[int] = None,
) -> pd.DataFrame:
    """Convert raw category tree to a tidy DataFrame."""
    rows = _flatten(raw, max_depth=max_depth)
    df   = pd.DataFrame(rows, columns=["id", "name", "full_path",
                                        "depth", "parent_id", "parent_name"])
    return df.sort_values(["depth", "name"]).reset_index(drop=True)


# ══════════════════════════════════════════════════════════════
# Filtering helpers
# ══════════════════════════════════════════════════════════════

def filter_by_keyword(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    """Return rows whose full_path contains *keyword* (case-insensitive)."""
    mask = df["full_path"].str.contains(keyword, case=False, na=False)
    return pd.DataFrame(df.loc[mask]).reset_index(drop=True)


def filter_retail_relevant(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows that match any retail-relevant keyword."""
    pattern = "|".join(RETAIL_KEYWORDS)
    mask    = df["full_path"].str.contains(pattern, case=False, na=False)
    return pd.DataFrame(df.loc[mask]).reset_index(drop=True)


# ══════════════════════════════════════════════════════════════
# Display helpers
# ══════════════════════════════════════════════════════════════

def print_tree(df: pd.DataFrame, max_rows: int = 200) -> None:
    """Print categories as an indented tree."""
    top = df[df["depth"] == df["depth"].min()].copy()
    _all = df.set_index("id")

    printed: set = set()

    def _print_node(row_id: int, indent: int = 0) -> None:
        if row_id in printed:
            return
        printed.add(row_id)
        try:
            row = _all.loc[row_id]
        except KeyError:
            return
        prefix = "  " * indent + ("├─ " if indent else "")
        print(f"{prefix}[{row_id:>5}]  {row['name']}")
        children = df[df["parent_id"] == row_id]
        for _, child in children.iterrows():
            _print_node(child["id"], indent + 1)

    count = 0
    for _, root_row in top.iterrows():
        if count >= max_rows:
            print(f"\n  … (truncated – use --filter or --depth to narrow results)")
            break
        _print_node(root_row["id"])
        count += 1
        print()   # blank line between top-level groups


def print_table(df: pd.DataFrame) -> None:
    """Print a compact tabular view."""
    col_w = {"id": 7, "depth": 5, "name": 30, "full_path": 70}
    header = (
        f"{'ID':>{col_w['id']}}  "
        f"{'DEPTH':>{col_w['depth']}}  "
        f"{'NAME':<{col_w['name']}}  "
        f"{'FULL PATH':<{col_w['full_path']}}"
    )
    sep = "-" * len(header)
    print(sep)
    print(header)
    print(sep)
    for _, row in df.iterrows():
        name_trunc = str(row["name"])[:col_w["name"]]
        path_trunc = str(row["full_path"])[:col_w["full_path"]]
        print(
            f"{int(row['id']):>{col_w['id']}}  "   # type: ignore[arg-type]
            f"{int(row['depth']):>{col_w['depth']}}  "  # type: ignore[arg-type]
            f"{name_trunc:<{col_w['name']}}  "
            f"{path_trunc:<{col_w['full_path']}}"
        )
    print(sep)
    print(f"  Total: {len(df)} categories\n")


# ══════════════════════════════════════════════════════════════
# Save helpers
# ══════════════════════════════════════════════════════════════

def save_csv(df: pd.DataFrame, label: str = "") -> Path:
    """Save DataFrame to CSV under demo_output/categories/."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = f"_{label}" if label else ""
    out  = _OUTPUT_DIR / f"trend_categories{slug}_{ts}.csv"
    df.to_csv(out, index=False)
    print(f"  💾  Saved CSV  → {out}")
    return out


def save_json(raw: dict, df: pd.DataFrame, label: str = "") -> Path:
    """Save both the raw tree and the flat table to JSON."""
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = f"_{label}" if label else ""
    out  = _OUTPUT_DIR / f"trend_categories{slug}_{ts}.json"
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_categories": len(df),
        "flat_table": df.to_dict(orient="records"),
        "raw_tree":   raw,
    }
    with open(out, "w") as fh:
        json.dump(payload, fh, indent=2)
    print(f"  💾  Saved JSON → {out}")
    return out


# ══════════════════════════════════════════════════════════════
# Summary stats
# ══════════════════════════════════════════════════════════════

def print_summary(df: pd.DataFrame) -> None:
    """Print a depth / count breakdown."""
    print("=" * 55)
    print("  GOOGLE TRENDS CATEGORY SUMMARY")
    print("=" * 55)
    depth_counts = df.groupby("depth").size().reset_index(name="count")
    depth_counts.columns = ["Depth", "# Categories"]
    for _, row in depth_counts.iterrows():
        d     = int(row["Depth"])       # type: ignore[arg-type]
        cnt   = int(row["# Categories"])  # type: ignore[arg-type]
        label = "Top-level" if d == 0 else f"Level-{d}"
        print(f"  {label:<12}  {cnt:>5} categories")
    print("-" * 55)
    print(f"  {'TOTAL':<12}  {len(df):>5} categories")
    print("=" * 55)
    print()


# ══════════════════════════════════════════════════════════════
# CLI entry point
# ══════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch trending searches and category IDs from Google Trends.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get trending searches + categories
  python trend_categories.py --all
  
  # Trending searches only
  python trend_categories.py --trends-only
  
  # Specific countries
  python trend_categories.py --trends-only --countries "United States" Germany
  
  # Categories with filters
  python trend_categories.py --categories-only --filter fashion
  python trend_categories.py --categories-only --retail
  
  # Save everything
  python trend_categories.py --all --save both
        """,
    )
    p.add_argument("--trends-only", action="store_true",
                   help="Fetch only trending searches (no categories).")
    p.add_argument("--categories-only", action="store_true",
                   help="Fetch only categories (no trending searches).")
    p.add_argument("--all", "-a", action="store_true",
                   help="Fetch both trending searches and categories.")
    p.add_argument("--countries", nargs="+", metavar="COUNTRY",
                   help="Countries for trending searches (e.g., 'United States' Germany).")
    p.add_argument("--realtime", action="store_true",
                   help="Include real-time trending searches (US only by default).")
    p.add_argument("--geo", default="US",
                   help="Geography code for real-time trends (default: US).")
    p.add_argument("--filter",  "-f",  metavar="KEYWORD",
                   help="Filter categories by keyword in path.")
    p.add_argument("--retail",  "-r",  action="store_true",
                   help="Show only retail-relevant categories.")
    p.add_argument("--depth",   "-d",  type=int, default=None,
                   metavar="N",
                   help="Max category depth (0 = top-level only).")
    p.add_argument("--save",    "-s",  choices=["csv", "json", "both"],
                   help="Save output to file(s).")
    p.add_argument("--tree",    "-t",  action="store_true",
                   help="Print categories as indented tree (default is table).")
    p.add_argument("--no-print", action="store_true",
                   help="Skip printing to stdout (useful with --save).")
    return p.parse_args()


def main() -> dict:
    args = parse_args()

    print("\n" + "=" * 65)
    print("  GOOGLE TRENDS DRIVER LIST GENERATOR")
    print("=" * 65 + "\n")

    # Determine what to fetch
    fetch_trends = args.trends_only or args.all or (not args.categories_only)
    fetch_categories = args.categories_only or args.all
    
    trending_df = pd.DataFrame()
    realtime_df = pd.DataFrame()
    categories_df = pd.DataFrame()
    raw_categories = {}

    # ── 1. Fetch Trending Searches ────────────────────────────
    if fetch_trends:
        print("🔥 FETCHING TRENDING SEARCHES")
        print("-" * 65)
        
        countries = args.countries if args.countries else None
        trending_df = fetch_trending_searches(countries=countries)
        
        if not trending_df.empty:
            print(f"\n  ✅  Collected {len(trending_df)} trending searches from {len(trending_df['country'].unique())} countries\n")
        else:
            print("\n  ⚠️   No trending searches collected\n")
        
        # Real-time trends
        if args.realtime:
            print("\n⚡ FETCHING REAL-TIME TRENDS")
            print("-" * 65)
            realtime_df = fetch_realtime_trending(geo=args.geo)
            if not realtime_df.empty:
                print(f"\n  ✅  Collected {len(realtime_df)} real-time trends\n")
            else:
                print("\n  ⚠️   No real-time trends available\n")

    # ── 2. Fetch Categories ────────────────────────────────────
    if fetch_categories:
        print("\n📁 FETCHING CATEGORY HIERARCHY")
        print("-" * 65)
        
        raw_categories = fetch_categories()
        if not raw_categories:
            print("  ⚠️   No category data received\n")
        else:
            categories_df = build_dataframe(raw_categories, max_depth=args.depth)
            
            # Apply filters
            label = ""
            if args.retail:
                categories_df = filter_retail_relevant(categories_df)
                label = "retail"
                print(f"  🛒  Retail filter applied → {len(categories_df)} categories")

            if args.filter:
                categories_df = filter_by_keyword(categories_df, args.filter)
                label = args.filter.lower().replace(" ", "_")
                print(f"  🔍  Keyword filter '{args.filter}' → {len(categories_df)} categories")

            if not categories_df.empty:
                print(f"\n  ✅  Collected {len(categories_df)} categories\n")

    # ── 3. Build Driver List ───────────────────────────────────
    driver_list = build_driver_list(trending_df, categories_df, realtime_df)

    # ── 4. Print Results ───────────────────────────────────────
    if not args.no_print:
        print("\n" + "=" * 65)
        print("  DRIVER LIST SUMMARY")
        print("=" * 65)
        print(f"  Trending Searches:  {driver_list['summary']['total_trending_searches']:>6}")
        print(f"  Real-time Trends:   {driver_list['summary']['total_realtime_trends']:>6}")
        print(f"  Categories:         {driver_list['summary']['total_categories']:>6}")
        if driver_list['summary']['countries_covered']:
            print(f"  Countries:          {', '.join(driver_list['summary']['countries_covered'][:5])}")
        print("=" * 65 + "\n")
        
        # Print trending searches
        if not trending_df.empty:
            print("🔥 TOP TRENDING SEARCHES")
            print("-" * 65)
            for country in trending_df['country'].unique()[:3]:  # Show first 3 countries
                country_trends = trending_df[trending_df['country'] == country].head(10)
                print(f"\n  {country}:")
                for _, row in country_trends.iterrows():
                    print(f"    {int(row['rank']):>2}. {row['search_term']}")  # type: ignore[arg-type]
            print()
        
        # Print real-time trends
        if not realtime_df.empty:
            print("\n⚡ REAL-TIME TRENDS")
            print("-" * 65)
            for idx, row in realtime_df.head(10).iterrows():
                if 'title' in realtime_df.columns:
                    print(f"  • {row['title']}")
            print()
        
        # Print categories
        if not categories_df.empty:
            print("\n📁 CATEGORY HIERARCHY")
            print("-" * 65)
            print_summary(categories_df)
            if args.tree:
                print_tree(categories_df, max_rows=50)
            else:
                print_table(categories_df.head(50))  # Show first 50

    # ── 5. Save Results ────────────────────────────────────────
    if args.save:
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if args.save in ("json", "both"):
            out = _OUTPUT_DIR / f"driver_list_{ts}.json"
            with open(out, "w") as fh:
                json.dump(driver_list, fh, indent=2)
            print(f"  💾  Saved driver list JSON → {out}")
        
        if args.save in ("csv", "both"):
            if not trending_df.empty:
                out_trends = _OUTPUT_DIR / f"trending_searches_{ts}.csv"
                trending_df.to_csv(out_trends, index=False)
                print(f"  💾  Saved trending searches CSV → {out_trends}")
            
            if not categories_df.empty:
                out_cats = _OUTPUT_DIR / f"categories_{ts}.csv"
                categories_df.to_csv(out_cats, index=False)
                print(f"  💾  Saved categories CSV → {out_cats}")
            
            if not realtime_df.empty:
                out_rt = _OUTPUT_DIR / f"realtime_trends_{ts}.csv"
                realtime_df.to_csv(out_rt, index=False)
                print(f"  💾  Saved real-time trends CSV → {out_rt}")

    print("\n✅  Done.\n")
    
    # Return driver list for programmatic use
    return driver_list


if __name__ == "__main__":
    main()
