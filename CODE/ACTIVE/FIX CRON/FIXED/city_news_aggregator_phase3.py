#!/usr/bin/env python3
"""City news aggregator Phase 3: Multi-language (EN/FR/ES/NE/HI) with Romanian source translation."""

import base64
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests

sys.path.insert(0, os.path.dirname(__file__))
from city_news_rss import fetch_articles
from city_news_translate import translate_batch, LANGUAGES as TRANSLATION_LANGS
from mastodon_publisher import MastodonPublisher, format_mastodon_status
from facebook_news_publisher import FacebookNewsPublisher, format_facebook_news, NEWS_PAGE_TARGETS, load_page_tokens
try:
    from twitter_news_publisher import TwitterNewsPublisher, format_twitter_status
except ImportError:
    TwitterNewsPublisher = None; format_twitter_status = None
try:
    from linkedin_news_publisher import LinkedInNewsPublisher, format_linkedin_status
except ImportError:
    LinkedInNewsPublisher = None; format_linkedin_status = None
from telegram_news_publisher import TelegramNewsPublisher, format_telegram_status
from city_news_config import (
    CITIES, LANGUAGES, WP_URL, WP_USER, WP_PASS, DB_DSN,
    MASTODON_INSTANCE, MASTODON_TOKEN, MASTODON_POST_DELAY, FB_PAGES_JSON, FB_NEWS_ENABLED,
    TWITTER_ENABLED, TWITTER_ACCESS_TOKEN,
    LINKEDIN_ENABLED, LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID,
    TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID
)

TOPIC_ORDER = ["Economy", "Politics", "Society", "Culture"]


def db_connect():
    return psycopg2.connect(DB_DSN)


def ensure_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS city_news_reviews (
                id          SERIAL PRIMARY KEY,
                review_date DATE NOT NULL,
                city        VARCHAR(50) NOT NULL,
                language    VARCHAR(10) NOT NULL,
                article_count INT,
                wp_post_id  INTEGER,
                wp_url      TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(review_date, city, language)
            );
            CREATE TABLE IF NOT EXISTS city_news_articles (
                id          SERIAL PRIMARY KEY,
                article_id  VARCHAR(64) UNIQUE NOT NULL,
                review_date DATE NOT NULL,
                city        VARCHAR(50) NOT NULL,
                source_lang VARCHAR(10),
                language    VARCHAR(10) NOT NULL,
                source_name TEXT,
                title       TEXT,
                summary     TEXT,
                link        TEXT,
                topic       TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS city_news_sources (
                id          SERIAL PRIMARY KEY,
                city        VARCHAR(50),
                source_name TEXT,
                rss_url     TEXT,
                language    VARCHAR(10),
                is_active   BOOLEAN DEFAULT TRUE,
                added_date  TIMESTAMPTZ DEFAULT NOW()
            );
        """)
    conn.commit()


def already_posted(conn, review_date, city, language) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM city_news_reviews WHERE review_date=%s AND city=%s AND language=%s",
            (review_date, city, language))
        return cur.fetchone() is not None


def save_post(conn, review_date, city, language, wp_post_id, wp_url):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO city_news_reviews (review_date, city, language, wp_post_id, wp_url)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (review_date, city, language) DO UPDATE SET wp_post_id=%s, wp_url=%s""",
            (review_date, city, language, wp_post_id, wp_url, wp_post_id, wp_url))
    conn.commit()


def save_articles(conn, review_date, city, articles_with_translations):
    """Save articles with translations to database (one row per language per article)."""
    with conn.cursor() as cur:
        for a in articles_with_translations:
            source_lang = a.get("lang", "en")
            translations = a.get("translations", {})

            if not translations:
                # Fallback: single language entry
                cur.execute(
                    """INSERT INTO city_news_articles
                       (article_id, review_date, city, source_lang, language, source_name, title, summary, link, topic)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (article_id) DO NOTHING""",
                    (a["id"], review_date, city, source_lang, source_lang, a["source"],
                     a["title"], a.get("summary", a.get("desc", "")[:200]), a["link"], a["topic"]))
            else:
                # Save one row per language
                for lang, translation in translations.items():
                    cur.execute(
                        """INSERT INTO city_news_articles
                           (article_id, review_date, city, source_lang, language, source_name, title, summary, link, topic)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (article_id) DO NOTHING""",
                        (a["id"] + f"_{lang}", review_date, city, source_lang, lang, a["source"],
                         translation.get("title", a["title"]),
                         translation.get("summary", a.get("summary", "")),
                         a["link"], a["topic"]))
    conn.commit()


