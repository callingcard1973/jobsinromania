#!/usr/bin/env python3
"""
A2 Link Verifier - Check all links on A2-hosted websites.

Usage:
    python3 a2_link_verifier.py --domain factoryjobs.eu
    python3 a2_link_verifier.py --domain factoryjobs.eu --skip-external
    python3 a2_link_verifier.py --summary
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import csv
import time
import argparse
import logging
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

# Try to import shared modules
try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg): print(f"[TELEGRAM] {msg}")

try:
    from skills_common import to_ascii
except ImportError:
    import unicodedata
    def to_ascii(text):
        if not text:
            return text
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')


# Configuration
OUTPUT_DIR = "/opt/ACTIVE/OPENDATA/DATA/LINK_AUDIT"

CRAWL_CONFIG = {
    "max_depth": 3,
    "page_delay": 0.5,
    "timeout": 10,
    "user_agent": "A2LinkVerifier/1.0 (internal audit)",
    "excluded_extensions": ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
                            '.css', '.js', '.woff', '.woff2', '.mp4', '.mp3', '.zip',
                            '.doc', '.docx', '.xls', '.xlsx'],
    "excluded_patterns": ['/wp-admin/', '/wp-login', 'xmlrpc.php', '/wp-json/'],
}

HTTP_CONFIG = {
    "timeout": 10,
    "retry_count": 2,
    "retry_delay": 2,
    "max_workers": 15,
}

# Known false positive domains (block HEAD, return 403/999)
FALSE_POSITIVE_DOMAINS = [
    'linkedin.com', 'facebook.com', 'twitter.com', 'x.com',
    'instagram.com', 'tiktok.com', 'stackoverflow.com', 'amazon.com',
]


@dataclass
class LinkInfo:
    url: str
    is_internal: bool
    source_pages: List[str]
    status_code: Optional[int] = None
    status_msg: str = ""
    is_broken: bool = False
    link_type: str = "unknown"  # internal, external, mailto, tel, anchor


@dataclass
class CrawlResult:
    domain: str
    pages_crawled: int
    internal_links: Dict[str, List[str]]  # url -> [source pages]
    external_links: Dict[str, List[str]]
    mailto_links: Dict[str, List[str]]
    tel_links: Dict[str, List[str]]
    errors: List[dict]
    crawl_time_sec: float


class SiteCrawler:
    """Crawl a single website, extracting all links."""

    def __init__(self, domain: str, config: dict = None):
        self.domain = domain
        self.base_url = f"https://{domain}"
        self.config = config or CRAWL_CONFIG

        self.visited: Set[str] = set()
        self.pending: List[Tuple[str, int]] = []  # (url, depth)
        self.internal_links: Dict[str, List[str]] = defaultdict(list)
        self.external_links: Dict[str, List[str]] = defaultdict(list)
        self.mailto_links: Dict[str, List[str]] = defaultdict(list)
        self.tel_links: Dict[str, List[str]] = defaultdict(list)
        self.errors: List[dict] = []

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.config['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

        # Setup logging
        self.logger = logging.getLogger(f"crawler.{domain}")

    def crawl(self, max_depth: int = None) -> CrawlResult:
        """Crawl site starting from homepage."""
        max_depth = max_depth or self.config['max_depth']
        start_time = time.time()

        # Start with homepage and common pages
        self.pending.append((self.base_url, 0))
        self.pending.append((f"{self.base_url}/", 0))

        while self.pending:
            url, depth = self.pending.pop(0)
            normalized = self._normalize_url(url)

            if normalized in self.visited or depth > max_depth:
                continue

            if self._should_skip_url(url):
                continue

            self.visited.add(normalized)
            self.logger.info(f"Crawling [{depth}]: {url}")

            self._process_page(url, depth)
            time.sleep(self.config['page_delay'])

        crawl_time = time.time() - start_time

        return CrawlResult(
            domain=self.domain,
            pages_crawled=len(self.visited),
            internal_links=dict(self.internal_links),
            external_links=dict(self.external_links),
            mailto_links=dict(self.mailto_links),
            tel_links=dict(self.tel_links),
            errors=self.errors,
            crawl_time_sec=crawl_time
        )

    def _process_page(self, url: str, depth: int):
        """Fetch and parse a single page."""
        try:
            response = self.session.get(
                url,
                timeout=self.config['timeout'],
                allow_redirects=True,
                verify=True
            )

            if response.status_code != 200:
                self.errors.append({
                    'url': url,
                    'error': f"HTTP {response.status_code}",
                    'type': 'fetch_error'
                })
                return

            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type.lower():
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            self._extract_links(soup, url, depth)

        except requests.exceptions.SSLError as e:
            # Try without SSL verification
            try:
                response = self.session.get(
                    url,
                    timeout=self.config['timeout'],
                    allow_redirects=True,
                    verify=False
                )
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    self._extract_links(soup, url, depth)
                    self.errors.append({
                        'url': url,
                        'error': 'SSL warning (verified=False worked)',
                        'type': 'ssl_warning'
                    })
            except Exception as e2:
                self.errors.append({
                    'url': url,
                    'error': f"SSL: {str(e)}",
                    'type': 'ssl_error'
                })
        except requests.exceptions.Timeout:
            self.errors.append({
                'url': url,
                'error': 'Timeout',
                'type': 'timeout'
            })
        except Exception as e:
            self.errors.append({
                'url': url,
                'error': str(e),
                'type': 'error'
            })

    def _extract_links(self, soup: BeautifulSoup, base_url: str, depth: int):
        """Extract all links from page."""
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()

            if not href:
                continue

            # Handle special link types
            if href.startswith('mailto:'):
                email = href[7:].split('?')[0]
                self.mailto_links[email].append(base_url)
                continue

            if href.startswith('tel:'):
                phone = href[4:]
                self.tel_links[phone].append(base_url)
                continue

            if href.startswith('#') or href.startswith('javascript:'):
                continue

            # Resolve relative URLs
            try:
                full_url = urljoin(base_url, href)
            except Exception:
                continue

            # Classify link
            if self._is_internal(full_url):
                self.internal_links[full_url].append(base_url)
                normalized = self._normalize_url(full_url)
                if normalized not in self.visited:
                    self.pending.append((full_url, depth + 1))
            else:
                self.external_links[full_url].append(base_url)

    def _is_internal(self, url: str) -> bool:
        """Check if URL is internal to this domain."""
        try:
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            domain = self.domain.lower()
            return (host == domain or
                    host == f"www.{domain}" or
                    host.endswith(f".{domain}"))
        except Exception:
            return False

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for deduplication."""
        try:
            parsed = urlparse(url)
            path = parsed.path.rstrip('/')
            if path.endswith('/index.html') or path.endswith('/index.htm'):
                path = path.rsplit('/', 1)[0]
            if not path:
                path = ''
            return f"{parsed.scheme}://{parsed.netloc.lower()}{path}"
        except Exception:
            return url

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped."""
        url_lower = url.lower()

        # Skip excluded extensions
        for ext in self.config['excluded_extensions']:
            if url_lower.endswith(ext):
                return True

        # Skip excluded patterns
        for pattern in self.config['excluded_patterns']:
            if pattern in url_lower:
                return True

        return False


class LinkChecker:
    """Validate links via HTTP requests."""

    def __init__(self, config: dict = None):
        self.config = config or HTTP_CONFIG
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; LinkChecker/1.0)',
        })
        self.logger = logging.getLogger("link_checker")

    def check_url(self, url: str) -> Tuple[Optional[int], str, bool]:
        """
        Check URL accessibility.
        Returns (status_code, message, is_broken).
        """
        # Skip known false positive domains
        try:
            parsed = urlparse(url)
            for fp_domain in FALSE_POSITIVE_DOMAINS:
                if fp_domain in parsed.netloc:
                    return None, "Skipped (known false positive)", False
        except Exception:
            pass

        for attempt in range(self.config['retry_count']):
            try:
                # Try HEAD first (faster)
                response = self.session.head(
                    url,
                    timeout=self.config['timeout'],
                    allow_redirects=True
                )

                # Fallback to GET if HEAD blocked
                if response.status_code in [405, 403, 501]:
                    response = self.session.get(
                        url,
                        timeout=self.config['timeout'],
                        allow_redirects=True,
                        stream=True
                    )
                    response.close()

                is_broken = response.status_code >= 400
                return response.status_code, response.reason, is_broken

            except requests.exceptions.Timeout:
                if attempt < self.config['retry_count'] - 1:
                    time.sleep(self.config['retry_delay'] * (attempt + 1))
                    continue
                return None, "Timeout", True

            except requests.exceptions.SSLError:
                return None, "SSL Error", True

            except requests.exceptions.ConnectionError as e:
                err_str = str(e).lower()
                if 'name or service not known' in err_str or 'nodename nor servname' in err_str:
                    return None, "Domain not found", True
                if 'connection refused' in err_str:
                    return None, "Connection refused", True
                return None, "Connection Error", True

            except Exception as e:
                return None, str(e)[:50], True

        return None, "Max retries exceeded", True

    def check_urls_parallel(self, urls: Dict[str, List[str]]) -> List[LinkInfo]:
        """Check multiple URLs in parallel."""
        results = []
        total = len(urls)
        checked = 0

        with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
            future_to_url = {
                executor.submit(self.check_url, url): url
                for url in urls.keys()
            }

            for future in as_completed(future_to_url):
                url = future_to_url[future]
                checked += 1

                try:
                    status_code, message, is_broken = future.result()
                except Exception as e:
                    status_code, message, is_broken = None, str(e), True

                results.append(LinkInfo(
                    url=url,
                    is_internal=False,
                    source_pages=urls[url],
                    status_code=status_code,
                    status_msg=message,
                    is_broken=is_broken,
                    link_type="external"
                ))

                if checked % 10 == 0:
                    self.logger.info(f"Checked {checked}/{total} external links")

        return results


class ReportGenerator:
    """Generate various report formats."""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_domain_report(self, domain: str, crawl_result: CrawlResult,
                               broken_internal: List[LinkInfo],
                               broken_external: List[LinkInfo]) -> str:
        """Generate markdown report for single domain."""
        lines = [
            f"# Link Report: {domain}",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Pages Crawled:** {crawl_result.pages_crawled}",
            f"**Crawl Time:** {crawl_result.crawl_time_sec:.1f} seconds",
            "",
            "## Statistics",
            "",
            f"- Internal Links: {len(crawl_result.internal_links)}",
            f"- External Links: {len(crawl_result.external_links)}",
            f"- Mailto Links: {len(crawl_result.mailto_links)}",
            f"- Tel Links: {len(crawl_result.tel_links)}",
            "",
            f"- **Broken Internal:** {len(broken_internal)}",
            f"- **Broken External:** {len(broken_external)}",
            "",
        ]

        # Broken internal links
        if broken_internal:
            lines.extend([
                "## Broken Internal Links",
                "",
            ])
            for link in broken_internal[:50]:
                pages = ", ".join(link.source_pages[:2])
                if len(link.source_pages) > 2:
                    pages += f" (+{len(link.source_pages)-2})"
                lines.append(f"- **{link.status_msg}**: `{link.url}`")
                lines.append(f"  - Found on: {pages}")
            if len(broken_internal) > 50:
                lines.append(f"\n*...and {len(broken_internal) - 50} more*")
            lines.append("")

        # Broken external links
        if broken_external:
            lines.extend([
                "## Broken External Links",
                "",
            ])
            for link in broken_external[:50]:
                pages = ", ".join(link.source_pages[:2])
                if len(link.source_pages) > 2:
                    pages += f" (+{len(link.source_pages)-2})"
                status = link.status_code or link.status_msg
                lines.append(f"- **{status}**: `{link.url}`")
                lines.append(f"  - Found on: {pages}")
            if len(broken_external) > 50:
                lines.append(f"\n*...and {len(broken_external) - 50} more*")
            lines.append("")

        # Crawl errors
        if crawl_result.errors:
            lines.extend([
                "## Crawl Errors",
                "",
            ])
            for err in crawl_result.errors[:20]:
                lines.append(f"- {err['type']}: `{err['url']}` - {err['error']}")
            lines.append("")

        return "\n".join(lines)

    def save_broken_links_csv(self, domain: str, broken_internal: List[LinkInfo],
                              broken_external: List[LinkInfo]) -> str:
        """Save broken links to CSV."""
        filepath = os.path.join(self.output_dir, domain, "broken_links.csv")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['type', 'url', 'status_code', 'status_msg', 'found_on'])

            for link in broken_internal:
                writer.writerow([
                    'internal',
                    link.url,
                    link.status_code or '',
                    link.status_msg,
                    '|'.join(link.source_pages[:5])
                ])

            for link in broken_external:
                writer.writerow([
                    'external',
                    link.url,
                    link.status_code or '',
                    link.status_msg,
                    '|'.join(link.source_pages[:5])
                ])

        return filepath

    def save_all_links_json(self, domain: str, crawl_result: CrawlResult) -> str:
        """Save complete link data to JSON."""
        filepath = os.path.join(self.output_dir, domain, "all_links.json")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        data = {
            'domain': domain,
            'crawled_at': datetime.now().isoformat(),
            'pages_crawled': crawl_result.pages_crawled,
            'crawl_time_sec': crawl_result.crawl_time_sec,
            'internal_links': crawl_result.internal_links,
            'external_links': crawl_result.external_links,
            'mailto_links': crawl_result.mailto_links,
            'tel_links': crawl_result.tel_links,
            'errors': crawl_result.errors,
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)

        return filepath


def check_internal_links(domain: str, internal_links: Dict[str, List[str]]) -> List[LinkInfo]:
    """Check internal links via HTTP."""
    checker = LinkChecker()
    broken = []

    total = len(internal_links)
    logging.info(f"Checking {total} internal links...")

    for i, (url, source_pages) in enumerate(internal_links.items()):
        if (i + 1) % 20 == 0:
            logging.info(f"Checked {i+1}/{total} internal links")

        status_code, message, is_broken = checker.check_url(url)

        if is_broken:
            broken.append(LinkInfo(
                url=url,
                is_internal=True,
                source_pages=source_pages,
                status_code=status_code,
                status_msg=message,
                is_broken=True,
                link_type="internal"
            ))

        time.sleep(0.1)  # Small delay

    return broken


def verify_domain(domain: str, skip_external: bool = False, max_depth: int = 3) -> dict:
    """Run full verification on a single domain."""
    logging.info(f"Starting verification of {domain}")

    # Create output directory
    domain_dir = os.path.join(OUTPUT_DIR, domain)
    os.makedirs(domain_dir, exist_ok=True)

    # Setup file logging
    log_file = os.path.join(domain_dir, "crawl.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    # Step 1: Crawl the site
    logging.info(f"Step 1: Crawling {domain}...")
    crawler = SiteCrawler(domain)
    crawl_result = crawler.crawl(max_depth=max_depth)

    logging.info(f"Crawled {crawl_result.pages_crawled} pages")
    logging.info(f"Found {len(crawl_result.internal_links)} internal links")
    logging.info(f"Found {len(crawl_result.external_links)} external links")

    # Step 2: Check internal links
    logging.info("Step 2: Checking internal links...")
    broken_internal = check_internal_links(domain, crawl_result.internal_links)
    logging.info(f"Found {len(broken_internal)} broken internal links")

    # Step 3: Check external links (if not skipped)
    broken_external = []
    if not skip_external and crawl_result.external_links:
        logging.info("Step 3: Checking external links...")
        checker = LinkChecker()
        external_results = checker.check_urls_parallel(crawl_result.external_links)
        broken_external = [r for r in external_results if r.is_broken]
        logging.info(f"Found {len(broken_external)} broken external links")
    elif skip_external:
        logging.info("Step 3: Skipped external link checking")

    # Step 4: Generate reports
    logging.info("Step 4: Generating reports...")
    report_gen = ReportGenerator(OUTPUT_DIR)

    # Markdown report
    report_md = report_gen.generate_domain_report(
        domain, crawl_result, broken_internal, broken_external
    )
    report_path = os.path.join(domain_dir, "report.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_md)

    # CSV of broken links
    csv_path = report_gen.save_broken_links_csv(domain, broken_internal, broken_external)

    # JSON of all links
    json_path = report_gen.save_all_links_json(domain, crawl_result)

    logging.info(f"Reports saved to {domain_dir}")

    # Clean up file handler
    logging.getLogger().removeHandler(file_handler)
    file_handler.close()

    return {
        'domain': domain,
        'pages_crawled': crawl_result.pages_crawled,
        'internal_links': len(crawl_result.internal_links),
        'external_links': len(crawl_result.external_links),
        'broken_internal': len(broken_internal),
        'broken_external': len(broken_external),
        'report_dir': domain_dir,
    }


def generate_summary():
    """Generate summary across all checked domains."""
    summaries = []

    for item in os.listdir(OUTPUT_DIR):
        item_path = os.path.join(OUTPUT_DIR, item)
        if os.path.isdir(item_path) and item not in ['__pycache__']:
            json_path = os.path.join(item_path, "all_links.json")
            if os.path.exists(json_path):
                with open(json_path) as f:
                    data = json.load(f)

                csv_path = os.path.join(item_path, "broken_links.csv")
                broken_count = 0
                if os.path.exists(csv_path):
                    with open(csv_path) as f:
                        broken_count = sum(1 for _ in f) - 1  # Exclude header

                summaries.append({
                    'domain': item,
                    'crawled_at': data.get('crawled_at', 'N/A'),
                    'pages': data.get('pages_crawled', 0),
                    'internal': len(data.get('internal_links', {})),
                    'external': len(data.get('external_links', {})),
                    'broken': broken_count
                })

    if not summaries:
        print("No domains have been checked yet.")
        return

    # Sort by broken count
    summaries.sort(key=lambda x: x['broken'], reverse=True)

    lines = [
        "# A2 Link Verification Summary",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Domains Checked:** {len(summaries)}",
        "",
        "| Domain | Pages | Internal | External | Broken |",
        "|--------|-------|----------|----------|--------|",
    ]

    for s in summaries:
        lines.append(f"| {s['domain']} | {s['pages']} | {s['internal']} | {s['external']} | {s['broken']} |")

    summary_path = os.path.join(OUTPUT_DIR, "summary.md")
    with open(summary_path, 'w') as f:
        f.write("\n".join(lines))

    print("\n".join(lines))
    print(f"\nSummary saved to: {summary_path}")


def main():
    parser = argparse.ArgumentParser(description="A2 Link Verifier")
    parser.add_argument("--domain", help="Domain to check (e.g., factoryjobs.eu)")
    parser.add_argument("--skip-external", action="store_true",
                        help="Skip external link validation")
    parser.add_argument("--max-depth", type=int, default=3,
                        help="Maximum crawl depth (default: 3)")
    parser.add_argument("--summary", action="store_true",
                        help="Generate summary across all checked domains")
    parser.add_argument("--notify", action="store_true",
                        help="Send Telegram notification when done")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    if args.summary:
        generate_summary()
        return

    if not args.domain:
        parser.error("--domain is required (or use --summary)")

    # Run verification
    try:
        result = verify_domain(
            args.domain,
            skip_external=args.skip_external,
            max_depth=args.max_depth
        )

        # Print summary
        print(f"\n{'='*50}")
        print(f"VERIFICATION COMPLETE: {args.domain}")
        print(f"{'='*50}")
        print(f"Pages crawled: {result['pages_crawled']}")
        print(f"Internal links: {result['internal_links']}")
        print(f"External links: {result['external_links']}")
        print(f"Broken internal: {result['broken_internal']}")
        print(f"Broken external: {result['broken_external']}")
        print(f"Report: {result['report_dir']}/report.md")

        if args.notify:
            msg = (
                f"Link Verification: {args.domain}\n"
                f"Pages: {result['pages_crawled']}\n"
                f"Broken: {result['broken_internal']} internal, {result['broken_external']} external\n"
                f"Report: {result['report_dir']}"
            )
            send_telegram(msg)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.exception(f"Error verifying {args.domain}")
        sys.exit(1)


if __name__ == '__main__':
    main()
