#!/usr/bin/env python3
"""Generate deploy/index.html + data files for AstroAxis.

globe.html now uses dynamic fetch('news-data.json') and fetch('timeline-data.json')
instead of inline injection. This script writes those JSON files into deploy/ and
copies globe.html as deploy/index.html.
"""
import json, re, sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DEPLOY_DIR = BASE_DIR / "deploy"
SRC_LOCS_PATHS = [
    DATA_DIR / "source_locs.json",
    Path("/tmp/source_locs.json"),
]

# Default source locations (fallback if /tmp file missing)
DEFAULT_SOURCE_LOCS = {
    "CoinDesk": [40.7, -74.0, "New York"],
    "CoinTelegraph": [51.5, -0.1, "London"],
    "The Block": [40.7, -74.0, "New York"],
    "Decrypt": [37.8, -122.4, "San Francisco"],
    "Blockworks": [40.7, -74.0, "New York"],
    "Bloomberg Crypto": [40.7, -74.0, "New York"],
    "Bloomberg": [40.7, -74.0, "New York"],
    "CNBC": [40.9, -73.9, "Englewood Cliffs"],
    "WSJ Markets": [40.7, -74.0, "New York"],
    "FT Tech": [51.5, -0.1, "London"],
    "TechCrunch": [37.8, -122.4, "San Francisco"],
    "ArsTechnica": [42.4, -71.1, "Boston"],
    "Wired": [37.8, -122.4, "San Francisco"],
    "Chainlink (Chinese)": [31.2, 121.5, "Shanghai"],
    "Unchained": [40.7, -74.0, "New York"],
    "DL News": [51.5, -0.1, "London"],
    "Bankless": [37.8, -122.4, "San Francisco"],
    "Reuters": [51.5, -0.1, "London"],
    "BBC World": [51.5, -0.1, "London"],
    "Reuters World": [51.5, -0.1, "London"],
    "AP News": [40.7, -74.0, "New York"],
    "Al Jazeera": [25.3, 51.5, "Doha"],
    "NPR": [38.9, -77.0, "Washington DC"],
    "Nikkei Asia": [35.7, 139.7, "Tokyo"],
    "SCMP": [22.3, 114.2, "Hong Kong"],
    "The Guardian": [51.5, -0.1, "London"],
    "New York Times": [40.7, -74.0, "New York"],
    "Washington Post": [38.9, -77.0, "Washington DC"],
    "Time": [40.7, -74.0, "New York"],
    "The Economist": [51.5, -0.1, "London"],
    "動區動趨 (BlockTempo)": [25.0, 121.5, "Taipei"],
    "區塊客 (Blockcast)": [25.0, 121.5, "Taipei"],
    "科技新報": [25.0, 121.5, "Taipei"],
    "鉅亨網": [25.0, 121.5, "Taipei"],
    "香港經濟日報": [22.3, 114.2, "Hong Kong"],
}


def load_source_locs():
    """Load source locations, with fallback."""
    for path in SRC_LOCS_PATHS:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    # Try extracting from existing deploy/index.html
    deploy_html = DEPLOY_DIR / "index.html"
    if deploy_html.exists():
        with open(deploy_html) as f:
            html = f.read()
        m = re.search(r'"sourceLocations":(\{[^}]+\})', html)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
    print("WARNING: Using default source locations (no /tmp/source_locs.json)", file=sys.stderr)
    return DEFAULT_SOURCE_LOCS


def load_articles():
    with open(BASE_DIR / "data" / "articles.json") as f:
        return json.load(f)


def main():
    articles = load_articles()

    # Filter to summarized only
    summarized = [a for a in articles if a.get("summarized") and a.get("ai_summary")]
    summarized.sort(key=lambda a: a.get("published", ""), reverse=True)
    summarized = summarized[:500]

    # Build article payload
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
    }

    # Write news-data.json to deploy directory
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)
    news_json_path = DEPLOY_DIR / "news-data.json"
    with open(news_json_path, "w") as f:
        json.dump(news_data, f, ensure_ascii=False)
    print(f"Wrote {len(articles_out)} articles to {news_json_path}")

    # Write timeline-data.json to deploy directory
    timeline_file = DATA_DIR / "timeline_recent.json"
    if timeline_file.exists():
        with open(timeline_file) as f:
            timeline_data = json.load(f)
        tl_path = DEPLOY_DIR / "timeline-data.json"
        with open(tl_path, "w") as f:
            json.dump(timeline_data, f, ensure_ascii=False)
        total_events = sum(len(v) for v in timeline_data.values())
        print(f"Wrote timeline: {total_events} events, {len(timeline_data)} years")
    else:
        print("WARNING: data/timeline_recent.json not found, skipping timeline", file=sys.stderr)

    # Copy globe.html as deploy/index.html (no inline injection needed)
    with open(BASE_DIR / "globe.html") as f:
        html = f.read()
    index_path = DEPLOY_DIR / "index.html"
    with open(index_path, "w") as f:
        f.write(html)
    print(f"Copied globe.html -> {index_path}")


if __name__ == "__main__":
    main()
