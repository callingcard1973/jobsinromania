"""Upload all 48 country articles to ajwang.org WordPress via cPanel PHP runner."""
import json
import re
import time
from pathlib import Path

import requests

CPANEL_HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
DOMAIN = "ajwang.org"
DOCROOT = f"/home/{CPANEL_USER}/{DOMAIN}"

DATA_DIR = Path(__file__).parent.parent / "DATA"
ARTICLES_DIR = DATA_DIR / "articles"
COUNTRIES_JSON = DATA_DIR / "countries.json"

DONE = {"NG", "KE", "ET", "MA", "ZA", "GH"}
BATCH_SIZE = 10


def cpanel_php_run(php_code: str) -> str:
    """Upload a PHP file to cPanel and execute it."""
    filename = f"_batch_{int(time.time())}.php"
    url_path = f"https://{DOMAIN}/{filename}"

    # Write file via cPanel API2 (savefile)
    write_url = f"{CPANEL_HOST}/json-api/cpanel"
    headers = {
        "Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}",
    }
    resp = requests.post(
        write_url,
        headers=headers,
        data={
            "cpanel_jsonapi_user": CPANEL_USER,
            "cpanel_jsonapi_apiversion": "2",
            "cpanel_jsonapi_module": "Fileman",
            "cpanel_jsonapi_func": "savefile",
            "dir": DOCROOT,
            "filename": filename,
            "content": php_code,
        },
        timeout=30,
        verify=False,
    )
    resp.raise_for_status()
    result = resp.json()
    event = result.get("cpanelresult", {}).get("event", {})
    if not event.get("result"):
        raise RuntimeError(f"File write failed: {result}")

    # Execute by fetching URL
    time.sleep(1)
    exec_resp = requests.get(url_path, timeout=120, verify=False)
    return exec_resp.text


def make_php_batch(articles: list[dict]) -> str:
    """Generate PHP batch script for a list of articles."""
    # Build PHP array entries
    entries = []
    for a in articles:
        title = a["title"].replace("'", "\\'")
        slug = a["slug"]
        content = a["content"].replace("\\", "\\\\").replace("'", "\\'")
        region = a["region"].replace("'", "\\'")
        country_name = a["country_name"].replace("'", "\\'")
        metadesc = f"Complete guide to doing business in {country_name}. GDP data, investment climate, company registration, banking, and mobility guide.".replace("'", "\\'")
        focuskw = f"doing business in {country_name}".replace("'", "\\'")
        tags = ["Africa business", "investment", "doing business in Africa", f"{country_name} business", region]
        tags_php = ", ".join(f"'{t}'" for t in tags)

        entries.append(
            f"""  ['title'=>'{title}','slug'=>'{slug}','content'=>'{content}','focuskw'=>'{focuskw}','metadesc'=>'{metadesc}','tags'=>[{tags_php}]]"""
        )

    arr = ",\n".join(entries)

    return f"""<?php
chdir('{DOCROOT}');
$_SERVER['HTTP_HOST'] = '{DOMAIN}';
$_SERVER['REQUEST_URI'] = '/';
$_SERVER['REQUEST_METHOD'] = 'GET';
$_SERVER['SERVER_NAME'] = '{DOMAIN}';
require_once('wp-load.php');

$articles = [
{arr}
];

foreach ($articles as $a) {{
    $existing = get_page_by_path($a['slug'], OBJECT, 'post');
    if ($existing) {{
        wp_update_post(['ID'=>$existing->ID,'post_title'=>$a['title'],'post_content'=>$a['content'],'post_status'=>'publish','post_name'=>$a['slug']]);
        $id = $existing->ID;
        echo "Updated ID=$id: " . $a['title'] . "\\n";
    }} else {{
        $id = wp_insert_post(['post_title'=>$a['title'],'post_content'=>$a['content'],'post_status'=>'publish','post_type'=>'post','post_name'=>$a['slug']]);
        echo "Created ID=$id: " . $a['title'] . "\\n";
    }}
    if ($id && !is_wp_error($id)) {{
        update_post_meta($id, '_yoast_wpseo_focuskw', $a['focuskw']);
        update_post_meta($id, '_yoast_wpseo_metadesc', $a['metadesc']);
        wp_set_post_tags($id, $a['tags'], true);
    }}
}}
echo "BATCH DONE\\n";
@unlink(__FILE__);
"""


def make_slug(name: str) -> str:
    s = name.lower()
    s = re.sub(r"['’]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return f"doing-business-in-{s.strip('-')}"


def main() -> None:
    import urllib3
    urllib3.disable_warnings()

    data = json.loads(COUNTRIES_JSON.read_text(encoding="utf-8"))
    countries = {c["iso2"]: c for c in data if c["iso2"] not in DONE}

    articles = []
    for iso2, c in countries.items():
        name = c["name"]
        slug_file = name.lower().replace(" ", "_").replace("'", "").replace(",", "")
        html_file = ARTICLES_DIR / f"{iso2.lower()}_{slug_file}.html"
        if not html_file.exists():
            print(f"WARNING: No file for {name}: {html_file}")
            continue
        content = html_file.read_text(encoding="utf-8")
        articles.append({
            "iso2": iso2,
            "country_name": name,
            "region": c.get("region", "Africa"),
            "title": f"Doing Business in {name}: Complete Guide for International Investors",
            "slug": make_slug(name),
            "content": content,
        })

    print(f"Total articles to upload: {len(articles)}")

    # Process in batches
    batches = [articles[i:i + BATCH_SIZE] for i in range(0, len(articles), BATCH_SIZE)]
    total_ok = 0

    for i, batch in enumerate(batches, 1):
        print(f"\n--- Batch {i}/{len(batches)} ({len(batch)} articles) ---")
        php = make_php_batch(batch)
        try:
            output = cpanel_php_run(php)
            print(output)
            ok = output.count("BATCH DONE")
            created = output.count("Created ID=")
            updated = output.count("Updated ID=")
            total_ok += created + updated
            print(f"  Created: {created}, Updated: {updated}")
        except Exception as e:
            print(f"ERROR in batch {i}: {e}")

    print(f"\nAll done. Total posts created/updated: {total_ok}")


if __name__ == "__main__":
    main()
