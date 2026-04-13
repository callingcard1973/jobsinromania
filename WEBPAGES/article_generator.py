#!/usr/bin/env python3
"""
SEO Article Generator: Create, translate, and deploy articles to 14 job sites.
Qwen 2.5 on raspibig (ollama, http://192.168.100.20:11434/api/generate).
Outputs: English articles + 11 language translations + HTML with schema + cPanel deployment.
"""
import requests, json, os, sys, re, urllib.request, urllib.parse, ssl
from datetime import datetime
from pathlib import Path
from time import sleep

LOG_FILE = f"article_deployment_{datetime.now().strftime('%Y-%m-%d')}.log"
SITES = {
    "careworkers.eu": "Care Workers",
    "factoryjobs.eu": "Factory Jobs",
    "buildjobs.eu": "Construction",
    "electricjobs.eu": "Electrician",
    "farmworkers.eu": "Farm Workers",
    "horecaworkers.eu": "Hospitality",
    "meatworkers.eu": "Meat Processing",
    "mechanicjobs.eu": "Mechanics",
    "warehouseworkers.eu": "Warehouse",
    "aluminumrecyclehub.com": "Aluminum Recycling",
    "expatsinromania.org": "Expat Services",
    "interjob.ro": "InterJob Romania",
    "mivromania.info": "MivRomania",
    "nepalezi.com": "Nepali Workers"
}
LANGS = ["ar", "bn", "hi", "ur", "vi", "am", "ne", "pa", "ps", "uz"]
QWEN_URL = "http://192.168.100.20:11434/api/generate"
CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com"
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"

def log(msg):
    print(msg)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")

def qwen_generate(prompt, retries=3):
    """Call Qwen via ollama with retry logic."""
    for attempt in range(retries):
        try:
            r = requests.post(QWEN_URL, json={
                "model": "qwen2.5:7b-instruct",
                "prompt": prompt,
                "stream": False
            }, timeout=120)
            if r.status_code == 200:
                return r.json().get("response", "").strip()
        except Exception as e:
            log(f"Qwen error (attempt {attempt+1}/{retries}): {e}")
            if attempt < retries - 1:
                sleep(5)
    return None

def generate_article(domain, topic):
    """Generate 600-word English article via Qwen."""
    sector = SITES.get(domain, domain)
    templates = {
        "Best jobs": f"Write a comprehensive 600-word SEO article about the best jobs in {sector} in Europe. Focus on job types, locations, requirements, and salary expectations.",
        "Salary guide": f"Write a 600-word guide about salary expectations for {sector} workers in Europe. Include country comparisons, skill premiums, and earning potential.",
        "Worker tips": f"Write 600 words of practical tips for {sector} workers in Europe. Cover work culture, certification requirements, safety, and career advancement."
    }
    prompt = templates.get(topic, templates["Best jobs"])
    article = qwen_generate(prompt)
    return article if article and len(article) > 400 else None

def translate_article(article, lang, retries=3):
    """Translate article to target language via Qwen."""
    prompt = f"Translate this article to {lang} (maintain markdown, preserve HTML tags):\n\n{article}"
    return qwen_generate(prompt, retries)

def make_slug(text):
    """Convert text to URL slug."""
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def html_from_markdown(md, title, lang, domain):
    """Convert markdown to HTML with schema, hreflang, og tags."""
    rtl_langs = {"ar", "ur", "ps"}
    is_rtl = lang in rtl_langs

    html_content = md.replace('\n# ', '<h2>').replace('\n## ', '<h3>')
    html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
    html_content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html_content)

    hreflang = "\n".join([
        f'<link rel="alternate" hreflang="en" href="https://{domain}/articles/{make_slug(title)}/en.html"/>'
    ] + [f'<link rel="alternate" hreflang="{l}" href="https://{domain}/articles/{make_slug(title)}/{l}.html"/>'
         for l in LANGS])

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "articleBody": md[:200],
        "datePublished": datetime.now().isoformat(),
        "inLanguage": lang
    })

    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{'rtl' if is_rtl else 'ltr'}">
