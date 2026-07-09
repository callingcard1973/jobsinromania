#!/usr/bin/env python3
"""Publisher Agent — posts articles to WordPress REST API + Yoast metadata."""

import base64
import json
import sys
import time
from datetime import datetime

import requests
import psycopg2

def get_auth_header(user, password):
    """Generate Basic auth header."""
    creds = f"{user}:{password}"
    encoded = base64.b64encode(creds.encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }

def get_or_create_category(wp_url, headers, name):
    """Get or create WordPress category."""
    try:
        r = requests.get(
            f"{wp_url}/wp-json/wp/v2/categories?search={name}",
            headers=headers,
            timeout=10
        )
        if r.ok and r.json():
            return r.json()[0]["id"]

        r = requests.post(
            f"{wp_url}/wp-json/wp/v2/categories",
            headers=headers,
            json={"name": name, "slug": name.lower().replace(" ", "-")},
            timeout=10
        )
        if r.ok:
            return r.json().get("id")
    except Exception as e:
        print(f"[WARN] Category creation failed: {e}", file=sys.stderr)

    return None

def publish_post(wp_url, headers, article, cat_id, max_retries=3):
    """Publish a single post to WordPress with retry logic."""
    payload = {
        "title": article["title"],
        "slug": article["slug"],
        "content": article["content_html"],
        "status": "publish",
        "categories": [cat_id] if cat_id else []
    }

    for attempt in range(max_retries):
        try:
            r = requests.post(
                f"{wp_url}/wp-json/wp/v2/posts",
                headers=headers,
                json=payload,
                timeout=30
            )
            if r.status_code in [200, 201]:
                post_id = r.json().get("id")

                # Patch Yoast metadata
                try:
                    requests.post(
                        f"{wp_url}/wp-json/wp/v2/posts/{post_id}",
                        headers=headers,
                        json={
                            "meta": {
                                "_yoast_wpseo_focuskw": article["focus_keyword"],
                                "_yoast_wpseo_metadesc": article["meta_description"]
                            }
                        },
                        timeout=15
                    )
                except Exception as e:
                    print(f"[WARN] Yoast metadata patch failed: {e}", file=sys.stderr)

                return post_id
            elif r.status_code in [500, 502, 503]:
                wait = 2 ** attempt
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    continue
                return None
            else:
                print(f"[WARN] WP error {r.status_code}: {r.text[:150]}", file=sys.stderr)
                return None
        except requests.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None

    return None

def record_publish(db_config, lang, post_id):
    """Record publish in wp_roundup_log."""
    try:
        conn = psycopg2.connect(
            host=db_config["db_host"],
            port=db_config.get("db_port", 5432),
            dbname=db_config["db_name"],
            user=db_config["db_user"],
            password=db_config["db_pass"]
        )
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO wp_roundup_log (roundup_date, lang, wp_post_id)
            VALUES (CURRENT_DATE, %s, %s)
            ON CONFLICT DO NOTHING
        """, (lang, post_id))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[WARN] DB logging failed: {e}", file=sys.stderr)

def main():
    config = json.loads(sys.stdin.read())

    wp_url = config["wp_url"]
    wp_user = config["wp_user"]
    wp_pass = config["wp_pass"]
    articles = config.get("articles", {})

    headers = get_auth_header(wp_user, wp_pass)

    results = {}

    # Publish RO article
    if articles.get("ro"):
        cat_ro = get_or_create_category(wp_url, headers, "Piata Muncii")
        post_id = publish_post(wp_url, headers, articles["ro"], cat_ro)
        if post_id:
            record_publish(config, "ro", post_id)
            results["ro"] = {
                "post_id": post_id,
                "slug": articles["ro"]["slug"],
                "url": f"{wp_url}/{articles['ro']['slug']}/",
                "category_id": cat_ro,
                "yoast_meta_set": True,
                "published_at": datetime.now().isoformat()
            }
        else:
            results["ro"] = {"post_id": None, "error": "Failed to publish RO article"}

    # Publish EN article
    if articles.get("en"):
        cat_en = get_or_create_category(wp_url, headers, "Job Market")
        post_id = publish_post(wp_url, headers, articles["en"], cat_en)
        if post_id:
            record_publish(config, "en", post_id)
            results["en"] = {
                "post_id": post_id,
                "slug": articles["en"]["slug"],
                "url": f"{wp_url}/{articles['en']['slug']}/",
                "category_id": cat_en,
                "yoast_meta_set": True,
                "published_at": datetime.now().isoformat()
            }
        else:
            results["en"] = {"post_id": None, "error": "Failed to publish EN article"}

    # Determine overall status
    ro_ok = results.get("ro", {}).get("post_id") is not None
    en_ok = results.get("en", {}).get("post_id") is not None

    output = {
        "status": "published" if (ro_ok and en_ok) else ("partial" if (ro_ok or en_ok) else "failed"),
        "results": results,
        "db_log_recorded": ro_ok or en_ok
    }

    print(json.dumps(output))

if __name__ == "__main__":
    main()
