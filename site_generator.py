#!/usr/bin/env python3
"""Static site generator — produce a beautiful dark-themed news site."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"
ARTICLES_FILE = DATA_DIR / "articles.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("sitegen")

SITE_TITLE = "AstroAxis 鏈聞"
SITE_DESCRIPTION = "全球加密貨幣與金融新聞・AI 摘要・繁體中文"
BASE_URL = "https://lazycat00x.github.io/astroaxis-site"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🔗</text></svg>">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#0a0a0f;
  --bg2:#12121a;
  --bg3:#1a1a26;
  --border:#2a2a3a;
  --text:#e4e4ec;
  --text2:#8888a0;
  --accent:#6366f1;
  --accent2:#818cf8;
  --green:#22c55e;
  --red:#ef4444;
  --yellow:#eab308;
  --blue:#3b82f6;
  --orange:#f97316;
}}
body{{
  background:var(--bg);
  color:var(--text);
  font-family:'Inter','Noto Sans SC',-apple-system,sans-serif;
  line-height:1.6;
  min-height:100vh;
}}
.container{{max-width:1200px;margin:0 auto;padding:0 20px}}

/* Header */
.header{{
  background:var(--bg2);
  border-bottom:1px solid var(--border);
  padding:24px 0;
  position:sticky;top:0;z-index:100;
  backdrop-filter:blur(12px);
}}
.header-inner{{
  display:flex;align-items:center;justify-content:space-between;
  flex-wrap:wrap;gap:12px;
}}
.header h1{{font-size:24px;font-weight:700;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.header .subtitle{{color:var(--text2);font-size:14px}}
.header .meta{{color:var(--text2);font-size:13px}}

/* Filters */
.filters{{
  display:flex;gap:8px;flex-wrap:wrap;padding:16px 0;
  position:sticky;top:72px;z-index:99;
  background:var(--bg);
  border-bottom:1px solid var(--border);
}}
.filter-btn{{
  background:var(--bg3);color:var(--text2);border:1px solid var(--border);
  padding:6px 14px;border-radius:20px;font-size:13px;cursor:pointer;
  transition:all 0.2s;
}}
.filter-btn:hover,.filter-btn.active{{background:var(--accent);color:#fff;border-color:var(--accent)}}

/* Article Grid */
.grid{{display:grid;grid-template-columns:1fr;gap:16px;padding:20px 0 60px}}
@media(min-width:768px){{.grid{{grid-template-columns:1fr 1fr}}}}
@media(min-width:1024px){{.grid{{grid-template-columns:1fr 1fr 1fr}}}}

/* Article Card */
.card{{
  background:var(--bg2);border:1px solid var(--border);border-radius:12px;
  padding:20px;transition:all 0.25s;display:flex;flex-direction:column;
}}
.card:hover{{border-color:var(--accent);transform:translateY(-2px);box-shadow:0 8px 30px rgba(99,102,241,0.1)}}
.card-tags{{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}}
.tag{{
  font-size:11px;padding:2px 8px;border-radius:4px;font-weight:500;
}}
.tag.crypto{{background:rgba(99,102,241,0.15);color:var(--accent2)}}
.tag.finance{{background:rgba(34,197,94,0.15);color:var(--green)}}
.tag.tech{{background:rgba(59,130,246,0.15);color:var(--blue)}}
.tag.bitcoin{{background:rgba(249,115,22,0.15);color:var(--orange)}}
.tag.ethereum{{background:rgba(99,102,241,0.15);color:var(--accent2)}}
.tag.defi{{background:rgba(34,197,94,0.15);color:var(--green)}}
.tag.regulation{{background:rgba(239,68,68,0.15);color:var(--red)}}
.tag.policy{{background:rgba(234,179,8,0.15);color:var(--yellow)}}
.tag.ai{{background:rgba(59,130,246,0.15);color:var(--blue)}}
.tag.trading{{background:rgba(249,115,22,0.15);color:var(--orange)}}
.tag.macro{{background:rgba(139,92,246,0.15);color:#a78bfa}}
.tag.general{{background:rgba(136,136,160,0.15);color:var(--text2)}}

.card-title{{
  font-size:15px;font-weight:600;line-height:1.4;margin-bottom:8px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}}
.card-title a{{color:var(--text);text-decoration:none}}
.card-title a:hover{{color:var(--accent2)}}

.card-summary{{
  font-size:13px;color:var(--text2);flex:1;margin-bottom:12px;
  display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden;
}}

.card-meta{{
  font-size:12px;color:var(--text2);display:flex;justify-content:space-between;
  align-items:center;border-top:1px solid var(--border);padding-top:12px;margin-top:auto;
}}
.card-source{{font-weight:500;color:var(--accent2)}}
.card-time{{font-size:11px}}

/* Loading / No articles */
.empty-state{{text-align:center;padding:80px 20px;color:var(--text2)}}
.empty-state h2{{font-size:20px;margin-bottom:8px;color:var(--text)}}
.empty-state p{{font-size:14px}}

/* Footer */
.footer{{
  text-align:center;padding:24px;color:var(--text2);font-size:12px;
  border-top:1px solid var(--border);
}}

/* Source badge */
.source-emoji{{margin-right:4px}}
.lang-badge{{font-size:10px;opacity:0.6;margin-left:4px}}
</style>
</head>
<body>

<header class="header">
<div class="container header-inner">
  <div>
    <h1>{title}</h1>
    <div class="subtitle">{description}</div>
  </div>
  <div class="meta">
    🕐 更新於 {updated}
  </div>
</div>
</header>

<div class="container">
<div class="filters" id="filters">
  <button class="filter-btn active" data-filter="all">All</button>
  {filter_buttons}
</div>

<div class="grid" id="grid">
  {articles_html}
</div>
</div>

<footer class="footer">
  <div>{title} · 自動聚合 AI 摘要 · 僅供參考，不構成投資建議</div>
  <div style="margin-top:4px">資料來源：{source_count} 個新聞源 · {article_count} 篇文章</div>
</footer>

<script>
document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const filter = btn.dataset.filter;
    document.querySelectorAll('.card').forEach(card => {{
      if (filter === 'all' || card.dataset.topics?.includes(filter)) {{
        card.style.display = 'flex';
      }} else {{
        card.style.display = 'none';
      }}
    }});
  }});
}});
</script>

</body>
</html>"""


