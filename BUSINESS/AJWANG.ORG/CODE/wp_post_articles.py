"""Upload 6 launch country articles to ajwang.org WordPress as draft posts."""
import json
import ssl
import urllib.request
import urllib.parse
from pathlib import Path

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

CPANEL_HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
DOMAIN = "ajwang.org"

ARTICLES_DIR = Path(__file__).parent.parent / "DATA" / "articles"

ARTICLE_META = {
    "ng_nigeria.html":       {"title": "Doing Business in Nigeria: Complete Guide for International Investors",  "slug": "doing-business-in-nigeria"},
    "ke_kenya.html":         {"title": "Doing Business in Kenya: Complete Guide for International Investors",   "slug": "doing-business-in-kenya"},
    "et_ethiopia.html":      {"title": "Doing Business in Ethiopia: Complete Guide for International Investors","slug": "doing-business-in-ethiopia"},
    "ma_morocco.html":       {"title": "Doing Business in Morocco: Complete Guide for International Investors", "slug": "doing-business-in-morocco"},
    "za_south_africa.html":  {"title": "Doing Business in South Africa: Complete Guide for International Investors","slug": "doing-business-in-south-africa"},
    "gh_ghana.html":         {"title": "Doing Business in Ghana: Complete Guide for International Investors",   "slug": "doing-business-in-ghana"},
}


def cpanel_upload_php(php_code: str) -> bool:
    boundary = "----FormBound7749"
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"dir\"\r\n\r\n/home/{USER}/{DOMAIN}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\n1\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file-1\"; filename=\"_fix.php\"\r\nContent-Type: text/plain\r\n\r\n".encode(),
        php_code.encode("utf-8"),
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        f"{CPANEL_HOST}/execute/Fileman/upload_files",
        data=body,
        method="POST",
        headers={
            "Authorization": f"cpanel {USER}:{TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    r = json.loads(urllib.request.urlopen(req, timeout=30, context=CTX).read())
    return bool(r.get("data", {}).get("succeeded", 0))


def run_php(php_code: str) -> str:
    if not cpanel_upload_php(php_code):
        return "UPLOAD FAILED"
    req = urllib.request.Request(
        f"https://{DOMAIN}/_fix.php",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    try:
        return urllib.request.urlopen(req, timeout=30, context=CTX).read().decode()
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.read().decode()[:500]}"
    except Exception as e:
        return f"ERR: {e}"


def build_php(articles: list[dict]) -> str:
    # Encode each article as PHP array entry
    entries = []
    for a in articles:
        content_escaped = a["content"].replace("\\", "\\\\").replace("'", "\\'")
        title_escaped = a["title"].replace("'", "\\'")
        slug_escaped = a["slug"].replace("'", "\\'")
        entries.append(
            f"  ['title'=>'{title_escaped}','slug'=>'{slug_escaped}','content'=>'{content_escaped}']"
        )
    entries_php = ",\n".join(entries)

    return f"""<?php
chdir('/home/{USER}/{DOMAIN}');
$_SERVER['HTTP_HOST'] = '{DOMAIN}';
$_SERVER['REQUEST_URI'] = '/';
$_SERVER['REQUEST_METHOD'] = 'GET';
$_SERVER['SERVER_NAME'] = '{DOMAIN}';
require_once('wp-load.php');

$articles = [
{entries_php}
];

foreach ($articles as $a) {{
    // Check if slug exists
    $existing = get_page_by_path($a['slug'], OBJECT, 'post');
    if ($existing) {{
        $post_id = wp_update_post([
            'ID'           => $existing->ID,
            'post_title'   => $a['title'],
            'post_content' => $a['content'],
            'post_status'  => 'draft',
            'post_name'    => $a['slug'],
        ]);
        echo "Updated: " . $a['title'] . " (ID=$post_id)\\n";
    }} else {{
        $post_id = wp_insert_post([
            'post_title'   => $a['title'],
            'post_content' => $a['content'],
            'post_status'  => 'draft',
            'post_type'    => 'post',
            'post_name'    => $a['slug'],
        ]);
        echo "Created: " . $a['title'] . " (ID=$post_id)\\n";
    }}
}}

echo "DONE\\n";
@unlink(__FILE__);
"""


def main() -> None:
    articles = []
    for filename, meta in ARTICLE_META.items():
        path = ARTICLES_DIR / filename
        if not path.exists():
            print(f"MISSING: {filename}")
            continue
        content = path.read_text(encoding="utf-8")
        articles.append({
            "title": meta["title"],
            "slug": meta["slug"],
            "content": content,
        })
        print(f"Loaded: {filename} ({len(content)} chars)")

    print(f"\nBuilding PHP for {len(articles)} articles...")
    php = build_php(articles)
    print(f"PHP size: {len(php)} bytes")

    print("Uploading and running on ajwang.org...")
    result = run_php(php)
    print("\n=== Result ===")
    print(result)


if __name__ == "__main__":
    main()
