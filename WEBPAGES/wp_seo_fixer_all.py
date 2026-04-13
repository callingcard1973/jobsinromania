#!/usr/bin/env python3
"""WordPress SEO Fixer - Process all 8 sites, one per night"""
import os, json, base64, requests, logging, re, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from db_client import get_conn, safe_insert
except ImportError:
    def get_conn(*args, **kwargs): return None
    def safe_insert(*args, **kwargs): return False

SITES = [
    ('cumparlegume.com', 'WP_CUMPARLEGUME'),
    ('seicarescu.com', 'WP_SEICARESCU'),
    ('agroevolution.com', 'WP_AGROEVOLUTION'),
    ('ajwang.org', 'WP_AJWANG'),
    ('baneasa39.com', 'WP_BANEASA39'),
    ('cifn.info', 'WP_CIFN'),
    ('haritina.com', 'WP_HARITINA'),
    ('mivromania.com', 'WP_MIVROMANIA'),
]

def load_env():
    """Load WordPress credentials from .env file"""
    env_path = Path(__file__).parent / 'wp_sites.env'
    if not env_path.exists():
        env_path = Path('D:/MEMORY/WEBPAGES/wp_sites.env')
    env = {}
    if env_path.exists():
        for line in open(env_path):
            line = line.strip()
            if line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k] = v
    return env

def setup_logging(domain):
    """Setup logging for this run"""
    log_file = f"wp_seo_fix_{domain}_{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

def qwen_generate(prompt):
    """Call Qwen 2.5 on raspibig (:11434)"""
    try:
        resp = requests.post(
            'http://192.168.100.20:11434/api/generate',
            json={'model': 'qwen2.5', 'prompt': prompt, 'stream': False},
            timeout=30
        )
        return resp.json().get('response', '').strip() if resp.status_code == 200 else None
    except:
        return None

def wp_request(domain, user, password, endpoint, method='GET', data=None):
    """Generic WordPress REST API request"""
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}
    url = f"https://{domain}/wp-json/wp/v2/{endpoint}"
    try:
        if method == 'GET':
            return requests.get(url, headers=headers, timeout=10, verify=False).json()
        else:
            return requests.post(url, headers=headers, json=data, timeout=10, verify=False).status_code in [200, 201]
    except:
        return [] if method == 'GET' else False

def get_paginated(domain, user, password, endpoint, logger):
    """Fetch paginated posts/media"""
    items = []
    for page in range(1, 11):
        try:
            resp = requests.get(
                f"https://{domain}/wp-json/wp/v2/{endpoint}?per_page=100&page={page}",
                headers={'Authorization': f'Basic {base64.b64encode(f"{user}:{password}".encode()).decode()}'},
                timeout=10, verify=False
            )
            if resp.status_code == 400:
                break
            data = resp.json()
            if not data:
                break
            items.extend(data)
        except:
            break
    return items

def fix_seo(domain, user, password, logger):
    """Main SEO fixing routine"""
    requests.packages.urllib3.disable_warnings()

    posts = get_paginated(domain, user, password, 'posts', logger)
    logger.info(f"Fetched {len(posts)} posts")

    # Fix missing titles
    for post in posts:
        if not post.get('title', {}).get('rendered', '').strip():
            prompt = f"Generate SEO title (max 60 chars): {post.get('content', {}).get('rendered', '')[:200]}"
            title = qwen_generate(prompt)
            if title:
                old_title = post.get('title', {}).get('rendered', '')
                if wp_request(domain, user, password, f"posts/{post['id']}", 'POST', {'title': title}):
                    conn = get_conn()
                    if conn:
                        sql = "INSERT INTO wp_seo_fixes (domain, post_id, fix_type, old_value, new_value, applied, fix_date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                        safe_insert(conn, sql, (domain, post['id'], 'missing_title', old_title, title, True, datetime.now().date()))
                        conn.close()
                    logger.info(f"[DB] SEO fix logged: post {post['id']} title")

    # Fix missing meta descriptions (excerpt)
    for post in posts:
        if not post.get('excerpt', {}).get('rendered', '').strip():
            content = post.get('content', {}).get('rendered', '')[:300]
            prompt = f"Write 160-char meta description: {content}"
            desc = qwen_generate(prompt)
            if desc:
                old_desc = post.get('excerpt', {}).get('rendered', '')
                if wp_request(domain, user, password, f"posts/{post['id']}", 'POST', {'excerpt': desc}):
                    conn = get_conn()
                    if conn:
                        sql = "INSERT INTO wp_seo_fixes (domain, post_id, fix_type, old_value, new_value, applied, fix_date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                        safe_insert(conn, sql, (domain, post['id'], 'missing_description', old_desc, desc, True, datetime.now().date()))
                        conn.close()
                    logger.info(f"[DB] SEO fix logged: post {post['id']} description")

    # Find duplicates by title/slug
    seen = {}
    for post in posts:
        title = post.get('title', {}).get('rendered', '')
        key = title.lower()
        if key in seen:
            logger.warning(f"DUPLICATE: Posts {seen[key]} and {post['id']} - '{title}'")
        else:
            seen[key] = post['id']

    # Fix missing alt-text
    media = get_paginated(domain, user, password, 'media', logger)
    for item in media:
        if not item.get('alt_text', '').strip():
            filename = item.get('source_url', '').split('/')[-1]
            prompt = f"SEO alt-text (max 125 chars) for: {filename}"
            alt = qwen_generate(prompt)
            if alt:
                if wp_request(domain, user, password, f"media/{item['id']}", 'POST', {'alt_text': alt}):
                    conn = get_conn()
                    if conn:
                        sql = "INSERT INTO wp_seo_fixes (domain, post_id, fix_type, old_value, new_value, applied, fix_date) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                        safe_insert(conn, sql, (domain, item['id'], 'missing_alt_text', '', alt, True, datetime.now().date()))
                        conn.close()
                    logger.info(f"[DB] SEO fix logged: media {item['id']} alt-text")

    logger.info(f"Completed SEO fix for {domain}\n")

def get_site_for_today():
    """Rotate through sites: day mod 8"""
    day = datetime.now().timetuple().tm_yday
    return SITES[day % len(SITES)]

if __name__ == '__main__':
    env = load_env()
    domain, env_key = get_site_for_today()
    logger = setup_logging(domain)
    logger.info(f"Processing site: {domain}")

    user = env.get(f"{env_key}_USER")
    password = env.get(f"{env_key}_PASS")

    if user and password:
        fix_seo(domain, user, password, logger)
    else:
        logger.error(f"Missing credentials for {domain}")
