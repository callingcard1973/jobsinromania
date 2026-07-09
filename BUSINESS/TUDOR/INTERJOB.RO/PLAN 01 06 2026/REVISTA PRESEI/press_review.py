"""Daily Romania press review: scrape RSS → Ollama summaries → WP post + RSS feed → A2 deploy."""

import base64
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests

_ENV_FILE = "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env"
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k, _v)

sys.path.insert(0, os.path.dirname(__file__))
from press_review_rss import fetch_articles, build_rss_feed

try:
    from facebook_news_publisher import FacebookNewsPublisher, load_page_tokens
except ImportError:
    FacebookNewsPublisher = None
    load_page_tokens = None

WP_URL   = "https://expatsinromania.org"
FB_PAGES_JSON = Path("/opt/ACTIVE/SCRAPERS/ROMANIA/data/fb_pages.json")
FB_PAGE_ID = "102068074657345"  # Expats in Romania
WP_USER  = os.getenv("WP_EXPATSINROMANIA_ORG_USER", "expatsinromania.org")
WP_PASS  = os.getenv("WP_EXPATSINROMANIA_ORG_PASS", "")   # set in wp_sites.env
DB_DSN   = "host=localhost dbname=interjob_master user=tudor password=REDACTED"
CPANEL_HOST  = "nl1-cl8-ats1.a2hosting.com"
CPANEL_USER  = "loaiidil"
CPANEL_TOKEN = os.getenv("A2_CPANEL_API_TOKEN", "")
DOCROOT  = "/home/loaiidil/expatsinromania.org"
RSS_LOCAL = "/tmp/press_review_feed.xml"
TOPIC_ORDER = ["Economy", "Energy", "Agriculture", "Real Estate", "Technology", "Labor",
              "Infrastructure", "Manufacturing", "Legal", "Politics", "Society", "Culture"]

def db_connect():
    return psycopg2.connect(DB_DSN)

def ensure_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS press_review_posts (
                id          SERIAL PRIMARY KEY,
                review_date DATE UNIQUE NOT NULL,
                wp_post_id  INTEGER,
                wp_url      TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS press_review_articles (
                id          SERIAL PRIMARY KEY,
                article_id  VARCHAR(32) UNIQUE NOT NULL,
                review_date DATE NOT NULL,
                source      TEXT,
                title       TEXT,
                link        TEXT,
                summary     TEXT,
                topic       TEXT
            );
        """)
    conn.commit()

def already_posted(conn, review_date) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM press_review_posts WHERE review_date=%s", (review_date,))
        return cur.fetchone() is not None

def save_post(conn, review_date, wp_post_id, wp_url):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO press_review_posts (review_date,wp_post_id,wp_url) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (review_date, wp_post_id, wp_url))
    conn.commit()

def save_articles(conn, review_date, articles):
    with conn.cursor() as cur:
        rows = [(a["id"], review_date, a["source"], a["title"], a["link"], a.get("summary",""), a["topic"])
                for a in articles]
        cur.executemany(
            """INSERT INTO press_review_articles (article_id,review_date,source,title,link,summary,topic)
               VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""", rows)
    conn.commit()

def recent_reviews_for_feed(conn, limit=30):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT p.review_date, p.wp_url,
                   string_agg(a.summary, ' | ' ORDER BY a.topic) AS summaries
            FROM press_review_posts p
            JOIN press_review_articles a ON a.review_date=p.review_date
            GROUP BY p.review_date, p.wp_url
            ORDER BY p.review_date DESC LIMIT %s
        """, (limit,))
        return cur.fetchall()

def summarize(desc: str, lang: str = "en", translator=None) -> str:
    """2-sentence English summary; translate RO→EN via Google Translate (free)."""
    if lang == "ro" and translator:
        try:
            translated_desc = translator.translate(desc[:500])  # cap for API
        except Exception:
            translated_desc = desc
        sentences = [s.strip() for s in translated_desc.replace("  ", " ").split(". ") if len(s.strip()) > 20]
        result = ". ".join(sentences[:2]) + ("." if sentences else "")
        return result[:200] if result else translated_desc[:200]
    sentences = [s.strip() for s in desc.replace("  ", " ").split(". ") if len(s.strip()) > 20]
    result = ". ".join(sentences[:2]) + ("." if sentences else "")
    return result[:200] if result else desc[:200]

def _wp_auth() -> str:
    return base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()

def wp_ensure_category(name: str = "Press Review") -> int:
    """Return WP category ID, creating it if missing."""
    headers = {"Authorization": f"Basic {_wp_auth()}"}
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories", params={"search": name}, headers=headers, timeout=15)
    cats = r.json() if r.ok else []
    if cats:
        return cats[0]["id"]
    r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/categories",
                       json={"name": name, "slug": "press-review"}, headers=headers, timeout=15)
    return r2.json().get("id", 1)

