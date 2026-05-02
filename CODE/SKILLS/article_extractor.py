#!/usr/bin/env python3
"""
Article Extractor - Extract and summarize web content
Usage: python3 article_extractor.py <url> [--output file.md] [--format json|md|txt]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS, fetch_url

import os
import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin

# ============================================================
# CONFIGURATION
# ============================================================

CACHE_DIR = Path('/tmp/article_cache')
CACHE_DIR.mkdir(exist_ok=True)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Tags to remove completely
REMOVE_TAGS = [
    'script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe',
    'noscript', 'svg', 'form', 'button', 'input', 'select', 'textarea',
    'advertisement', 'ad', 'sidebar', 'menu', 'popup', 'modal', 'cookie',
]

# Tags that typically contain main content
CONTENT_TAGS = ['article', 'main', 'content', 'post', 'entry', 'story']

# ============================================================
# HTML PARSING (no external dependencies)
# ============================================================

def clean_html(html: str) -> str:
    """Remove unwanted tags and clean HTML"""
    # Remove comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # Remove unwanted tags with content
    for tag in REMOVE_TAGS:
        html = re.sub(rf'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(rf'<{tag}[^>]*/>', '', html, flags=re.IGNORECASE)

    return html

def extract_text(html: str) -> str:
    """Extract readable text from HTML"""
    # Clean first
    html = clean_html(html)

    # Convert common elements to readable format
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</?p[^>]*>', '\n\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</?div[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</?li[^>]*>', '\n• ', html, flags=re.IGNORECASE)
    html = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n\n## \1\n\n', html, flags=re.DOTALL | re.IGNORECASE)

    # Remove remaining tags
    text = re.sub(r'<[^>]+>', '', html)

    # Decode entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)

    # Clean whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    return text.strip()

def extract_title(html: str) -> str:
    """Extract page title"""
    # Try og:title first
    match = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try title tag
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL | re.IGNORECASE)
    if match:
        title = re.sub(r'<[^>]+>', '', match.group(1))
        return title.strip()

    # Try h1
    match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    if match:
        title = re.sub(r'<[^>]+>', '', match.group(1))
        return title.strip()

    return 'Untitled'

def extract_description(html: str) -> str:
    """Extract meta description"""
    match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    match = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return ''

def extract_author(html: str) -> str:
    """Extract author"""
    match = re.search(r'<meta[^>]*name=["\']author["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    match = re.search(r'<meta[^>]*property=["\']article:author["\'][^>]*content=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return ''

def extract_date(html: str) -> str:
    """Extract publish date"""
    patterns = [
        r'<meta[^>]*property=["\']article:published_time["\'][^>]*content=["\']([^"\']+)["\']',
        r'<time[^>]*datetime=["\']([^"\']+)["\']',
        r'"datePublished"\s*:\s*"([^"]+)"',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            # Try to parse and format
            try:
                if 'T' in date_str:
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
            return date_str[:10]

    return ''

def extract_links(html: str, base_url: str) -> List[Dict]:
    """Extract all links from page"""
    links = []
    seen = set()

    for match in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.DOTALL | re.IGNORECASE):
        href = match.group(1).strip()
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()

        if not href or href.startswith('#') or href.startswith('javascript:'):
            continue

        # Make absolute URL
        full_url = urljoin(base_url, href)

        if full_url not in seen and text:
            seen.add(full_url)
            links.append({'url': full_url, 'text': text[:100]})

    return links[:50]  # Limit to 50 links

def extract_main_content(html: str) -> str:
    """Try to extract main article content"""
    # Try to find article/main/content sections
    for tag in CONTENT_TAGS:
        # Try class/id containing the word
        match = re.search(rf'<[^>]*(class|id)=["\'][^"\']*{tag}[^"\']*["\'][^>]*>(.*?)</\w+>',
                         html, re.DOTALL | re.IGNORECASE)
        if match and len(match.group(2)) > 500:
            return extract_text(match.group(2))

        # Try tag directly
        match = re.search(rf'<{tag}[^>]*>(.*?)</{tag}>', html, re.DOTALL | re.IGNORECASE)
        if match and len(match.group(1)) > 500:
            return extract_text(match.group(1))

    # Fall back to body
    match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if match:
        return extract_text(match.group(1))

    return extract_text(html)

# ============================================================
# FETCHING
# ============================================================

def fetch_url(url: str, use_cache: bool = True) -> str:
    """Fetch URL content with caching"""
    # Check cache
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{url_hash}.html"

    if use_cache and cache_file.exists():
        # Cache valid for 1 hour
        age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if age < 3600:
            return cache_file.read_text(encoding='utf-8', errors='ignore')

    # Fetch
    headers = {'User-Agent': USER_AGENT}

    if HTTP_CLIENT == 'httpx':
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            response = client.get(url, headers=headers)
            html = response.text
    else:
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        html = response.text

    # Cache
    cache_file.write_text(html, encoding='utf-8')

    return html

# ============================================================
# MAIN EXTRACTION
# ============================================================

def extract_article(url: str) -> Dict:
    """Extract article content from URL"""
    result = {
        'url': url,
        'domain': urlparse(url).netloc,
        'title': '',
        'author': '',
        'date': '',
        'description': '',
        'content': '',
        'word_count': 0,
        'links': [],
        'extracted_at': datetime.now().isoformat(),
        'error': None,
    }

    try:
        html = fetch_url(url)

        result['title'] = extract_title(html)
        result['author'] = extract_author(html)
        result['date'] = extract_date(html)
        result['description'] = extract_description(html)
        result['content'] = extract_main_content(html)
        result['word_count'] = len(result['content'].split())
        result['links'] = extract_links(html, url)

    except Exception as e:
        result['error'] = str(e)

    return result

def summarize_content(content: str, max_sentences: int = 5) -> str:
    """Simple extractive summary - first N sentences"""
    sentences = re.split(r'(?<=[.!?])\s+', content)
    # Filter out short/noisy sentences
    sentences = [s for s in sentences if len(s) > 30 and not s.startswith('•')]
    return ' '.join(sentences[:max_sentences])

# ============================================================
# OUTPUT FORMATTING
# ============================================================

def format_markdown(article: Dict) -> str:
    """Format article as Markdown"""
    lines = [
        f"# {article['title']}",
        "",
        f"**Source:** [{article['domain']}]({article['url']})",
    ]

    if article['author']:
        lines.append(f"**Author:** {article['author']}")
    if article['date']:
        lines.append(f"**Date:** {article['date']}")

    lines.extend([
        f"**Words:** {article['word_count']}",
        "",
    ])

    if article['description']:
        lines.extend([
            "## Summary",
            article['description'],
            "",
        ])

    lines.extend([
        "## Content",
        article['content'][:5000] + ('...' if len(article['content']) > 5000 else ''),
        "",
    ])

    if article['links']:
        lines.extend([
            "## Links",
            "",
        ])
        for link in article['links'][:10]:
            lines.append(f"- [{link['text']}]({link['url']})")

    return '\n'.join(lines)

def format_text(article: Dict) -> str:
    """Format article as plain text"""
    lines = [
        "=" * 60,
        article['title'],
        "=" * 60,
        "",
        f"Source: {article['url']}",
    ]

    if article['author']:
        lines.append(f"Author: {article['author']}")
    if article['date']:
        lines.append(f"Date: {article['date']}")

    lines.extend([
        f"Words: {article['word_count']}",
        "",
        "-" * 60,
        "",
        article['content'][:5000],
        "",
        "=" * 60,
    ])

    return '\n'.join(lines)

# ============================================================
# BATCH PROCESSING
# ============================================================

def extract_multiple(urls: List[str]) -> List[Dict]:
    """Extract multiple URLs"""
    results = []
    for url in urls:
        print(f"  Extracting: {url[:60]}...")
        result = extract_article(url)
        results.append(result)
    return results

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if not args or args[0] in ['-h', '--help']:
        print(f"""
{'='*60}
ARTICLE EXTRACTOR
{'='*60}

