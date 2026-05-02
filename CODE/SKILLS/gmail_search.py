#!/usr/bin/env python3
"""
Gmail Search Skill - Search emails via IMAP

Usage:
    python3 gmail_search.py "keyword1 keyword2" [--from sender] [--after YYYY-MM-DD] [--before YYYY-MM-DD]
    python3 gmail_search.py --query "ministerul agriculturii" --from madr.ro
    python3 gmail_search.py --query "distribuitori ingrasaminte" --has-attachment
    python3 gmail_search.py --interactive

Examples:
    # Search for ministry emails about fertilizers
    python3 gmail_search.py "distribuitori ingrasaminte autorizati"
    python3 gmail_search.py --query "directia agricola" --from agricultura
    python3 gmail_search.py --query "fertilizanti" --has-attachment --after 2024-01-01
"""
import imaplib
import email
import email.header
import re
import sys
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except ImportError:
    import unicodedata
    def to_ascii(text):
        if not text:
            return text
        normalized = unicodedata.normalize('NFKD', str(text))
        return normalized.encode('ascii', 'ignore').decode('ascii')

# Gmail credentials - load from .env
from dotenv import load_dotenv
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

GMAIL_USER = os.getenv('GMAIL_SEARCH_USER') or os.getenv('GMAIL_USER', 'fruitnature4@gmail.com')
GMAIL_PASS = os.getenv('GMAIL_SEARCH_PASSWORD') or os.getenv('GMAIL_PASS', 'flzd mxvp hltu fzbv')


def decode_header_value(header_value: str) -> str:
    """Decode email header value (handles encoded subjects/names)."""
    if not header_value:
        return ""
    decoded_parts = []
    for part, encoding in email.header.decode_header(header_value):
        if isinstance(part, bytes):
            decoded_parts.append(part.decode(encoding or 'utf-8', errors='ignore'))
        else:
            decoded_parts.append(part)
    return ' '.join(decoded_parts)


