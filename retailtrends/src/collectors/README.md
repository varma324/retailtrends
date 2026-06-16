# Google Trends Collectors

## trend_categories.py - Comprehensive Trends Driver List Generator

This standalone program fetches ALL trending searches and category information from Google Trends using pytrends. It returns a comprehensive **driver list** containing:

1. **Real-time trending searches** (today's hot topics)
2. **Daily trending searches** by country
3. **Category hierarchy** with IDs
4. **Comprehensive metadata**

### Quick Start

```bash
# Install dependencies
pip install pytrends pandas pyyaml

# Get trending searches from all countries (default)
python trend_categories.py

# Get trending searches + categories + real-time
python trend_categories.py --all --realtime

# Trending searches only
python trend_categories.py --trends-only

# Specific countries
python trend_categories.py --trends-only --countries "United States" Germany Japan

# Categories only with retail filter
python trend_categories.py --categories-only --retail

# Save everything to JSON and CSV
python trend_categories.py --all --save both
```

### Command Line Options

#### Data Fetching Modes

- `--trends-only` - Fetch only trending searches (no categories)
- `--categories-only` - Fetch only categories (no trending searches)
- `--all` - Fetch both trending searches and categories (recommended)

#### Trending Searches Options

- `--countries COUNTRY [COUNTRY ...]` - Specify countries for trending searches
  - Example: `--countries "United States" Germany "United Kingdom"`
  - Available: United States, United Kingdom, Germany, France, Canada, Australia, Japan, Brazil, India, South Korea, Italy, Spain, Mexico, Netherlands, Sweden

- `--realtime` - Include real-time trending searches (last few hours)
- `--geo GEO` - Geography code for real-time trends (default: US)
  - Examples: `--geo US`, `--geo GB`, `--geo DE`

#### Category Filtering Options

- `--filter KEYWORD` - Filter categories whose path contains KEYWORD
  - Example: `--filter fashion`
  
- `--retail` - Show only retail-relevant categories
  - Includes: shopping, retail, fashion, apparel, beauty, food, grocery, home, electronics, etc.

- `--depth N` - Maximum category depth (0 = top-level only)
  - Example: `--depth 2`

#### Output Options

- `--save {csv,json,both}` - Save output to files
  - `csv` - Separate CSV files for trends and categories
  - `json` - Complete driver list in JSON format
  - `both` - All formats

- `--tree` - Print categories as indented tree (default is table)
- `--no-print` - Skip console output (useful with `--save`)

### Output Format

The script returns a **driver list** dictionary with the following structure:

```json
{
  "generated_at": "2026-06-16T10:30:00",
  "trending_searches": [
    {
      "rank": 1,
      "search_term": "NBA Finals",
      "country": "United States",
      "country_code": "united_states",
      "collected_at": "2026-06-16T10:30:00"
    }
  ],
  "realtime_trends": [
    {
      "title": "Breaking News Topic",
      "geo": "US",
      "collected_at": "2026-06-16T10:30:00"
    }
  ],
  "categories": [
    {
      "id": 3,
      "name": "Arts & Entertainment",
      "full_path": "Arts & Entertainment",
      "depth": 0,
      "parent_id": null,
      "parent_name": "(root)"
    }
  ],
  "summary": {
    "total_trending_searches": 150,
    "total_realtime_trends": 20,
    "total_categories": 1450,
    "countries_covered": ["United States", "Germany", "Japan"]
  }
}
```

### Saved Files

When using `--save`, files are saved to `demo_output/categories/`:

- `driver_list_YYYYMMDD_HHMMSS.json` - Complete driver list
- `trending_searches_YYYYMMDD_HHMMSS.csv` - Trending searches table
- `categories_YYYYMMDD_HHMMSS.csv` - Category hierarchy table
- `realtime_trends_YYYYMMDD_HHMMSS.csv` - Real-time trends table

### Usage Examples

#### Example 1: Get Global Trending Searches

```bash
python trend_categories.py --trends-only --save json
```

Returns trending searches from 15 countries in a driver list format.

#### Example 2: Retail-Focused Analysis

```bash
python trend_categories.py --all --retail --save both
```

Gets trending searches + retail categories, saves to both CSV and JSON.

#### Example 3: Real-Time Monitoring

```bash
python trend_categories.py --trends-only --realtime --geo US
```

Fetches both daily and real-time trending searches for the US.

#### Example 4: Category Research

```bash
python trend_categories.py --categories-only --filter fashion --tree
```

Shows fashion-related categories in a tree structure.

#### Example 5: Multi-Country Comparison

```bash
python trend_categories.py --trends-only \
  --countries "United States" "United Kingdom" Germany France Japan \
  --save csv
```

Compares trending searches across 5 countries.

### Programmatic Usage

You can also import and use the functions in your Python code:

```python
from trend_categories import (
    fetch_trending_searches,
    fetch_categories,
    build_driver_list,
)

# Fetch trending searches
trending_df = fetch_trending_searches(
    countries=["United States", "Germany"]
)

# Fetch categories
raw_cats = fetch_categories()
categories_df = build_dataframe(raw_cats)

# Build driver list
driver_list = build_driver_list(trending_df, categories_df)

print(f"Total trends: {driver_list['summary']['total_trending_searches']}")
```

### Available Countries

The following countries are supported for trending searches:

- 🇺🇸 United States
- 🇬🇧 United Kingdom
- 🇩🇪 Germany
- 🇫🇷 France
- 🇨🇦 Canada
- 🇦🇺 Australia
- 🇯🇵 Japan
- 🇧🇷 Brazil
- 🇮🇳 India
- 🇰🇷 South Korea
- 🇮🇹 Italy
- 🇪🇸 Spain
- 🇲🇽 Mexico
- 🇳🇱 Netherlands
- 🇸🇪 Sweden

### Notes

- **Rate Limiting**: The script includes automatic rate limiting (2 seconds between requests)
- **Retries**: Failed requests are automatically retried (default: 3 attempts)
- **No API Key Required**: Uses the unofficial pytrends library (no Google API key needed)
- **Data Freshness**: Trending searches are updated multiple times per day by Google

### Troubleshooting

**"Import pytrends could not be resolved"**
```bash
pip install pytrends
```

**"429 Too Many Requests"**
- Increase sleep time between requests
- Reduce number of countries
- Try again later

**"No data returned"**
- Some countries may have limited trending data
- Try a different country or time of day
- Check your internet connection

---

## pytrends_collector.py.py

The main collector class for fetching comprehensive Google Trends data including interest over time, geographic breakdowns, related queries, and more. See the file itself for detailed documentation.