Usage: article_extractor.py <url> [options]
       article_extractor.py --batch urls.txt [options]

Options:
  --output FILE    Save to file (default: print to stdout)
  --format FORMAT  Output format: md, json, txt (default: md)
  --no-cache       Disable URL caching
  --links          Include extracted links in output
  --summary        Show only summary (first 5 sentences)

Examples:
  article_extractor.py https://example.com/article
  article_extractor.py https://news.site/story --format json --output story.json
  article_extractor.py --batch urls.txt --format md --output articles.md

Batch file format (one URL per line):
  https://example.com/article1
  https://example.com/article2
""")
        return

    # Parse arguments
    urls = []
    output_file = None
    output_format = 'md'
    use_cache = True
    show_links = False
    summary_only = False

    i = 0
    while i < len(args):
        arg = args[i]

        if arg == '--batch' and i + 1 < len(args):
            # Read URLs from file
            batch_file = args[i + 1]
            if os.path.exists(batch_file):
                with open(batch_file) as f:
                    urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            i += 2
        elif arg == '--output' and i + 1 < len(args):
            output_file = args[i + 1]
            i += 2
        elif arg == '--format' and i + 1 < len(args):
            output_format = args[i + 1]
            i += 2
        elif arg == '--no-cache':
            use_cache = False
            i += 1
        elif arg == '--links':
            show_links = True
            i += 1
        elif arg == '--summary':
            summary_only = True
            i += 1
        elif arg.startswith('http'):
            urls.append(arg)
            i += 1
        else:
            i += 1

    if not urls:
        print("Error: No URLs provided")
        return

    print(f"\n{'='*60}")
    print(f"ARTICLE EXTRACTOR")
    print(f"URLs: {len(urls)}")
    print(f"Format: {output_format}")
    print(f"{'='*60}\n")

    # Extract
    articles = []
    for url in urls:
        print(f"Extracting: {urlparse(url).netloc}...")
        article = extract_article(url)

        if article['error']:
            print(f"  Error: {article['error']}")
        else:
            print(f"  Title: {article['title'][:50]}...")
            print(f"  Words: {article['word_count']}")

        if summary_only and article['content']:
            article['content'] = summarize_content(article['content'])

        if not show_links:
            article['links'] = []

        articles.append(article)

    # Format output
    if output_format == 'json':
        output = json.dumps(articles if len(articles) > 1 else articles[0], indent=2, ensure_ascii=False)
    elif output_format == 'txt':
        output = '\n\n'.join(format_text(a) for a in articles)
    else:  # md
        output = '\n\n---\n\n'.join(format_markdown(a) for a in articles)

    # Output
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\nSaved to: {output_file}")
    else:
        print(f"\n{'='*60}")
        print(output[:3000])
        if len(output) > 3000:
            print(f"\n... ({len(output)} chars total, use --output to save full content)")

    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()
