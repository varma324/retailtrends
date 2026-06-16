# Where is the Driver List? - Quick Guide

## 📍 Location of Driver List

The **driver list** is a JSON/dictionary that contains all Google Trends categories with their IDs. Here's where to find it:

### 1. **Saved JSON File** (Recommended)

**File Path**: `retailtrends/demo_output/categories/driver_list_YYYYMMDD_HHMMSS.json`

**Current File**: `/Users/mudun/Downloads/retailtrends/retailtrends/demo_output/categories/driver_list_20260616_084106.json`

**Size**: 347 KB (1,426 categories)

---

## 🚀 How to Generate the Driver List

### Quick Command
```bash
cd /Users/mudun/Downloads/retailtrends

# Generate driver list JSON
python retailtrends/src/collectors/trend_categories.py \
  --categories-only \
  --save json
```

### Custom Options
```bash
# Retail categories only
python retailtrends/src/collectors/trend_categories.py \
  --categories-only \
  --retail \
  --save json

# Filter by keyword
python retailtrends/src/collectors/trend_categories.py \
  --categories-only \
  --filter "fashion" \
  --save json

# Top-level categories only
python retailtrends/src/collectors/trend_categories.py \
  --categories-only \
  --depth 0 \
  --save json

# Save as both JSON and CSV
python retailtrends/src/collectors/trend_categories.py \
  --categories-only \
  --save both
```

---

## 📊 Driver List Structure

### JSON Format
```json
{
  "generated_at": "2026-06-16T08:41:06.302107",
  "trending_searches": [],
  "realtime_trends": [],
  "categories": [
    {
      "id": 3,
      "name": "Arts & Entertainment",
      "full_path": "Arts & Entertainment",
      "depth": 0,
      "parent_id": null,
      "parent_name": "(root)"
    },
    {
      "id": 18,
      "name": "Shopping",
      "full_path": "Shopping",
      "depth": 0,
      "parent_id": null,
      "parent_name": "(root)"
    },
    {
      "id": 68,
      "name": "Apparel",
      "full_path": "Shopping > Apparel",
      "depth": 1,
      "parent_id": 18,
      "parent_name": "Shopping"
    }
    // ... 1,426 total categories
  ],
  "summary": {
    "total_trending_searches": 0,
    "total_realtime_trends": 0,
    "total_categories": 1426,
    "countries_covered": []
  }
}
```

---

## 💻 Using the Driver List Programmatically

### Method 1: Load from JSON File
```python
import json

# Load the driver list
with open('retailtrends/demo_output/categories/driver_list_20260616_084106.json') as f:
    driver_list = json.load(f)

# Access categories
categories = driver_list['categories']
print(f"Total categories: {len(categories)}")

# Find shopping category ID
shopping_cats = [c for c in categories if 'shopping' in c['full_path'].lower()]
for cat in shopping_cats[:5]:
    print(f"ID: {cat['id']} - {cat['full_path']}")
```

### Method 2: Generate Directly in Python
```python
import sys
sys.path.insert(0, '/Users/mudun/Downloads/retailtrends')

from retailtrends.src.collectors.trend_categories import (
    fetch_categories,
    build_dataframe,
    build_driver_list,
    filter_retail_relevant
)
import pandas as pd

# Fetch categories
raw = fetch_categories()
df = build_dataframe(raw)

# Build driver list
driver_list = build_driver_list(pd.DataFrame(), df, None)

# Access the data
print(f"Total categories: {driver_list['summary']['total_categories']}")
print(f"Categories list length: {len(driver_list['categories'])}")

# Get shopping category IDs
shopping = [c for c in driver_list['categories'] if c['name'] == 'Shopping']
print(shopping[0])  # {'id': 18, 'name': 'Shopping', ...}
```

### Method 3: Call main() Function
```python
import sys
sys.path.insert(0, '/Users/mudun/Downloads/retailtrends')

from retailtrends.src.collectors import trend_categories

# The main() function returns the driver list
driver_list = trend_categories.main()

# Now you have the complete driver list dictionary
categories = driver_list['categories']
```

---

## 📁 File Locations

