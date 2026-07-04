#!/bin/bash
# AstroAxis deploy script — run pipeline + push to GitHub Pages
set -euo pipefail

cd /home/kevyn/projects/astroaxis
source .venv/bin/activate

# Step 1: Run full pipeline
echo "[$(date -u)] Starting pipeline..."
python3 run.py 2>&1
echo "[$(date -u)] Pipeline done."

# Step 2: Copy to deploy repo
cp output/index.html deploy/index.html

# Step 3: Generate external news JSON
python3 generate_news_json.py

# Step 4: Commit and push
cd deploy
git add index.html news-data.json
# Only commit if there are changes
if git diff --cached --quiet; then
    echo "[$(date -u)] No changes to deploy."
else
    git commit -m "Update $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    git push origin main 2>&1
    echo "[$(date -u)] Deployed to GitHub Pages."
fi
