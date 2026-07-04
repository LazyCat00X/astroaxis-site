#!/usr/bin/env python3
"""RSS feed crawler — fetch feeds, extract articles, deduplicate."""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent / "data"
FEEDS_FILE = Path(__file__).parent / "feeds.yaml"
ARTICLES_FILE = DATA_DIR / "articles.json"
CACHE_FILE = DATA_DIR / "cache.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("crawler")

# Load existing articles
def load_articles():
    if ARTICLES_FILE.exists():
        with open(ARTICLES_FILE) as f:
            return json.load(f)
    return []

def save_articles(articles):
    ARTICLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ARTICLES_FILE, "w") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def load_feeds():
    with open(FEEDS_FILE) as f:
        data = yaml.safe_load(f)
    return data.get("sources", [])

def fetch_rss(url, timeout=8):
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (compatible; NewsAggregator/1.0)"
        })
        resp.raise_for_status()
        return feedparser.parse(resp.content)
    except requests.exceptions.Timeout:
        log.warning("Timeout: %s", url)
        return None
    except Exception as e:
        log.warning("RSS fetch failed: %s — %s", url, e)
        return None

def extract_text_from_url(url, timeout=10):
    """Fallback: extract article text using readability-like approach."""
    try:
        resp = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        })
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        # Remove script/style
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()
        # Try article tag first
        article = soup.find("article")
        if not article:
            article = soup.find("main")
        if not article:
            article = soup.body
        if not article:
            return ""
        text = article.get_text(separator="\n", strip=True)
        # Clean up: deduplicate lines, limit length
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # Remove very short lines (likely noise)
        lines = [l for l in lines if len(l) > 20]
        text = "\n".join(lines[:200])  # first 200 meaningful lines
        return text[:8000]  # cap at 8K chars
    except Exception as e:
        log.debug("Text extraction failed: %s — %s", url, e)
        return ""

def parse_date(entry):
    """Try multiple date formats from RSS entry."""
    for attr in ["published_parsed", "updated_parsed"]:
        tp = getattr(entry, attr, None)
        if tp:
            try:
                return datetime(*tp[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)

def classify_article(title, summary, source_name, category):
    """Assign a topic tag based on keywords."""
    import re
    t = (title or "") + " " + (summary or "")
    t_lower = t.lower()

    def match_text(keyword):
        """Match with word boundaries for short keywords, substring for long."""
        if len(keyword) <= 3:
            # Short keywords need word boundaries to avoid false positives
            return bool(re.search(r'\b' + re.escape(keyword) + r'\b', t_lower))
        return keyword in t_lower

    # Source-based override: Bloomberg general articles shouldn't be AI-tagged
    # Only crypto/finance-specific Bloomberg articles get crypto/finance tags
    if source_name == "Bloomberg Crypto":
        # Bloomberg Crypto feed is specifically crypto news
        pass  # Use normal keyword matching
    elif source_name == "Bloomberg":
        # Bloomberg general feed - check for specific keywords, not generic "AI" in headlines
        if not any(kw in t_lower for kw in ["bitcoin", "ethereum", "crypto", "blockchain", "defi", "nft", "trading", "fed", "interest rate", "inflation", "gdp", "market"]):
            # Generic Bloomberg article - use category-based default
            if category == "finance":
                return "Finance"
            elif category == "general":
                return "World"

    topics = {
        "Bitcoin": ["bitcoin", "btc", "satoshi"],
        "Ethereum": ["ethereum", "vitalik", "以太坊"],
        "DeFi": ["defi", "lending", "liquidity", "yield", "compound", "aave", "uniswap"],
        "NFT": ["nft", "nfts", "collectible"],
        "Regulation": ["sec", "regulation", "cftc", "compliance", "lawsuit", "legal", "mica"],
        "Policy": ["fed", "federal reserve", "interest rate", "inflation", "monetary", "ecb", "central bank"],
        "AI": ["artificial intelligence", "gpt", "llm", "machine learning", "deep learning", "neural network", "chatgpt", "claude", "openai", "anthropic"],
        "Trading": ["trading", "price", "volatility", "arbitrage", "etf", "flows"],
        "Macro": ["economy", "gdp", "recession", "jobs", "employment", "treasury", "fiscal"],
        "World": ["world", "global", "international", "diplomatic", "foreign", "geopolitics", "war", "conflict", "treaty"],
        "Politics": ["politics", "political", "election", "government", "parliament", "president", "congress", "senate", "democrat", "republican", "vote", "voting", "trump", "biden"],
        "Health": ["health", "disease", "hospital", "medical", "covid", "pandemic", "vaccine", "outbreak"],
        "Science": ["science", "scientist", "research", "study", "discovery", "nasa", "space", "earthquake"],
        "Sports": ["sports", "sport", "soccer", "football", "olympic", "nba", "tennis", "athlete", "world cup"],
        "Entertainment": ["entertainment", "movie", "film", "music", "celebrity", "tv", "television", "hollywood", "box office"],
        "Finance": ["market", "stock", "bond", "investor", "ipo", "hedge", "fund", "portfolio", "dividend", "earnings", "revenue"],
    }

    for topic, keywords in topics.items():
        for kw in keywords:
            if match_text(kw):
                return topic
    return category.capitalize()

def crawl():
    articles = load_articles()
    cache = load_cache()
    seen_urls = {a["url"] for a in articles}
    feeds = load_feeds()
    
    new_count = 0
    skip_count = 0
    
    for source in feeds:
        name = source["name"]
        url = source["url"]
        category = source.get("category", "general")
        lang = source.get("lang", "en")
        
        log.info("Fetching: %s", name)
        parsed = fetch_rss(url)
        if not parsed:
            continue
        
        entries = getattr(parsed, "entries", [])
        if not entries:
            log.info("  No entries from %s", name)
            continue
        
        for entry in entries[:20]:  # top 20 per source
            link = entry.get("link", "").strip()
            if not link or link in seen_urls:
                skip_count += 1
                continue
            
            title = entry.get("title", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            pub_date = parse_date(entry)
            
            # Skip if too old (>7 days)
            age = datetime.now(timezone.utc) - pub_date
            if age.days > 7:
                continue
            
            # Get full text content
            full_text = cache.get(link, {}).get("full_text", "")
            if not full_text:
                full_text = extract_text_from_url(link)
                if full_text:
                    cache[link] = {"full_text": full_text}
            
            article = {
                "url": link,
                "title": title,
                "summary": summary,
                "full_text": full_text,
                "source": name,
                "category": category,
                "lang": lang,
                "topic": classify_article(title, summary, name, category),
                "published": pub_date.isoformat(),
                "crawled": datetime.now(timezone.utc).isoformat(),
                "summarized": False,
                "ai_summary": "",
            }
            articles.append(article)
            seen_urls.add(link)
            new_count += 1
        
        # Polite delay between sources
        time.sleep(0.5)
    
    # Keep only last 7 days, max 500 articles
    cutoff = datetime.now(timezone.utc).timestamp() - 7 * 86400
    articles = [a for a in articles 
                if datetime.fromisoformat(a["published"]).timestamp() > cutoff]
    articles = articles[-500:]
    
    save_articles(articles)
    save_cache(cache)
    
    log.info("Done: %d new, %d skipped, %d total", new_count, skip_count, len(articles))
    return new_count

if __name__ == "__main__":
    crawl()
