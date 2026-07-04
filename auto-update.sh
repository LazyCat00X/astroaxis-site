#!/bin/bash
# AstroAxis auto-update — crawl, summarize, deploy globe with fresh data
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
source .venv/bin/activate 2>/dev/null || source .venv/bin/activate

echo "=== AstroAxis Auto-Update $(date -u) ==="

# Step 1: Fetch timeline historical events (daily)
python3 timeline_fetcher.py 2>&1 | tail -2

# Step 2: Crawl new articles
python3 crawler.py 2>&1 | tail -3

# Step 3: Summarize (up to 30 per run)
MAX_ARTICLES_PER_RUN=30 python3 summarizer.py 2>&1 | tail -3

# Step 4: Generate fresh globe data for deploy
python3 generate_globe_data.py

# Step 5: Generate external JSON for frontend fetch
python3 generate_news_json.py

# Step 6: Generate sitemap for SEO
python3 generate_sitemap.py

# Step 7: Deploy to GitHub Pages
cd deploy
git add index.html news-data.json sitemap.xml robots.txt
if git diff --cached --quiet; then
    echo "No changes to deploy."
else
    git commit -m "Update $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    git push origin main 2>&1
    echo "Deployed to GitHub Pages."
fi

echo "=== Done $(date -u) ==="
