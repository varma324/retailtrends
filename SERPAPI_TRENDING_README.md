# SerpAPI Google Trends - Trending Now

This script uses SerpAPI to fetch real-time Google Trends "Trending Now" data for the US region and other countries.

## Features

✅ **Real-time trending searches** from Google Trends  
✅ **Search volume metrics** with traffic data  
✅ **Increase percentages** showing trend growth  
✅ **Category classification** (Sports, Entertainment, etc.)  
✅ **Related queries** and trend breakdowns  
✅ **JSON export** for data analysis  
✅ **Multiple region support** (US, GB, DE, etc.)

## Prerequisites

### API Key
You need a SerpAPI key. Get one at: https://serpapi.com/

The key is stored in: `retailtrends/config/.env`
```env
serpAPIkey=your_api_key_here
```

### Dependencies
```bash
pip install requests python-dotenv
```

## Usage

### Get Current Trending Data (US)
```bash
python get_serpapi_trending.py --last-7-days --save json
```

### Get Trending Data for Other Regions
```bash
# United Kingdom
python get_serpapi_trending.py --geo GB --save json

# Germany
python get_serpapi_trending.py --geo DE --save json

# France
python get_serpapi_trending.py --geo FR --save json
```

### Simple Query (Display Only)
```bash
python get_serpapi_trending.py --geo US
```

## Output

### Console Output
The script displays:
- Top 15 trending searches
- Search volume (number of searches)
- Increase percentage (+1000% = 10x growth)
- Categories (Sports, Entertainment, etc.)
- Related queries

### Example Output
```
🔥 GOOGLE TRENDS - TRENDING NOW (US)
======================================================================

🔥 Current Trending Searches (546 items)
----------------------------------------------------------------------

1. messi
   Search Volume: 1,000,000
   Increase: +1000%
   Categories: Sports
   Related: lionel messi, messi age, how old is messi

2. portugal
   Search Volume: 200,000
   Increase: +700%
   Categories: Sports
   Related: dr congo, portugal vs, portugal vs congo
```

### JSON Output
Data is saved to: `demo_output/serpapi_trending/serpapi_trending_US_YYYYMMDD_HHMMSS.json`

Structure:
```json
[
  {
    "date": "2026-06-17",
    "data": {
      "search_metadata": { ... },
      "trending_searches": [
        {
          "query": "messi",
          "search_volume": 1000000,
          "increase_percentage": 1000,
          "categories": [{"id": 17, "name": "Sports"}],
          "trend_breakdown": ["lionel messi", "messi age", ...]
        }
      ]
    }
  }
]
```

## API Documentation

- **SerpAPI Docs**: https://serpapi.com/search?engine=google_trends_trending_now
- **Playground**: https://serpapi.com/playground

## Data Fields

| Field | Description |
|-------|-------------|
| `query` | The trending search term |
| `search_volume` | Estimated number of searches |
| `increase_percentage` | Growth rate (1000 = 10x increase) |
| `categories` | Topic categories (Sports, News, etc.) |
| `trend_breakdown` | Related search queries |
| `start_timestamp` | When the trend started |
| `active` | Whether trend is currently active |

## Supported Regions

Use 2-letter country codes:
- `US` - United States
- `GB` - United Kingdom
- `DE` - Germany
- `FR` - France
- `JP` - Japan
- `CA` - Canada
- `AU` - Australia
- And many more...

## Notes

⚠️ **Historical Data**: The SerpAPI `google_trends_trending_now` endpoint provides current/recent trending data. For historical trends over specific date ranges (7 days, 30 days), consider using:
- The `pytrends` library (see `retailtrends/src/collectors/trending_7days.py`)
- SerpAPI's `google_trends` engine (different from `google_trends_trending_now`)

✅ **Rate Limits**: SerpAPI has rate limits based on your plan. The script includes a 1-second delay between requests.

✅ **Data Freshness**: Trending data updates frequently (every few minutes to hours).

## Comparison with PyTrends

| Feature | SerpAPI | PyTrends |
|---------|---------|----------|
| **Real-time trends** | ✅ Yes | ❌ Limited |
| **Search volume numbers** | ✅ Yes | ❌ Relative only |
| **Historical data** | ⚠️ Current only | ✅ Up to 5 years |
| **Rate limits** | Plan-based | IP-based |
| **Cost** | Paid | Free |
| **Reliability** | High | Variable |

## Troubleshooting

### "API Error" or 400 Bad Request
- Check your API key in `.env`
- Verify the region code is valid (2 letters)
- Check your SerpAPI account has remaining credits

### Empty Results
- The region might not have data available
- Try a different region (US, GB are most reliable)

### Import Errors
```bash
pip install -r requirements.txt
```

## Examples

### Analyze Retail Trends
```bash
# Get US retail trends
python get_serpapi_trending.py --geo US --save json

# Compare with UK trends  
python get_serpapi_trending.py --geo GB --save json

# Check trending products
grep -i "product\|shopping\|buy" demo_output/serpapi_trending/*.json
```

### Monitor Sports Events
```bash
# Get current sports trends
python get_serpapi_trending.py --geo US | grep -i "sports"
```

## License

This script uses:
- **SerpAPI**: Commercial API (subscription required)
- **Python**: MIT License
- **Requests**: Apache 2.0

---

**Created**: June 17, 2026  
**Last Updated**: June 17, 2026  
**Script**: `get_serpapi_trending.py`  
**Output Directory**: `demo_output/serpapi_trending/`
