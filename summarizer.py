#!/usr/bin/env python3
"""AstroAxis pipeline: Verify -> Neutralize -> Multi-language -> Source."""
import json, logging, os, time
from pathlib import Path
import requests

DATA_DIR = Path(__file__).parent / "data"
ARTICLES_FILE = DATA_DIR / "articles.json"
log = logging.getLogger("pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# GitHub Models API (free) - https://models.github.ai/inference
API_URL = "https://models.github.ai/inference/chat/completions"
MODEL = "openai/gpt-4o-mini"  # Free, fast
MAX_PER_RUN = int(os.environ.get("MAX_ARTICLES_PER_RUN", "2"))  # Very conservative
# Rate limit handling (GitHub Actions has very strict limits)
RATE_LIMIT_DELAY = 15  # Very long delay between calls

def get_api_key():
    KEY = ""
    for p in [Path(__file__).parent / ".env",
              Path(__file__).parent.parent.parent / ".hermes-luna" / ".env",
              Path.home() / ".hermes-luna" / ".env"]:
        if p.exists():
            with open(p) as f:
                for line in f:
                    if line.startswith("MODELS_API_TOKEN="):
                        KEY = line.split("=", 1)[1].strip()
                        break
        if KEY:
            break
    # Fallback to environment variable (for GitHub Actions)
    if not KEY:
        KEY = os.environ.get("MODELS_API_TOKEN", "")
    return KEY

API_KEY = get_api_key()

def call(system, user, temp=0.2, max_tok=500):
    if not API_KEY:
        return None
    payload = {"model": MODEL, "temperature": temp, "max_tokens": max_tok,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": user}]}
    headers = {"Authorization": f"Bearer {API_KEY}",
               "Content-Type": "application/json"}
    status = 0
    for attempt in range(5):
        try:
            r = requests.post(API_URL, json=payload, headers=headers, timeout=120)
            status = r.status_code
            r.raise_for_status()
            data = r.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if content and content.strip():
                return content.strip()
            log.warning("API returned empty content (attempt %d/%d)", attempt + 1, 5)
            if status == 429:
                time.sleep(15 * (attempt + 1))
            else:
                time.sleep(5)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            log.warning("API error (attempt %d/%d): %s", attempt + 1, 5, e)
            if status == 429:
                # Rate limit — exponential backoff
                time.sleep(15 * (attempt + 1))
            elif status >= 500:
                time.sleep(10)
            else:
                # 4xx other than 429 — likely permanent, give up
                if attempt < 2:
                    time.sleep(5)
                else:
                    return None
        except Exception as e:
            log.warning("API error (attempt %d/%d): %s", attempt + 1, 5, e)
            time.sleep(5)
    return None

# ── Step 1: Verify ──
VERIFY = """You are a fact-checker. Assess the article:
1. Source credibility
2. Specific evidence/citations
3. Opinion vs reporting
4. Loaded language
Output EXACTLY:
Credibility: HIGH|MEDIUM|LOW|UNVERIFIABLE
Reasoning: <1-2 sentences>
Has_Citations: YES|NO
Is_Opinion: YES|NO
Bias_Flag: YES|NO"""

# ── Step 2: Neutralize ──
NEUTRAL = """Rewrite ONLY the verifiable facts from this article in strictly neutral language:
- No emotional words
- No editorial opinions  
- No speculation
- Keep only: who, what, when, where
- Max 120 words
- Output the neutral text only, no headers"""

# ── Step 3: Multi-language ──
MULTI = """Translate this neutral news summary into ALL 5 languages. Keep facts identical.

[zh-HK]
• <Traditional Chinese>

[EN]
• <English>

[zh-CN]
• <Simplified Chinese>

[JA]
• <Japanese>

[KO]
• <Korean>"""

def verify(title, text):
    t = text[:4000] if text else ""
    result = call(VERIFY, f"Title: {title}\n\n{t}", 0.1, 250)
    if not result:
        return {"credibility": "ERROR"}
    out = {}
    for line in result.split("\n"):
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out

def neutralize(title, text):
    t = text[:5000] if text else ""
    result = call(NEUTRAL, f"Title: {title}\n\n{t}", 0.15, 400)
    return result or "(neutralize failed)"

def translate(neutral, title):
    result = call(MULTI, f"Title: {title}\n\nNeutral:\n{neutral}", 0.2, 700)
    if not result:
        return {"zh-HK": neutral}
    langs = {}; cur = None
    for line in result.split("\n"):
        ls = line.strip()
        if ls.startswith("[zh-HK]"): cur = "zh-HK"
        elif ls.startswith("[EN]"): cur = "en"
        elif ls.startswith("[zh-CN]"): cur = "zh-CN"
        elif ls.startswith("[JA]"): cur = "ja"
        elif ls.startswith("[KO]"): cur = "ko"
        elif cur and ls:
            langs[cur] = (langs.get(cur, "") + "\n" + ls).strip()
    if "zh-HK" not in langs or not langs["zh-HK"]:
        return {"zh-HK": result}
    return langs

def load_articles():
    if ARTICLES_FILE.exists():
        with open(ARTICLES_FILE) as f:
            return json.load(f)
    return []

def save_articles(articles):
    ARTICLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ARTICLES_FILE, "w") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def run():
    articles = load_articles()
    if not articles:
        return 0
    pending = [a for a in articles if not a.get("summarized") or a.get("needs_multilang")]
    pending.sort(key=lambda a: a.get("published", ""), reverse=True)
    pending = pending[:MAX_PER_RUN]
    if not pending:
        log.info("All done")
        return 0
    count = 0
    for art in pending:
        text = art.get("full_text", "") or art.get("summary", "")
        title = art.get("title", "")
        url = art.get("url", "")
        if not text:
            art["summarized"] = True
            art["ai_summary"] = "(no content)"
            continue
        log.info("── %s ──", title[:50])
        log.info("  Step 1/3: Verify")
        v = verify(title, text)
        art["verification"] = v
        cred = v.get("Credibility", "UNKNOWN")
        log.info("    -> %s", cred)
        if cred in ("LOW", "UNVERIFIABLE"):
            art["summarized"] = True
            art["ai_summary"] = f"[Skipped: {cred}]"
            art["summaries"] = {"zh-HK": f"[此文可信度評級為 {cred}，暫不處理]"}
            count += 1
            continue
        log.info("  Step 2/3: Neutralize")
        neutral = neutralize(title, text)
        art["neutral_text"] = neutral
        log.info("  Step 3/3: Translate")
        summaries = translate(neutral, title)
        art["summaries"] = summaries
        art["ai_summary"] = summaries.get("zh-HK", summaries.get("en", ""))
        art["summarized"] = True
        art["source_url"] = url
        log.info("  ✅ %s", ", ".join(summaries.keys()))
        count += 1
        # Save after each article so partial progress isn't lost on timeout
        save_articles(articles)
        time.sleep(RATE_LIMIT_DELAY)
    if count == 0:
        save_articles(articles)  # save any skipped articles
    log.info("Done: %d articles", count)
    return count

if __name__ == "__main__":
    run()