def wp_post(title: str, html_body: str, category_id: int) -> dict:
    headers = {"Authorization": f"Basic {_wp_auth()}",
               "Content-Type": "application/json"}
    payload = {
        "title":   title,
        "content": html_body,
        "status":  "publish",
        "categories": [category_id],
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", json=payload, headers=headers, timeout=30)
    if not r.ok:
        print(f"[ERROR] WP post failed: {r.status_code} {r.text[:200]}")
        return {}
    return r.json()

def build_html(articles, review_date) -> str:
    by_topic = defaultdict(list)
    for a in articles:
        by_topic[a["topic"]].append(a)

    source_names = ", ".join(sorted({a["source"] for a in articles}))
    total_stories = len(articles)

    parts = [
        '<div style="border-top: 3px solid #333; border-bottom: 3px solid #333; padding: 20px 0; margin-bottom: 30px; text-align: center;">',
        '<h1 style="margin: 0 0 5px 0; font-size: 28px; font-weight: bold;">ROMANIA PRESS REVIEW</h1>',
        f'<p style="margin: 5px 0; font-size: 20px; font-weight: bold;">{review_date.strftime("%B %d, %Y")}</p>',
        '<p style="margin: 10px 0; color: #666; font-size: 14px;">Business & Politics Intelligence | {0} sources | {1} stories | Updated 08:50 UTC</p>'.format(len({a["source"] for a in articles}), total_stories),
        '</div>',
    ]

    economy_articles = by_topic.get("Economy", [])
    if economy_articles:
        featured = economy_articles[0]
        parts.append('<div style="background-color: #f5f5f5; padding: 20px; border-left: 4px solid #2c3e50; margin-bottom: 30px;">')
        parts.append('<p style="margin: 0 0 10px 0; font-weight: bold; color: #2c3e50; font-size: 12px; text-transform: uppercase;">FEATURED STORY</p>')
        parts.append(f'<h2 style="margin: 0 0 10px 0; font-size: 20px; line-height: 1.3;"><a href="{featured["link"]}" target="_blank" rel="noopener" style="color: #2c3e50; text-decoration: none;">{featured["title"]}</a></h2>')
        summary = featured.get("summary", featured["desc"][:200])
        parts.append(f'<p style="margin: 0; font-size: 14px; color: #333; line-height: 1.6;">{summary}</p>')
        parts.append(f'<p style="margin: 10px 0 0 0; font-size: 12px; color: #666;"><em>Source: {featured["source"]}</em></p>')
        parts.append('</div>')

    for topic in TOPIC_ORDER:
        items = by_topic.get(topic, [])
        if not items:
            continue

        if topic == "Economy":
            items = items[1:] if len(items) > 1 else []
            if not items:
                continue

        story_word = "stories" if len(items) != 1 else "story"
        parts.append(f'<h2 style="margin-top: 25px; font-size: 16px; font-weight: bold; text-transform: uppercase; color: #2c3e50; border-bottom: 2px solid #e0e0e0; padding-bottom: 8px;">{topic} ({len(items)} {story_word})</h2>')

        for a in items:
            summary = a.get("summary", a["desc"][:200])
            parts.append('<div style="margin: 15px 0; padding: 0 0 15px 0; border-bottom: 1px solid #f0f0f0;">')
            parts.append(f'<h3 style="margin: 0 0 8px 0; font-size: 15px; line-height: 1.4;"><a href="{a["link"]}" target="_blank" rel="noopener" style="color: #2c3e50; text-decoration: none;">{a["title"]}</a></h3>')
            parts.append(f'<p style="margin: 0 0 8px 0; font-size: 13px; color: #555; line-height: 1.5;">{summary}</p>')
            parts.append(f'<p style="margin: 0; font-size: 11px; color: #999;"><em>{a["source"]}</em></p>')
            parts.append('</div>')

    parts.append('<hr style="margin-top: 30px; border: none; border-top: 1px solid #e0e0e0;"/>')
    parts.append(f'<p style="font-size: 11px; color: #999; margin-top: 15px;"><em>Press review auto-generated daily by ExpatsInRomania.org. Sources: {source_names}.</em></p>')

    return "\n".join(parts)

def deploy_to_cpanel(local_path: str, remote_rel: str) -> bool:
    """Upload file via cPanel UAPI FileManager (creates dir if needed)."""
    try:
        content = open(local_path).read()
        rel_parts = remote_rel.rsplit('/', 1)
        subdir = rel_parts[0] if len(rel_parts) > 1 else ""
        filename, remote_dir = rel_parts[-1], f"{DOCROOT}/{subdir}" if subdir else DOCROOT
        headers = {"Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}"}
        if subdir:
            requests.get(f"https://{CPANEL_HOST}:2083/json-api/cpanel",
                         params={"cpanel_jsonapi_apiversion": "2", "cpanel_jsonapi_module": "Fileman",
                                 "cpanel_jsonapi_func": "mkdir", "path": DOCROOT,
                                 "name": subdir, "permissions": "0755"},
                         headers=headers, timeout=30, verify=False)
        r = requests.post(f"https://{CPANEL_HOST}:2083/execute/Fileman/save_file_content",
                          data={"dir": remote_dir, "file": filename, "content": content},
                          headers=headers, timeout=30, verify=False)
        if r.ok and r.json().get("status") == 1:
            print(f"[DEPLOY] Uploaded {filename} to {remote_dir}")
            return True
        print(f"[WARN] cPanel upload failed: {r.text[:100]}")
        return False
    except Exception as e:
        print(f"[WARN] cPanel deploy error: {e}")
        return False

def post_to_facebook(title: str, wp_url: str, articles: list = None) -> bool:
    """Post press review to Facebook Expats in Romania page with article summary."""
    if not FacebookNewsPublisher or not load_page_tokens:
        return False
    try:
        tokens = load_page_tokens(str(FB_PAGES_JSON))
        token = tokens.get(FB_PAGE_ID)
        if not token:
            print("[WARN] No FB token for Expats in Romania")
            return False

        title_short = title[:80] if len(title) > 80 else title

        message_parts = [title_short, ""]

        if articles:
            for _i, article in enumerate(articles[:3]):
                title = article.get("title", "")[:70]
                source = article.get("source", "")
                message_parts.append(f"• {title}")
                message_parts.append(f"  {source}")
            message_parts.append("")

        message_parts.extend([wp_url, "", "#Romania #News #Expats"])
        message = "\n".join(message_parts)

        publisher = FacebookNewsPublisher(FB_PAGE_ID, token)
        result = publisher.post(message, wp_url)
        if result:
            print(f"[INFO] FB post: {result.get('id', 'posted')}")
            return True
        return False
    except Exception as e:
        print(f"[WARN] FB posting failed: {e}")
        return False

def main():
    today = datetime.now(timezone.utc).date()

    conn = db_connect()
    ensure_tables(conn)

    if already_posted(conn, today):
        print(f"[INFO] Press review for {today} already exists. Exiting.")
        conn.close()
        return

    print(f"[INFO] Fetching articles for {today}…")
    articles = fetch_articles(hours_back=26)
    if not articles:
        print("[ERROR] No articles fetched.")
        conn.close()
        return
    print(f"[INFO] Fetched {len(articles)} articles.")

    translator = None
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="ro", target="en")
    except Exception:
        print("[WARN] GoogleTranslator unavailable; RO titles will not be translated.")

    print("[INFO] Summarizing…")
    for a in articles:
        a["summary"] = summarize(a["desc"], lang=a.get("lang", "en"), translator=translator)
        if a.get("lang") == "ro" and translator:
            try:
                a["title"] = translator.translate(a["title"][:100])
                time.sleep(0.5)  # avoid Google Translate rate limit (free tier)
            except Exception:
                pass

    title = f"Romania Press Review — {today.strftime('%B %-d, %Y')}"
    html_body = build_html(articles, today)

    print("[INFO] Posting to WordPress…")
    if not WP_PASS:
        print("[WARN] WP_EXPATSINROMANIA_ORG_PASS not set — skipping WP post.")
        wp_url = ""
        wp_id = None
    else:
        cat_id = wp_ensure_category("Press Review")
        result = wp_post(title, html_body, cat_id)
        wp_url = result.get("link", "")
        wp_id  = result.get("id")
        print(f"[INFO] WP post: {wp_url}")

    save_articles(conn, today, articles)
    save_post(conn, today, wp_id, wp_url)

    print("[INFO] Posting to Facebook…")
    if wp_id and wp_url:
        post_to_facebook(title, wp_url, articles)

    print("[INFO] Building RSS feed…")
    feed_items = [{
        "title":    "Romania Press Review — " + r.strftime("%B %-d, %Y"),
        "link":     u or f"{WP_URL}/press-review/{r}/",
        "pub_date": datetime(r.year, r.month, r.day, 8, 0, 0, tzinfo=timezone.utc),
        "summary":  (s or "")[:500],
    } for r, u, s in recent_reviews_for_feed(conn, limit=30)]
    build_rss_feed(feed_items, RSS_LOCAL)

    print("[INFO] Deploying RSS feed to A2…")
    deploy_to_cpanel(RSS_LOCAL, "press-review/feed.xml")

    conn.close()
    print("[DONE]")

if __name__ == "__main__":
    main()
