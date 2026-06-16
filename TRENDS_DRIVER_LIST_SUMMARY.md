# Trends Driver List Generator - Summary

## What Was Created

A comprehensive **standalone Python program** (`trend_categories.py`) that fetches ALL available trends data from Google Trends and returns it as a **driver list**.

## Key Features

### 🔥 Trending Searches
- Fetches daily trending searches from **15+ countries**
- Countries: US, UK, Germany, France, Canada, Australia, Japan, Brazil, India, South Korea, Italy, Spain, Mexico, Netherlands, Sweden
- Returns ranked list with search terms and metadata

### ⚡ Real-Time Trends
- Fetches real-time trending searches (last few hours)
- Supports any geography code (US, GB, DE, etc.)
- Captures breaking news and viral topics

### 📁 Category Hierarchy
- Complete Google Trends category tree with IDs
- All categories and subcategories
- Filterable by keyword or retail-relevance
- Configurable depth levels

### 📊 Driver List Output
Returns a comprehensive dictionary containing:
```python
{
    "generated_at": "timestamp",
    "trending_searches": [...],  # Daily trends by country
    "realtime_trends": [...],     # Real-time hot topics
    "categories": [...],          # Category tree with IDs
    "summary": {
        "total_trending_searches": N,
        "total_realtime_trends": N,
        "total_categories": N,
        "countries_covered": [...]
    }
}
```

## Quick Usage

```bash
# Default: Get trending searches from all countries
python trend_categories.py

# Get everything (trends + categories + real-time)
python trend_categories.py --all --realtime --save both

# Trending searches only from specific countries
python trend_categories.py --trends-only --countries "United States" Germany Japan

# Categories with retail filter
python trend_categories.py --categories-only --retail --save csv

# Real-time monitoring
python trend_categories.py --trends-only --realtime --geo US
```

## Output Formats

### JSON (Complete Driver List)
- `driver_list_YYYYMMDD_HHMMSS.json` - All data in structured format

### CSV (Separate Tables)
- `trending_searches_YYYYMMDD_HHMMSS.csv` - Trends by country
- `categories_YYYYMMDD_HHMMSS.csv` - Category hierarchy
- `realtime_trends_YYYYMMDD_HHMMSS.csv` - Real-time data

## Command Line Options

| Option | Description |
|--------|-------------|
| `--trends-only` | Fetch only trending searches |
| `--categories-only` | Fetch only categories |
| `--all` | Fetch everything |
| `--countries C1 C2...` | Specify countries |
| `--realtime` | Include real-time trends |
| `--geo GEO` | Geography for real-time (default: US) |
| `--filter KEYWORD` | Filter categories by keyword |
| `--retail` | Only retail-relevant categories |
| `--depth N` | Max category depth |
| `--save {csv,json,both}` | Save to files |
| `--tree` | Print tree view |
| `--no-print` | Skip console output |

## Files Created

1. **`trend_categories.py`** (690+ lines)
   - Main script with all functionality
   - Fetches trends from multiple sources
   - Builds comprehensive driver list
   - CLI with extensive options

2. **`README.md`** (collectors documentation)
   - Complete usage guide
   - All command examples
   - Programmatic usage
   - Troubleshooting tips

## What Makes This a "Driver List"

The script returns a **comprehensive driver list** that includes:

1. ✅ **All trending search terms** across multiple countries
2. ✅ **Real-time trending topics** (breaking news)
3. ✅ **Complete category IDs** for filtering Google Trends queries
4. ✅ **Metadata and timestamps** for tracking
5. ✅ **Summary statistics** for quick overview
6. ✅ **Structured format** ready for downstream processing

This driver list can be used to:
- Monitor what's trending globally
- Discover new keywords for analysis
- Filter trends by category
- Track breaking news in real-time
- Feed into automated pipelines
- Generate trend reports

## Repository Status

✅ **Committed and pushed to GitHub**
- Repository: `varma324/retailtrends`
- Commit: "feat: add comprehensive trends driver list generator"
- Files: 2 new files (trend_categories.py, README.md)
- Lines: 940+ lines of code and documentation

## Next Steps (Optional)

1. **Install dependencies**: `pip install pytrends pandas pyyaml`
2. **Run the script**: `python retailtrends/src/collectors/trend_categories.py --all`
3. **Save results**: Add `--save json` to save the driver list
4. **Integrate**: Import functions into your pipeline code
5. **Automate**: Schedule regular runs to track trends over time

---

**View on GitHub**: https://github.com/varma324/retailtrends
