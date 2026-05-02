#!/usr/bin/env python3
"""
WordPress Database Cleanup Tool
Cleans transients, revisions, spam, and orphaned data.
Requires: MySQL/MariaDB connection or WP-CLI
"""

import argparse
import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.END}"


def run_wp_cli(cmd: str, path: str = ".") -> tuple:
    """Run WP-CLI command and return output"""
    full_cmd = f"wp {cmd} --path={path}"
    try:
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1


def check_wp_cli() -> bool:
    """Check if WP-CLI is available"""
    try:
        result = subprocess.run(
            "wp --version",
            shell=True,
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except:
        return False


def get_db_stats(path: str) -> dict:
    """Get database statistics"""
    stats = {
        "transients": 0,
        "expired_transients": 0,
        "revisions": 0,
        "auto_drafts": 0,
        "trashed_posts": 0,
        "spam_comments": 0,
        "trashed_comments": 0,
        "orphaned_postmeta": 0,
        "orphaned_commentmeta": 0,
        "orphaned_term_relationships": 0,
    }

    # Count transients
    out, _, _ = run_wp_cli("db query \"SELECT COUNT(*) FROM wp_options WHERE option_name LIKE '_transient_%'\" --skip-column-names", path)
    try:
        stats["transients"] = int(out.strip())
    except:
        pass

    # Count expired transients
    out, _, _ = run_wp_cli("transient list --expired --format=count", path)
    try:
        stats["expired_transients"] = int(out.strip())
    except:
        pass

    # Count revisions
    out, _, _ = run_wp_cli("db query \"SELECT COUNT(*) FROM wp_posts WHERE post_type = 'revision'\" --skip-column-names", path)
    try:
        stats["revisions"] = int(out.strip())
    except:
        pass

    # Count auto-drafts
    out, _, _ = run_wp_cli("db query \"SELECT COUNT(*) FROM wp_posts WHERE post_status = 'auto-draft'\" --skip-column-names", path)
    try:
        stats["auto_drafts"] = int(out.strip())
    except:
        pass

    # Count trashed posts
    out, _, _ = run_wp_cli("db query \"SELECT COUNT(*) FROM wp_posts WHERE post_status = 'trash'\" --skip-column-names", path)
    try:
        stats["trashed_posts"] = int(out.strip())
    except:
        pass

    # Count spam comments
    out, _, _ = run_wp_cli("db query \"SELECT COUNT(*) FROM wp_comments WHERE comment_approved = 'spam'\" --skip-column-names", path)
    try:
        stats["spam_comments"] = int(out.strip())
    except:
        pass

    # Count trashed comments
    out, _, _ = run_wp_cli("db query \"SELECT COUNT(*) FROM wp_comments WHERE comment_approved = 'trash'\" --skip-column-names", path)
    try:
        stats["trashed_comments"] = int(out.strip())
    except:
        pass

    return stats


def cleanup_transients(path: str, dry_run: bool = True) -> int:
    """Delete expired transients"""
    if dry_run:
        out, _, _ = run_wp_cli("transient list --expired --format=count", path)
        try:
            return int(out.strip())
        except:
            return 0

    out, err, code = run_wp_cli("transient delete --expired --all", path)
    if code == 0:
        # Count what was deleted
        match = out.strip()
        return 1 if "Success" in match else 0
    return 0


def cleanup_revisions(path: str, keep: int = 5, dry_run: bool = True) -> int:
    """Delete old post revisions, keeping last N per post"""
    if dry_run:
        out, _, _ = run_wp_cli(
            f"db query \"SELECT COUNT(*) FROM wp_posts WHERE post_type = 'revision'\" --skip-column-names",
            path
        )
        try:
            return int(out.strip())
        except:
            return 0

    # Get posts with revisions
    out, _, _ = run_wp_cli(
        "db query \"SELECT DISTINCT post_parent FROM wp_posts WHERE post_type = 'revision' AND post_parent > 0\" --skip-column-names",
        path
    )

    deleted = 0
    for post_id in out.strip().split('\n'):
        if not post_id.strip():
            continue

        # Get revision IDs to delete (all except last N)
        query = f"""
        SELECT ID FROM wp_posts
        WHERE post_type = 'revision' AND post_parent = {post_id}
        ORDER BY post_date DESC
        LIMIT 999999 OFFSET {keep}
        """
        rev_out, _, _ = run_wp_cli(f'db query "{query}" --skip-column-names', path)

        for rev_id in rev_out.strip().split('\n'):
            if rev_id.strip():
                run_wp_cli(f"post delete {rev_id} --force", path)
                deleted += 1

    return deleted


def cleanup_spam(path: str, dry_run: bool = True) -> int:
    """Delete spam comments"""
    if dry_run:
        out, _, _ = run_wp_cli(
            "db query \"SELECT COUNT(*) FROM wp_comments WHERE comment_approved = 'spam'\" --skip-column-names",
            path
        )
        try:
            return int(out.strip())
        except:
            return 0

    out, _, code = run_wp_cli("comment delete $(wp comment list --status=spam --format=ids) --force", path)
    return 0 if code != 0 else 1


def cleanup_trash(path: str, dry_run: bool = True) -> dict:
    """Delete trashed posts and comments"""
    result = {"posts": 0, "comments": 0}

    if dry_run:
        out, _, _ = run_wp_cli(
            "db query \"SELECT COUNT(*) FROM wp_posts WHERE post_status = 'trash'\" --skip-column-names",
            path
        )
        try:
            result["posts"] = int(out.strip())
        except:
            pass

        out, _, _ = run_wp_cli(
            "db query \"SELECT COUNT(*) FROM wp_comments WHERE comment_approved = 'trash'\" --skip-column-names",
            path
        )
        try:
            result["comments"] = int(out.strip())
        except:
            pass

        return result

    # Delete trashed posts
    run_wp_cli("post delete $(wp post list --post_status=trash --format=ids) --force", path)

    # Delete trashed comments
    run_wp_cli("comment delete $(wp comment list --status=trash --format=ids) --force", path)

    return result


def cleanup_orphaned(path: str, dry_run: bool = True) -> dict:
    """Delete orphaned meta entries"""
    result = {"postmeta": 0, "commentmeta": 0, "termmeta": 0}

    queries = {
        "postmeta": """
            SELECT COUNT(*) FROM wp_postmeta pm
            LEFT JOIN wp_posts p ON pm.post_id = p.ID
            WHERE p.ID IS NULL
        """,
        "commentmeta": """
            SELECT COUNT(*) FROM wp_commentmeta cm
            LEFT JOIN wp_comments c ON cm.comment_id = c.comment_ID
            WHERE c.comment_ID IS NULL
        """,
        "termmeta": """
            SELECT COUNT(*) FROM wp_termmeta tm
            LEFT JOIN wp_terms t ON tm.term_id = t.term_id
            WHERE t.term_id IS NULL
        """
    }

    delete_queries = {
        "postmeta": """
            DELETE pm FROM wp_postmeta pm
            LEFT JOIN wp_posts p ON pm.post_id = p.ID
            WHERE p.ID IS NULL
        """,
        "commentmeta": """
            DELETE cm FROM wp_commentmeta cm
            LEFT JOIN wp_comments c ON cm.comment_id = c.comment_ID
            WHERE c.comment_ID IS NULL
        """,
        "termmeta": """
            DELETE tm FROM wp_termmeta tm
            LEFT JOIN wp_terms t ON tm.term_id = t.term_id
            WHERE t.term_id IS NULL
        """
    }

    for key, query in queries.items():
        out, _, _ = run_wp_cli(f'db query "{query}" --skip-column-names', path)
        try:
            result[key] = int(out.strip())
        except:
            pass

    if not dry_run:
        for key, query in delete_queries.items():
            run_wp_cli(f'db query "{query}"', path)

    return result


def optimize_tables(path: str) -> bool:
    """Optimize WordPress database tables"""
    out, err, code = run_wp_cli("db optimize", path)
    return code == 0


def get_autoload_analysis(path: str) -> list:
    """Analyze autoloaded options"""
    query = """
        SELECT option_name, LENGTH(option_value) as size
        FROM wp_options
        WHERE autoload = 'yes'
        ORDER BY size DESC
        LIMIT 20
    """
    out, _, _ = run_wp_cli(f'db query "{query}"', path)

    results = []
    for line in out.strip().split('\n')[1:]:  # Skip header
        parts = line.split('\t')
        if len(parts) >= 2:
            try:
                results.append({
                    "option": parts[0],
                    "size": int(parts[1])
                })
            except:
                pass

    return results


def main():
    parser = argparse.ArgumentParser(description='WordPress Database Cleanup Tool')
    parser.add_argument('path', nargs='?', default='.', help='Path to WordPress installation')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without doing it')
    parser.add_argument('--all', action='store_true', help='Run all cleanup operations')
    parser.add_argument('--transients', action='store_true', help='Delete expired transients')
    parser.add_argument('--revisions', action='store_true', help='Delete old revisions')
    parser.add_argument('--keep-revisions', type=int, default=5, help='Number of revisions to keep per post')
    parser.add_argument('--spam', action='store_true', help='Delete spam comments')
    parser.add_argument('--trash', action='store_true', help='Empty trash')
    parser.add_argument('--orphaned', action='store_true', help='Delete orphaned meta')
    parser.add_argument('--optimize', action='store_true', help='Optimize database tables')
    parser.add_argument('--analyze', action='store_true', help='Analyze autoloaded options')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    # Check WP-CLI
    if not check_wp_cli():
        print(f"{color('Error:', Colors.RED)} WP-CLI is not installed or not in PATH")
        print("Install WP-CLI: https://wp-cli.org/#installing")
        sys.exit(1)

    # Verify WordPress installation
    out, err, code = run_wp_cli("core is-installed", args.path)
    if code != 0:
        print(f"{color('Error:', Colors.RED)} Not a valid WordPress installation: {args.path}")
        sys.exit(1)

    results = {
        "path": args.path,
        "timestamp": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "operations": {}
    }

    if args.dry_run:
        print(f"{color('DRY RUN MODE', Colors.YELLOW)} - No changes will be made\n")

    print(f"{color('WordPress Database Cleanup', Colors.BOLD)}")
    print(f"Path: {args.path}\n")

    # Show current stats
    print(f"{color('## Current Database Stats', Colors.BOLD)}")
    stats = get_db_stats(args.path)
    for key, value in stats.items():
        label = key.replace('_', ' ').title()
        print(f"  {label}: {value}")
    print()

    results["stats_before"] = stats

    # Run operations
    if args.all or args.transients:
        print(f"{color('## Transients', Colors.BOLD)}")
        count = cleanup_transients(args.path, args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"  {action} expired transients: {count}")
        results["operations"]["transients"] = count
        print()

    if args.all or args.revisions:
        print(f"{color('## Revisions', Colors.BOLD)}")
        count = cleanup_revisions(args.path, args.keep_revisions, args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"  {action} revisions (keeping {args.keep_revisions} per post): {count}")
        results["operations"]["revisions"] = count
        print()

    if args.all or args.spam:
        print(f"{color('## Spam Comments', Colors.BOLD)}")
        count = cleanup_spam(args.path, args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"  {action} spam comments: {stats['spam_comments']}")
        results["operations"]["spam"] = stats["spam_comments"]
        print()

    if args.all or args.trash:
        print(f"{color('## Trash', Colors.BOLD)}")
        trash = cleanup_trash(args.path, args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"  {action} trashed posts: {trash['posts']}")
        print(f"  {action} trashed comments: {trash['comments']}")
        results["operations"]["trash"] = trash
        print()

    if args.all or args.orphaned:
        print(f"{color('## Orphaned Data', Colors.BOLD)}")
        orphaned = cleanup_orphaned(args.path, args.dry_run)
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"  {action} orphaned postmeta: {orphaned['postmeta']}")
        print(f"  {action} orphaned commentmeta: {orphaned['commentmeta']}")
        print(f"  {action} orphaned termmeta: {orphaned['termmeta']}")
        results["operations"]["orphaned"] = orphaned
        print()

    if args.optimize and not args.dry_run:
        print(f"{color('## Optimize Tables', Colors.BOLD)}")
        success = optimize_tables(args.path)
        print(f"  Database optimization: {'Success' if success else 'Failed'}")
        results["operations"]["optimize"] = success
        print()

    if args.analyze:
        print(f"{color('## Autoloaded Options Analysis', Colors.BOLD)}")
        autoload = get_autoload_analysis(args.path)
        total_size = sum(a["size"] for a in autoload)
        print(f"  Total autoloaded size: {total_size / 1024:.1f} KB")
        print(f"  Top 10 largest autoloaded options:")
        for item in autoload[:10]:
            size_kb = item["size"] / 1024
            print(f"    {item['option']}: {size_kb:.1f} KB")
        results["autoload_analysis"] = autoload
        print()

    if args.json:
        print(json.dumps(results, indent=2))

    if args.dry_run:
        print(f"\n{color('To apply changes, run without --dry-run', Colors.YELLOW)}")


if __name__ == "__main__":
    main()
