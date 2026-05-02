#!/usr/bin/env python3
"""
RSS News Aggregator Skill
Manage 50+ news feeds, scrape, and publish to Telegram/WordPress/Facebook.

Usage:
    python3 rss_news.py status              # Show dashboard
    python3 rss_news.py scrape              # Scrape all feeds
    python3 rss_news.py scrape --feed BBC   # Scrape single feed
    python3 rss_news.py publish [N]         # Publish N articles to Telegram
    python3 rss_news.py publish --dry-run   # Preview without posting
"""

import argparse
import subprocess
import sys
import os

RSS_DIR = "/opt/ACTIVE/WEB/RSS"
SCRAPER = os.path.join(RSS_DIR, "rss_scraper.py")
PUBLISHER = os.path.join(RSS_DIR, "rss_publisher.py")


def run_cmd(cmd):
    """Run command and return output."""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=RSS_DIR)
    return result.stdout + result.stderr


def status():
    """Show RSS dashboard."""
    print("=== RSS News Aggregator ===\n")

    # Scraper status
    print("--- Feed Status ---")
    output = run_cmd(["python3", SCRAPER, "--status"])
    print(output)

    # Publisher status
    print("\n--- Publishing Status ---")
    output = run_cmd(["python3", PUBLISHER, "--status"])
    print(output)


def scrape(feed=None, verbose=False):
    """Scrape RSS feeds."""
    cmd = ["python3", SCRAPER]
    if feed:
        cmd.extend(["--feed", feed])
    if verbose:
        cmd.append("-v")

    print(f"Scraping {'feed: ' + feed if feed else 'all feeds'}...")
    result = subprocess.run(cmd, cwd=RSS_DIR)
    return result.returncode


def publish(limit=10, dry_run=False, platform="telegram"):
    """Publish articles to platform."""
    cmd = ["python3", PUBLISHER, f"--{platform}", "--limit", str(limit)]
    if dry_run:
        cmd.append("--dry-run")

    print(f"Publishing {limit} articles to {platform}{'(dry-run)' if dry_run else ''}...")
    result = subprocess.run(cmd, cwd=RSS_DIR)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="RSS News Aggregator Skill")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status
    subparsers.add_parser("status", help="Show dashboard")

    # scrape
    scrape_parser = subparsers.add_parser("scrape", help="Scrape feeds")
    scrape_parser.add_argument("--feed", help="Scrape single feed by name")
    scrape_parser.add_argument("-v", "--verbose", action="store_true")

    # publish
    publish_parser = subparsers.add_parser("publish", help="Publish articles")
    publish_parser.add_argument("limit", type=int, nargs="?", default=10, help="Number of articles")
    publish_parser.add_argument("--dry-run", action="store_true", help="Preview only")
    publish_parser.add_argument("--platform", default="telegram", choices=["telegram", "wordpress", "facebook", "all"])

    args = parser.parse_args()

    if args.command == "status" or not args.command:
        status()
    elif args.command == "scrape":
        scrape(args.feed, args.verbose)
    elif args.command == "publish":
        publish(args.limit, args.dry_run, args.platform)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
