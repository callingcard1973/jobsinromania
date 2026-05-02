#!/usr/bin/env python3
"""
Romanian Layoff/Closure News Monitor

Monitors Romanian news RSS feeds for layoff, closure, and insolvency keywords.
Sends Telegram alerts when relevant articles are found.

Usage:
    python rss_monitor.py --check          # Check feeds once
    python rss_monitor.py --watch          # Continuous monitoring (hourly)
    python rss_monitor.py --test-telegram  # Test Telegram notification
"""

import argparse
import feedparser
import hashlib
import json
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Import shared alerting
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(message: str, chat_id: str = None) -> bool:
        print(f"[TELEGRAM] {message}")
        return True

BASE_DIR = Path(__file__).parent
DB_FILE = BASE_DIR / "layoff_alerts.db"

# Romanian news RSS feeds (business/economic focus)
RSS_FEEDS = {
    'economica': 'https://www.economica.net/feed/',
    'wall-street': 'https://www.wall-street.ro/rss/articole.xml',
    'profit': 'https://www.profit.ro/rss',
    'hotnews': 'https://www.hotnews.ro/rss/economie',
    'capital': 'https://www.capital.ro/feed/',
    'ziarul-financiar': 'https://www.zf.ro/rss/',
    'agerpres': 'https://www.agerpres.ro/rss/economie',
    'bursa': 'https://www.bursa.ro/rss',
    'mediafax-economic': 'https://www.mediafax.ro/rss/economic.xml',
}

# Layoff/closure keywords (Romanian)
KEYWORDS = [
    # Layoffs
    'disponibilizari', 'disponibilizare', 'concedieri', 'concediere',
    'restructurare', 'restructurari', 'reduce personal', 'reducere personal',
    'somaj tehnic', 'suspendare activitate',
    # Closures
    'insolventa', 'faliment', 'falimenteaza', 'inchide fabrica', 'inchide uzina',
    'opreste productia', 'oprire productie', 'radiata', 'dizolvata', 'dizolvare',
    'lichidare', 'lichideaza',
    # Companies leaving
    'pleaca din romania', 'paraseste romania', 'muta productia',
    'relocare', 'inchidere fabrica',
]

# Sector keywords (to identify industry)
SECTORS = {
    'automotive': ['auto', 'masini', 'componente auto', 'piese auto', 'ford', 'dacia', 'renault'],
    'it': ['it', 'software', 'tech', 'outsourcing', 'programatori'],
    'manufacturing': ['fabrica', 'uzina', 'productie', 'industrie'],
    'retail': ['retail', 'magazine', 'supermarket', 'hypermarket'],
    'construction': ['constructii', 'santier', 'imobiliare'],
    'agriculture': ['agricultura', 'ferma', 'ferme'],
}


def init_db():
    """Initialize SQLite database for tracking seen articles."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            source TEXT,
            keywords TEXT,
            sector TEXT,
            published TEXT,
            found_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id TEXT,
            sent_at TEXT,
            FOREIGN KEY (article_id) REFERENCES articles(id)
        )
    ''')
    conn.commit()
    return conn


def article_hash(link: str) -> str:
    """Generate unique ID for article."""
    return hashlib.md5(link.encode()).hexdigest()[:16]


def check_keywords(text: str) -> List[str]:
    """Check text for layoff keywords. Returns matched keywords."""
    text_lower = text.lower()
    found = []
    for kw in KEYWORDS:
        if kw in text_lower:
            found.append(kw)
    return found


def detect_sector(text: str) -> Optional[str]:
    """Detect industry sector from text."""
    text_lower = text.lower()
    for sector, keywords in SECTORS.items():
        for kw in keywords:
            if kw in text_lower:
                return sector
    return None


def fetch_feed(url: str, source: str) -> List[Dict]:
    """Fetch and parse RSS feed."""
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:  # Last 20 entries
            title = entry.get('title', '')
            summary = entry.get('summary', entry.get('description', ''))
            link = entry.get('link', '')
            published = entry.get('published', entry.get('updated', ''))

            # Check for keywords in title + summary
            text = f"{title} {summary}"
            keywords = check_keywords(text)

            if keywords:
                articles.append({
                    'id': article_hash(link),
                    'title': title[:200],
                    'link': link,
                    'source': source,
                    'keywords': ','.join(keywords),
                    'sector': detect_sector(text),
                    'published': published,
                })
    except Exception as e:
        print(f"Error fetching {source}: {e}")

    return articles


def check_all_feeds(conn: sqlite3.Connection) -> List[Dict]:
    """Check all RSS feeds and return new articles."""
    new_articles = []

    for source, url in RSS_FEEDS.items():
        print(f"Checking {source}...", end=' ')
        articles = fetch_feed(url, source)
        print(f"{len(articles)} matches")

        for article in articles:
            # Check if already seen
            cursor = conn.execute(
                "SELECT id FROM articles WHERE id = ?",
                (article['id'],)
            )
            if cursor.fetchone():
                continue

            # New article - save it
            conn.execute('''
                INSERT INTO articles (id, title, link, source, keywords, sector, published, found_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article['id'], article['title'], article['link'],
                article['source'], article['keywords'], article['sector'],
                article['published'], datetime.now().isoformat()
            ))
            new_articles.append(article)

    conn.commit()
    return new_articles


def send_alert(article: Dict) -> bool:
    """Send Telegram alert for new layoff article."""
    sector_emoji = {
        'automotive': '🚗',
        'it': '💻',
        'manufacturing': '🏭',
        'retail': '🛒',
        'construction': '🏗️',
        'agriculture': '🌾',
    }

    emoji = sector_emoji.get(article.get('sector'), '📰')

    message = f"""{emoji} *LAYOFF ALERT*

*{article['title']}*

Source: {article['source']}
Keywords: {article['keywords']}
Sector: {article.get('sector', 'Unknown')}

{article['link']}
"""

    return send_telegram(message)


def main():
    parser = argparse.ArgumentParser(description='Romanian Layoff News Monitor')
    parser.add_argument('--check', action='store_true', help='Check feeds once')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring')
    parser.add_argument('--interval', type=int, default=3600, help='Check interval in seconds (default: 3600)')
    parser.add_argument('--test-telegram', action='store_true', help='Test Telegram notification')
    parser.add_argument('--list-recent', type=int, help='List N most recent articles')
    args = parser.parse_args()

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    conn = init_db()

    if args.test_telegram:
        success = send_telegram("🧪 *Test*: Layoff Monitor is working!")
        print(f"Telegram test: {'OK' if success else 'FAILED'}")
        return

    if args.list_recent:
        cursor = conn.execute(
            "SELECT title, source, keywords, found_at FROM articles ORDER BY found_at DESC LIMIT ?",
            (args.list_recent,)
        )
        for row in cursor:
            print(f"{row[3][:16]} | {row[1]:15} | {row[0][:50]}...")
        return

    if args.check or args.watch:
        print("=" * 60)
        print("Romanian Layoff News Monitor")
        print(f"Checking {len(RSS_FEEDS)} feeds for {len(KEYWORDS)} keywords")
        print("=" * 60)

        while True:
            new_articles = check_all_feeds(conn)

            if new_articles:
                print(f"\n🚨 Found {len(new_articles)} new articles!")
                for article in new_articles:
                    print(f"  - [{article['source']}] {article['title'][:60]}...")
                    send_alert(article)
            else:
                print("No new layoff news found.")

            if not args.watch:
                break

            print(f"\nNext check in {args.interval // 60} minutes...")
            time.sleep(args.interval)

    else:
        parser.print_help()

    conn.close()


if __name__ == '__main__':
    main()