TOPIC_COLORS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "DeFi": "defi",
    "NFT": "crypto",
    "Regulation": "regulation",
    "Policy": "policy",
    "AI": "ai",
    "Trading": "trading",
    "Macro": "macro",
    "Crypto": "crypto",
    "Finance": "finance",
    "Tech": "tech",
}


def time_ago(pub_str):
    """Human-readable time difference."""
    try:
        pub = datetime.fromisoformat(pub_str)
        now = datetime.now(timezone.utc)
        diff = now - pub
        total_seconds = int(diff.total_seconds())
        if total_seconds < 3600:
            m = max(1, total_seconds // 60)
            return f"{m}分鐘前"
        elif total_seconds < 86400:
            h = total_seconds // 3600
            return f"{h}小時前"
        elif total_seconds < 172800:
            return "昨天"
        else:
            d = total_seconds // 86400
            return f"{d}天前"
    except Exception:
        return ""


def generate():
    articles = load_articles()
    
    if not articles:
        log.info("No articles to generate site")
        _write_empty()
        return
    
    # Sort by published date (newest first)
    articles.sort(key=lambda a: a.get("published", ""), reverse=True)
    
    # Collect all unique topics for filter buttons
    all_topics = set()
    for a in articles:
        t = a.get("topic", "General")
        all_topics.add(t)
    
    # Prioritize common topics
    topic_order = ["Bitcoin", "Ethereum", "DeFi", "AI", "Regulation", "Policy", "Trading", "Macro", "Crypto", "Finance", "Tech"]
    sorted_topics = sorted(all_topics, key=lambda t: (topic_order.index(t) if t in topic_order else 99, t))
    
    filter_buttons = ""
    for topic in sorted_topics:
        filter_buttons += f'<button class="filter-btn" data-filter="{topic.lower()}">{topic}</button>\n'
    
    # Build article cards HTML
    articles_html = ""
    for a in articles:
        title = a.get("title", "Untitled")
        url = a.get("url", "")
        source = a.get("source", "")
        topic = a.get("topic", "General")
        published = a.get("published", "")
        summary = a.get("ai_summary", "") or a.get("summary", "")
        lang = a.get("lang", "en")
        
        if not summary or summary == "(no content available)":
            summary = a.get("summary", "")[:200]
        
        # Clean summary: remove "Original Title:" line if present
        summary_clean = summary
        if "Original Title:" in summary:
            parts = summary.split("Summary:", 1)
            if len(parts) > 1:
                summary_clean = parts[1].strip()
            else:
                summary_clean = summary.split("Original Title:")[0].strip()
        
        # Format bullet points with line breaks
        summary_html = summary_clean.replace("\n", "<br>")
        
        tag_class = TOPIC_COLORS.get(topic, "general")
        time_str = time_ago(published)
        
        # Topic filter data attribute includes all relevant tags
        filter_data = topic.lower()
        
        articles_html += f"""
<div class="card" data-topics="{filter_data}">
<div class="card-tags">
<span class="tag {tag_class}">{topic}</span>
</div>
<h3 class="card-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>
<div class="card-summary">{summary_html}</div>
<div class="card-meta">
  <span class="card-source">{source}</span>
  <span class="card-time">{time_str}</span>
</div>
</div>"""
    
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    
    html = HTML_TEMPLATE.format(
        title=SITE_TITLE,
        description=SITE_DESCRIPTION,
        updated=now_str,
        filter_buttons=filter_buttons,
        articles_html=articles_html,
        source_count=len(set(a.get("source", "") for a in articles)),
        article_count=len(articles),
    )
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "index.html"
    with open(output_path, "w") as f:
        f.write(html)
    
    log.info("Generated site: %s (%d articles)", output_path, len(articles))
    return output_path


def load_articles():
    if ARTICLES_FILE.exists():
        with open(ARTICLES_FILE) as f:
            return json.load(f)
    return []


def _write_empty():
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    html = HTML_TEMPLATE.format(
        title=SITE_TITLE,
        description=SITE_DESCRIPTION,
        updated=now_str,
        filter_buttons="",
        articles_html='<div class="empty-state"><h2>📡 正在收集新聞...</h2><p>首次運行需爬取文章，請稍後再來</p></div>',
        source_count=0,
        article_count=0,
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "index.html", "w") as f:
        f.write(html)


if __name__ == "__main__":
    generate()
