#!/bin/bash
# Quick start script for SerpAPI trending data collection

echo "════════════════════════════════════════════════════════"
echo "  🔥 SerpAPI Google Trends - Quick Start"
echo "════════════════════════════════════════════════════════"
echo ""

# Check if .env file exists
if [ ! -f "retailtrends/config/.env" ]; then
    echo "❌ Error: .env file not found!"
    echo "   Please create: retailtrends/config/.env"
    echo "   With content: serpAPIkey=your_api_key_here"
    exit 1
fi

# Check if dependencies are installed
echo "📦 Checking dependencies..."
python -c "import requests, dotenv" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Installing dependencies..."
    pip install requests python-dotenv
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  Choose an option:"
echo "════════════════════════════════════════════════════════"
echo ""
echo "  1. Get US trending data (default)"
echo "  2. Get UK trending data"
echo "  3. Get trending data for custom region"
echo "  4. Analyze existing data"
echo ""
read -p "Enter choice [1-4]: " choice

case $choice in
    2)
        echo ""
        echo "🇬🇧 Fetching UK trending data..."
        python get_serpapi_trending.py --geo GB --last-7-days --save json
        ;;
    3)
        echo ""
        read -p "Enter 2-letter country code (e.g., DE, FR, JP): " region
        echo ""
        echo "🌍 Fetching $region trending data..."
        python get_serpapi_trending.py --geo "$region" --last-7-days --save json
        ;;
    4)
        echo ""
        echo "📊 Analyzing existing data..."
        python analyze_serpapi_trends.py
        ;;
    *)
        echo ""
        echo "🇺🇸 Fetching US trending data..."
        python get_serpapi_trending.py --geo US --last-7-days --save json
        ;;
esac

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✨ Done! Check demo_output/serpapi_trending/"
echo "════════════════════════════════════════════════════════"