def get_email_body(msg) -> str:
    """Extract plain text body from email message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body += payload.decode(charset, errors='ignore')
                except Exception:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
        except Exception:
            pass
    return body


def has_attachments(msg) -> List[str]:
    """Check for attachments and return list of filenames."""
    attachments = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            filename = part.get_filename()
            if filename:
                attachments.append(decode_header_value(filename))
    return attachments


def build_imap_search(keywords: List[str] = None,
                      from_addr: str = None,
                      after_date: str = None,
                      before_date: str = None,
                      has_attachment: bool = False,
                      subject_only: bool = False) -> str:
    """Build IMAP search query string."""
    criteria = []

    if from_addr:
        criteria.append(f'FROM "{from_addr}"')

    if after_date:
        # IMAP date format: DD-Mon-YYYY
        try:
            dt = datetime.strptime(after_date, '%Y-%m-%d')
            criteria.append(f'SINCE {dt.strftime("%d-%b-%Y")}')
        except ValueError:
            pass

    if before_date:
        try:
            dt = datetime.strptime(before_date, '%Y-%m-%d')
            criteria.append(f'BEFORE {dt.strftime("%d-%b-%Y")}')
        except ValueError:
            pass

    # Keywords - search in subject or body
    if keywords:
        for kw in keywords:
            if subject_only:
                criteria.append(f'SUBJECT "{kw}"')
            else:
                # OR search in subject and body
                criteria.append(f'OR SUBJECT "{kw}" BODY "{kw}"')

    if not criteria:
        criteria.append('ALL')

    return ' '.join(criteria)


def search_gmail(query: str = None,
                keywords: List[str] = None,
                from_addr: str = None,
                after_date: str = None,
                before_date: str = None,
                has_attachment: bool = False,
                subject_only: bool = False,
                folder: str = "INBOX",
                limit: int = 50,
                show_body: bool = False) -> List[Dict]:
    """
    Search Gmail via IMAP.

    Args:
        query: Simple keyword string (split by spaces)
        keywords: List of keywords to search
        from_addr: Filter by sender (partial match)
        after_date: Search after date (YYYY-MM-DD)
        before_date: Search before date (YYYY-MM-DD)
        has_attachment: Only return emails with attachments
        subject_only: Search only in subject line
        folder: IMAP folder to search (default INBOX)
        limit: Maximum results to return
        show_body: Include email body in results

    Returns:
        List of email dicts with subject, from, date, attachments
    """
    results = []

    # Parse query string into keywords
    if query and not keywords:
        keywords = query.split()

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)

        # Select folder
        mail.select(folder, readonly=True)

        # Build and execute search
        search_query = build_imap_search(
            keywords=keywords,
            from_addr=from_addr,
            after_date=after_date,
            before_date=before_date,
            has_attachment=has_attachment,
            subject_only=subject_only
        )

        print(f"IMAP search: {search_query}")

        # Try search
        try:
            _, message_nums = mail.search(None, search_query)
        except imaplib.IMAP4.error:
            # Fallback to simpler search if complex query fails
            if keywords:
                _, message_nums = mail.search(None, f'BODY "{keywords[0]}"')
            else:
                _, message_nums = mail.search(None, 'ALL')

        if not message_nums[0]:
            print("No messages found")
            mail.logout()
            return results

        # Get message IDs (most recent first)
        msg_ids = message_nums[0].split()
        msg_ids = list(reversed(msg_ids))[:limit]

        print(f"Found {len(message_nums[0].split())} messages, processing {len(msg_ids)}")

        for num in msg_ids:
            try:
                _, data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])

                subject = decode_header_value(msg.get("Subject", ""))
                from_header = decode_header_value(msg.get("From", ""))
                date_str = msg.get("Date", "")
                attachments = has_attachments(msg)

                # Filter by attachment if requested
                if has_attachment and not attachments:
                    continue

                # Secondary keyword filter (IMAP search can be imprecise)
                if keywords:
                    body = get_email_body(msg).lower()
                    subject_lower = subject.lower()
                    matched = False
                    for kw in keywords:
                        kw_lower = kw.lower()
                        if kw_lower in subject_lower or kw_lower in body:
                            matched = True
                            break
                    if not matched:
                        continue

                result = {
                    'subject': to_ascii(subject)[:100],
                    'from': to_ascii(from_header)[:80],
                    'date': date_str[:30],
                    'attachments': [to_ascii(a) for a in attachments],
                    'message_id': msg.get("Message-ID", "")
                }

                if show_body:
                    body = get_email_body(msg)
                    result['body'] = to_ascii(body)[:2000]

                results.append(result)

            except Exception as e:
                print(f"Error processing message: {e}")
                continue

        mail.logout()

    except imaplib.IMAP4.error as e:
        print(f"IMAP error: {e}")
    except Exception as e:
        print(f"Error: {e}")

    return results


def search_ministry_agriculture(keywords: List[str] = None) -> List[Dict]:
    """
    Specialized search for Ministry of Agriculture / Directia Agricola emails.

    Searches for:
    - Ministerul Agriculturii (MADR)
    - Directia Agricola Judeteana (DAJ)
    - Keywords: distribuitori, ingrasaminte, fertilizanti, autorizati
    """
    default_keywords = [
        'ministerul agriculturii',
        'madr',
        'directia agricola',
        'daj',
        'distribuitori',
        'ingrasaminte',
        'fertilizanti',
        'autorizati',
        'ansvsa'
    ]

    if keywords:
        search_terms = keywords
    else:
        search_terms = default_keywords[:3]  # Start with main terms

    # Search with ministry-related senders
    ministry_domains = ['madr.ro', 'agricultura', 'ansvsa.ro', 'gov.ro']

    all_results = []

    # First search by domain
    for domain in ministry_domains:
        results = search_gmail(
            from_addr=domain,
            keywords=search_terms,
            limit=20
        )
        all_results.extend(results)

    # Then search by keywords only (broader)
    results = search_gmail(
        keywords=['distribuitori ingrasaminte', 'fertilizanti autorizati'],
        has_attachment=True,
        limit=30
    )
    all_results.extend(results)

    # Deduplicate by message_id
    seen = set()
    unique_results = []
    for r in all_results:
        mid = r.get('message_id', r['subject'])
        if mid not in seen:
            seen.add(mid)
            unique_results.append(r)

    return unique_results


def interactive_search():
    """Interactive search mode."""
    print("\n=== GMAIL SEARCH ===\n")
    print("Search your Gmail for specific emails.\n")

    query = input("Keywords (space-separated): ").strip()
    from_addr = input("From address/domain (optional): ").strip() or None
    after_date = input("After date YYYY-MM-DD (optional): ").strip() or None
    has_att = input("Has attachment? (y/n): ").strip().lower() == 'y'

    results = search_gmail(
        query=query,
        from_addr=from_addr,
        after_date=after_date,
        has_attachment=has_att,
        limit=20,
        show_body=False
    )

    print_results(results)
    return results


def print_results(results: List[Dict]):
    """Print search results in readable format."""
    if not results:
        print("\nNo results found.")
        return

    print(f"\n=== FOUND {len(results)} EMAILS ===\n")

    for i, r in enumerate(results, 1):
        print(f"{i}. {r['subject']}")
        print(f"   From: {r['from']}")
        print(f"   Date: {r['date']}")
        if r.get('attachments'):
            print(f"   Attachments: {', '.join(r['attachments'])}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Search Gmail via IMAP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "distribuitori ingrasaminte"
  %(prog)s --query "ministerul agriculturii" --from madr.ro
  %(prog)s --query "fertilizanti" --has-attachment
  %(prog)s --ministry  # Specialized ministry search
  %(prog)s --interactive
        """
    )

    parser.add_argument('query', nargs='?', help='Search keywords')
    parser.add_argument('--query', '-q', dest='query_opt', help='Search keywords (alternative)')
    parser.add_argument('--from', '-f', dest='from_addr', help='Filter by sender')
    parser.add_argument('--after', '-a', help='After date (YYYY-MM-DD)')
    parser.add_argument('--before', '-b', help='Before date (YYYY-MM-DD)')
    parser.add_argument('--has-attachment', action='store_true', help='Only emails with attachments')
    parser.add_argument('--subject-only', action='store_true', help='Search subject only')
    parser.add_argument('--limit', '-l', type=int, default=30, help='Max results (default 30)')
    parser.add_argument('--show-body', action='store_true', help='Include email body')
    parser.add_argument('--ministry', '-m', action='store_true', help='Search Ministry of Agriculture emails')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--folder', default='INBOX', help='IMAP folder (default INBOX)')

    args = parser.parse_args()

    if args.interactive:
        interactive_search()
        return

    if args.ministry:
        query = args.query or args.query_opt
        keywords = query.split() if query else None
        results = search_ministry_agriculture(keywords)
        print_results(results)
        return

    query = args.query or args.query_opt
    if not query and not args.from_addr:
        parser.print_help()
        print("\nError: Provide keywords or --from address")
        sys.exit(1)

    results = search_gmail(
        query=query,
        from_addr=args.from_addr,
        after_date=args.after,
        before_date=args.before,
        has_attachment=args.has_attachment,
        subject_only=args.subject_only,
        folder=args.folder,
        limit=args.limit,
        show_body=args.show_body
    )

    print_results(results)


if __name__ == "__main__":
    main()
