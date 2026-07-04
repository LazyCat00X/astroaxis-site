#!/usr/bin/env python3
"""Generate sitemap.xml for AstroAxis."""
import json
from datetime import datetime, timezone
from pathlib import Path

BASE_URL = "https://lazycat00x.github.io/astroaxis-site/"

def generate_sitemap():
    DATA_DIR = Path(__file__).parent / "data"
    DEPLOY_DIR = Path(__file__).parent / "deploy"
    
    # Load articles
    articles_file = DATA_DIR / "articles.json"
    if articles_file.exists():
        with open(articles_file) as f:
            articles = json.load(f)
    else:
        articles = []
    
    # Generate sitemap XML
    urls = []
    
    # Main page
    urls.append({
        "loc": BASE_URL,
        "lastmod": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "changefreq": "hourly",
        "priority": "1.0"
    })
    
    # News-data JSON
    urls.append({
        "loc": BASE_URL + "news-data.json",
        "lastmod": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "changefreq": "hourly",
        "priority": "0.8"
    })
    
    # OG image
    urls.append({
        "loc": BASE_URL + "og-image.png",
        "changefreq": "monthly",
        "priority": "0.5"
    })
    
    # Build XML
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""
    for u in urls:
        lastmod = u.get('lastmod', now)
        xml += f"""  <url>
    <loc>{u['loc']}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{u['changefreq']}</changefreq>
    <priority>{u['priority']}</priority>
  </url>
"""
    xml += "</urlset>"
    
    # Write to deploy
    output_path = DEPLOY_DIR / "sitemap.xml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(xml)
    
    print(f"Generated sitemap.xml with {len(urls)} URLs")

if __name__ == "__main__":
    generate_sitemap()