def _wp_auth() -> str:
    return base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()


def wp_ensure_category(name: str = "Local News") -> int:
    """Return WP category ID, creating if missing."""
    headers = {"Authorization": f"Basic {_wp_auth()}"}
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/categories", params={"search": name}, headers=headers, timeout=15)
    cats = r.json() if r.ok else []
    if cats:
        return cats[0]["id"]
    r2 = requests.post(f"{WP_URL}/wp-json/wp/v2/categories",
                       json={"name": name, "slug": "local-news"}, headers=headers, timeout=15)
    return r2.json().get("id", 1)


def wp_post(title: str, html_body: str, category_id: int) -> dict:
    headers = {"Authorization": f"Basic {_wp_auth()}", "Content-Type": "application/json"}
    payload = {
        "title": title,
        "content": html_body,
        "status": "publish",
        "categories": [category_id],
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/posts", json=payload, headers=headers, timeout=30)
    if not r.ok:
        print(f"[ERROR] WP post failed: {r.status_code} {r.text[:200]}")
        return {}
    return r.json()


def build_html(articles, city, language, review_date) -> str:
    by_topic = defaultdict(list)
    for a in articles:
        by_topic[a["topic"]].append(a)

    city_name = CITIES.get(city, {}).get("name", city.title())
    lang_name = TRANSLATION_LANGS.get(language, language.upper())

    parts = [
        f'<p><em>Daily local news from {city_name} — {lang_name} edition — for expat communities.</em></p>',
        '<hr/>',
    ]
    for topic in TOPIC_ORDER:
        items = by_topic.get(topic, [])
        if not items:
            continue
        parts.append(f"<h2>{topic}</h2>")
        for a in items:
            summary = a.get("summary", "")
            parts.append(
                f'<h3><a href="{a["link"]}" target="_blank" rel="noopener">{a["title"]}</a></h3>'
                f'<p>{summary} — <em>{a["source"]}</em></p>'
            )
    parts.append(f'<hr/><p><small>{city_name} news auto-generated by ExpatsInRomania.org bot. '
                 f'Available in: English, Français, Español, Nepali, हिन्दी</small></p>')
    return "\n".join(parts)


def main():
    today = datetime.now(timezone.utc).date()
    conn = db_connect()
    ensure_tables(conn)

    # Conservative: 2 posts/day max (EN only, top cities)
    cat_id = wp_ensure_category("Local News") if WP_PASS else None
    total_posts = 0
    mastodon = MastodonPublisher(MASTODON_INSTANCE, MASTODON_TOKEN, MASTODON_POST_DELAY) if MASTODON_TOKEN else None

    # Load Facebook page tokens
    fb_tokens = load_page_tokens(FB_PAGES_JSON) if FB_NEWS_ENABLED else {}

    # Initialize other social media publishers
    twitter = TwitterNewsPublisher(TWITTER_ACCESS_TOKEN) if TWITTER_ENABLED and TWITTER_ACCESS_TOKEN else None
    linkedin = LinkedInNewsPublisher(LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID) if LINKEDIN_ENABLED and LINKEDIN_ACCESS_TOKEN else None
    telegram = TelegramNewsPublisher(TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID) if TELEGRAM_ENABLED and TELEGRAM_BOT_TOKEN else None

    # Fetch all cities, pick top 2 by article count (cache to avoid refetch)
    city_articles = {}
    for city in CITIES.keys():
        articles = fetch_articles(city, hours_back=26)
        if articles:
            city_articles[city] = articles

    top_cities = sorted(city_articles, key=lambda c: len(city_articles[c]), reverse=True)[:2]
    print(f"[INFO] Limiting to top 2 cities: {[CITIES[c]['name'] for c in top_cities]}")

    for city in top_cities:
        print(f"\n[INFO] Processing {city.title()}…")

        # Use cached articles (no second fetch)
        articles = city_articles[city]
        if not articles:
            print(f"[WARN] No articles fetched for {city}.")
            continue

        print(f"[INFO] Fetched {len(articles)} articles from {city.title()}.")

        # Conservative: Use only EN articles (no translation needed)
        en_articles = [a for a in articles if a["lang"] == "en"]

        if not en_articles:
            print(f"[WARN] No English articles for {city.title()}, skipping.")
            continue

        all_articles_translated = []
        for a in en_articles:
            a["translations"] = {"en": {"title": a["title"], "summary": a["desc"][:200]}}
            a["summary"] = a["desc"][:200]
            all_articles_translated.append(a)

        # Conservative: English only (2 posts/day max)
        for language in ["en"]:
            if already_posted(conn, today, city, language):
                print(f"[SKIP] {city.title()} {language.upper()} already posted.")
                continue

            # Get translated articles for this language
            lang_articles = []
            for a in all_articles_translated:
                translation = a.get("translations", {}).get(language)
                if translation:
                    lang_articles.append({
                        "id": a["id"],
                        "source": a["source"],
                        "lang": a["lang"],
                        "title": translation["title"],
                        "summary": translation["summary"],
                        "link": a["link"],
                        "topic": a["topic"],
                        "desc": translation["summary"]
                    })

            if not lang_articles:
                continue

            # Build HTML for WordPress
            city_name = CITIES.get(city, {}).get("name", city.title())
            title = f"{city_name} Local News — {language.upper()} — {today.strftime('%B %-d, %Y')}"
            html_body = build_html(lang_articles, city, language, today)

            # Post to WordPress
            wp_url = ""
            wp_id = None
            if WP_PASS:
                result = wp_post(title, html_body, cat_id)
                wp_url = result.get("link", "")
                wp_id = result.get("id")
                print(f"[WP] {city.title()} {language.upper()}: {wp_url}")

            # Extract top article once for all social posts
            top_article = lang_articles[0]

            # Post to Mastodon
            if mastodon:
                try:
                    status = format_mastodon_status(city, top_article["title"],
                                                    top_article["link"],
                                                    top_article["source"], city_name)
                    result = mastodon.post(status, visibility="public")
                    if result:
                        print(f"[MASTODON] {city.title()}: {result['url']}")
                except Exception as e:
                    print(f"[WARN] Mastodon post failed: {e}")

            # Post to Facebook
            if FB_NEWS_ENABLED and fb_tokens:
                try:
                    for page_id, page_config in NEWS_PAGE_TARGETS.items():
                        if language not in page_config.get("languages", []):
                            continue
                        if page_id not in fb_tokens:
                            continue

                        fb_pub = FacebookNewsPublisher(page_id, fb_tokens[page_id])
                        message = format_facebook_news(city, top_article["title"],
                                                      top_article["link"],
                                                      top_article["source"],
                                                      language, city_name)
                        result = fb_pub.post(message, link=top_article["link"])
                        if result:
                            print(f"[FB] {city.title()}: {page_config['name']}")
                except Exception as e:
                    print(f"[WARN] FB post failed: {e}")

            # Post to Twitter/X
            if twitter:
                try:
                    tweet = format_twitter_status(city, top_article["title"],
                                                 top_article["link"], WP_URL)
                    result = twitter.post(tweet)
                    if result:
                        print(f"[TWITTER] {city.title()}: posted")
                except Exception as e:
                    print(f"[WARN] Twitter post failed: {e}")

            # Post to LinkedIn
            if linkedin:
                try:
                    text = format_linkedin_status(city, top_article["title"],
                                                 top_article["link"],
                                                 top_article["summary"], WP_URL)
                    result = linkedin.post(text, top_article["link"])
                    if result:
                        print(f"[LINKEDIN] {city.title()}: posted")
                except Exception as e:
                    print(f"[WARN] LinkedIn post failed: {e}")

            # Post to Telegram
            if telegram:
                try:
                    message = format_telegram_status(city, top_article["title"],
                                                    top_article["link"],
                                                    top_article["summary"], WP_URL)
                    result = telegram.post(message, top_article["link"])
                    if result:
                        print(f"[TELEGRAM] {city.title()}: posted")
                except Exception as e:
                    print(f"[WARN] Telegram post failed: {e}")

            # Save to DB
            save_articles(conn, today, city, all_articles_translated)
            save_post(conn, today, city, language, wp_id, wp_url)
            total_posts += 1

    conn.close()
    print(f"\n[SUMMARY] Published {total_posts} posts (2 cities × 1 language = 2 max)")
    print("[DONE]")


if __name__ == "__main__":
    main()
