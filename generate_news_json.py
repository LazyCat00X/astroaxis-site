#!/usr/bin/env python3
"""Generate external JSON file for frontend to fetch."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DEPLOY_DIR = BASE_DIR / "deploy"

def load_source_locs():
    path = DATA_DIR / "source_locs.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    # Default locations
    return {
        "CoinDesk": [40.7, -74.0, "New York"],
        "CoinTelegraph": [51.5, -0.1, "London"],
        "The Block": [40.7, -74.0, "New York"],
        "Decrypt": [37.8, -122.4, "San Francisco"],
        "Blockworks": [40.7, -74.0, "New York"],
        "Bloomberg Crypto": [40.7, -74.0, "New York"],
        "Bloomberg": [40.7, -74.0, "New York"],
        "CNBC": [40.9, -73.9, "Englewood Cliffs"],
        "FT Tech": [51.5, -0.1, "London"],
        "TechCrunch": [37.8, -122.4, "San Francisco"],
        "ArsTechnica": [42.4, -71.1, "Boston"],
        "Wired": [37.8, -122.4, "San Francisco"],
        "Reuters": [51.5, -0.1, "London"],
        "BBC World": [51.5, -0.1, "London"],
        "SCMP": [22.3, 114.2, "Hong Kong"],
        "The Guardian": [51.5, -0.1, "London"],
        "New York Times": [40.7, -74.0, "New York"],
        "Washington Post": [38.9, -77.0, "Washington DC"],
        "動區動趨 (BlockTempo)": [25.0, 121.5, "Taipei"],
        "區塊客 (Blockcast)": [25.0, 121.5, "Taipei"],
        "科技新報": [25.0, 121.5, "Taipei"],
        "鉅亨網": [25.0, 121.5, "Taipei"],
        "香港經濟日報": [22.3, 114.2, "Hong Kong"],
    }

def main():
    # Load articles
    with open(DATA_DIR / "articles.json") as f:
        articles = json.load(f)
    
    # Filter summarized articles
    summarized = [a for a in articles if a.get("summarized") and a.get("ai_summary")]
    summarized.sort(key=lambda a: a.get("published", ""), reverse=True)
    summarized = summarized[:100]
    
    # Build output
    articles_out = []
    for a in summarized:
        articles_out.append({
            "url": a["url"],
            "title": a["title"],
            "source": a["source"],
            "topic": a.get("topic", "General"),
            "category": a.get("category", "general"),
            "published": a.get("published", ""),
            "ai_summary": a.get("ai_summary", ""),
            "summaries": a.get("summaries", {}),
        })
    
    source_locs = load_source_locs()
    
    news_data = {
        "articles": articles_out,
        "sourceLocations": source_locs,
        "updated": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    
    # Write to deploy folder
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DEPLOY_DIR / "news-data.json"
    with open(output_path, "w") as f:
        json.dump(news_data, f, ensure_ascii=False, indent=2)
    
    print(f"Generated {output_path} ({len(articles_out)} articles, {len(source_locs)} sources)")

if __name__ == "__main__":
    main()