### Generated Files Directory
```
retailtrends/demo_output/categories/
├── driver_list_20260616_084106.json       # Complete driver list
├── categories_20260616_084106.csv          # Categories as CSV
└── ... (more timestamped files)
```

### Source Code Location
```
retailtrends/src/collectors/
├── trend_categories.py                     # Main script
├── README.md                               # Documentation
└── pytrends_collector.py.py               # Collector class
```

---

## 🔍 Example: Finding Category IDs

### Find All Shopping Categories
```bash
cd /Users/mudun/Downloads/retailtrends

# Show shopping categories
python -c "
import json
with open('retailtrends/demo_output/categories/driver_list_20260616_084106.json') as f:
    data = json.load(f)
shopping = [c for c in data['categories'] if 'shopping' in c['full_path'].lower()]
for cat in shopping[:10]:
    print(f\"{cat['id']:>5} | {cat['full_path']}\")
"
```

### Find Fashion Categories
```bash
python -c "
import json
with open('retailtrends/demo_output/categories/driver_list_20260616_084106.json') as f:
    data = json.load(f)
fashion = [c for c in data['categories'] if 'fashion' in c['full_path'].lower()]
for cat in fashion:
    print(f\"{cat['id']:>5} | {cat['full_path']}\")
"
```

---

## 📝 Key Fields in Driver List

| Field | Description | Example |
|-------|-------------|---------|
| `id` | Google Trends category ID | `18` |
| `name` | Category name | `"Shopping"` |
| `full_path` | Complete path from root | `"Shopping > Apparel"` |
| `depth` | Level in hierarchy (0=top) | `1` |
| `parent_id` | Parent category ID | `18` |
| `parent_name` | Parent category path | `"Shopping"` |

---

## 🎯 Common Use Cases

### 1. Get All Top-Level Categories (depth=0)
```python
import json
with open('retailtrends/demo_output/categories/driver_list_20260616_084106.json') as f:
    data = json.load(f)

top_level = [c for c in data['categories'] if c['depth'] == 0]
for cat in top_level:
    print(f"ID {cat['id']}: {cat['name']}")
```

### 2. Get All Retail Categories
```bash
python retailtrends/src/collectors/trend_categories.py \
  --categories-only \
  --retail \
  --save json \
  --no-print
```

### 3. Export to CSV for Excel
```bash
python retailtrends/src/collectors/trend_categories.py \
  --categories-only \
  --save csv
```

Then open: `retailtrends/demo_output/categories/categories_YYYYMMDD_HHMMSS.csv`

---

## 🔧 Quick Access Script

Save this as `get_driver_list.py`:

```python
#!/usr/bin/env python3
"""Quick script to get the latest driver list"""

import json
from pathlib import Path

# Find latest driver list file
output_dir = Path('retailtrends/demo_output/categories')
json_files = list(output_dir.glob('driver_list_*.json'))

if not json_files:
    print("No driver list found. Run:")
    print("  python retailtrends/src/collectors/trend_categories.py --categories-only --save json")
else:
    latest = max(json_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading: {latest}")
    
    with open(latest) as f:
        driver_list = json.load(f)
    
    print(f"\n✅ Loaded driver list")
    print(f"   Generated: {driver_list['generated_at']}")
    print(f"   Categories: {driver_list['summary']['total_categories']}")
    
    # Example: Show top-level categories
    top = [c for c in driver_list['categories'] if c['depth'] == 0]
    print(f"\n📁 Top-level categories ({len(top)}):")
    for cat in sorted(top, key=lambda x: x['name']):
        print(f"   [{cat['id']:>3}] {cat['name']}")
```

Run it:
```bash
python get_driver_list.py
```

---

## ✅ Summary

**The driver list is here**:
- 📄 **File**: `retailtrends/demo_output/categories/driver_list_20260616_084106.json`
- 📊 **Size**: 347 KB
- 🏷️ **Contains**: 1,426 Google Trends categories
- 🔢 **Format**: JSON dictionary with category IDs, names, and hierarchy

**To regenerate**:
```bash
python retailtrends/src/collectors/trend_categories.py --categories-only --save json
```

**To use in code**:
```python
import json
with open('path/to/driver_list.json') as f:
    driver_list = json.load(f)
categories = driver_list['categories']  # List of 1,426 categories
```