<head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width"/>
<title>{title}</title>
<meta name="description" content="{md[:160]}"/>
<meta property="og:title" content="{title}"/>
<meta property="og:description" content="{md[:160]}"/>
<meta property="og:image" content="https://{domain}/og-image.jpg"/>
{hreflang}
<script type="application/ld+json">{schema}</script>
</head>
<body>
<article>
<h1>{title}</h1>
{html_content}
</article>
</body>
</html>"""

def cpanel_upload(domain, slug, lang, html_content):
    """Upload to A2 via cPanel API."""
    path = f"articles/{slug}/{lang}.html"
    url = f"https://{CPANEL_HOST}:2083/execute/Fileman/save_file"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    data = urllib.parse.urlencode({
        "dir": f"/{domain}",
        "file": path,
        "content": html_content
    }).encode()

    req = urllib.request.Request(url, data=data)
    req.add_header('Authorization', f'cpanel {CPANEL_USER}:{CPANEL_TOKEN}')

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            result = json.loads(r.read().decode())
            return result.get("status") == 1
    except Exception as e:
        log(f"cPanel upload failed: {e}")
        return False

def process_site(domain):
    """Generate, translate, and deploy articles for one site."""
    log(f"\n=== Processing {domain} ===")
    topics = ["Best jobs", "Salary guide", "Worker tips"]

    for topic in topics:
        log(f"Generating: {topic}")
        article = generate_article(domain, topic)
        if not article:
            log(f"Failed to generate {topic}, skipping")
            continue

        slug = make_slug(f"{topic}-{SITES[domain]}")
        title = f"{topic} in {SITES[domain]}"

        # Deploy English
        html = html_from_markdown(article, title, "en", domain)
        if cpanel_upload(domain, slug, "en", html):
            log(f"Deployed {topic} (en)")
            # Write to DB
            try:
                import sys, os
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from db_client import get_conn, safe_insert
                conn = get_conn()
                if conn:
                    sql = """
                        INSERT INTO generated_articles (domain, topic, title, slug, lang, deployed, deploy_path, date_published)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (domain, slug, lang) DO UPDATE SET
                            deployed = EXCLUDED.deployed,
                            deploy_path = EXCLUDED.deploy_path,
                            date_published = EXCLUDED.date_published
                    """
                    params = (domain, topic, title, slug, "en", True, f"/articles/{slug}/en.html", datetime.now())
                    safe_insert(conn, sql, params)
                    conn.close()
            except ImportError:
                pass
        else:
            log(f"Failed to deploy {topic} (en)")
            continue

        # Translate and deploy
        for lang in LANGS:
            translated = translate_article(article, lang)
            if translated:
                html = html_from_markdown(translated, title, lang, domain)
                if cpanel_upload(domain, slug, lang, html):
                    log(f"Deployed {topic} ({lang})")
                    # Write to DB
                    try:
                        from db_client import get_conn, safe_insert
                        conn = get_conn()
                        if conn:
                            sql = """
                                INSERT INTO generated_articles (domain, topic, title, slug, lang, deployed, deploy_path, date_published)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (domain, slug, lang) DO UPDATE SET
                                    deployed = EXCLUDED.deployed,
                                    deploy_path = EXCLUDED.deploy_path,
                                    date_published = EXCLUDED.date_published
                            """
                            params = (domain, topic, title, slug, lang, True, f"/articles/{slug}/{lang}.html", datetime.now())
                            safe_insert(conn, sql, params)
                            conn.close()
                    except ImportError:
                        pass
            sleep(2)  # Rate limit

def main():
    """Main: process sites interactively or auto."""
    run_mode = os.getenv("RUN_MODE", "interactive").lower()

    if run_mode == "auto":
        for domain in SITES.keys():
            process_site(domain)
    else:
        print("\nAvailable sites:")
        for i, (d, s) in enumerate(SITES.items(), 1):
            print(f"{i}. {d} ({s})")
        choice = input("\nEnter site number (1-14) or press Enter to process all: ").strip()

        if not choice:
            for domain in SITES.keys():
                process_site(domain)
        elif choice.isdigit() and 1 <= int(choice) <= len(SITES):
            domain = list(SITES.keys())[int(choice) - 1]
            process_site(domain)
        else:
            print("Invalid choice")

    log(f"\nDeployment complete. Log: {LOG_FILE}")

if __name__ == "__main__":
    main()
