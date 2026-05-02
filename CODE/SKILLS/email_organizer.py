#!/usr/bin/env python3
"""
Email Organizer - Fetch, classify, and suggest responses using LLM.

Fetches emails from configured Gmail accounts, classifies them,
and suggests appropriate responses using LM Studio.

Usage:
    python3 email_organizer.py                    # Check all accounts
    python3 email_organizer.py --account EMAIL    # Check specific account
    python3 email_organizer.py --days 3           # Last 3 days
    python3 email_organizer.py --limit 20         # Max 20 emails
"""

import os
import sys
import json
import imaplib
import email
import httpx
from email.header import decode_header
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii
from dotenv import load_dotenv

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# LM Studio endpoint
LLM_URL = "http://localhost:1234/v1/chat/completions"

# Email accounts to check
ACCOUNTS = [
    {'email': 'manpowerdristor@gmail.com', 'password_env': 'GMAIL_APP_PASSWORD', 'name': 'Manpower Main'},
    {'email': 'elena.manpower.dristor@gmail.com', 'password_env': 'GMAIL_ELENA_PASSWORD', 'name': 'Elena'},
    {'email': 'expatsinromania@gmail.com', 'password_env': 'GMAIL_EXPATS_PASSWORD', 'name': 'Expats'},
]

# Categories for classification
CATEGORIES = {
    'JOB_INQUIRY': 'Job seeker asking about positions',
    'COMPANY_REPLY': 'Company replying to our outreach',
    'UNSUBSCRIBE': 'Unsubscribe/STOP request',
    'BOUNCE': 'Bounce/delivery failure',
    'SPAM': 'Spam or irrelevant',
    'CV_APPLICATION': 'CV/application submission',
    'POSITIVE_INTEREST': 'Positive interest from company',
    'NEGATIVE_REPLY': 'Not interested / rejection',
    'QUESTION': 'Question needing answer',
    'OTHER': 'Other/unclear',
}


def decode_mime_header(header):
    """Decode MIME encoded header."""
    if not header:
        return ""
    decoded = decode_header(header)
    parts = []
    for data, charset in decoded:
        if isinstance(data, bytes):
            parts.append(data.decode(charset or 'utf-8', errors='ignore'))
        else:
            parts.append(str(data))
    return ' '.join(parts)


def get_email_body(msg):
    """Extract plain text body from email."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        body = payload.decode(charset, errors='ignore')
                        break
                except:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                body = payload.decode(charset, errors='ignore')
        except:
            pass
    return body[:2000]  # Limit body length


def fetch_emails(account, days=7, limit=50):
    """Fetch recent emails from account."""
    emails = []

    password = os.getenv(account['password_env'])
    if not password:
        print(f"  No password for {account['email']}")
        return emails

    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(account['email'], password)
        imap.select("INBOX")

        # Search for recent emails
        since_date = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
        _, message_ids = imap.search(None, f'(SINCE "{since_date}")')

        ids = message_ids[0].split()[-limit:]  # Get last N emails

        for msg_id in ids:
            _, msg_data = imap.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    from_header = msg.get("From", "")
                    from_email = ""
                    from_name = ""
                    if '<' in from_header:
                        from_name = from_header.split('<')[0].strip().strip('"')
                        from_email = from_header.split('<')[1].rstrip('>')
                    else:
                        from_email = from_header

                    emails.append({
                        'id': msg_id.decode(),
                        'from_email': from_email.lower(),
                        'from_name': to_ascii(decode_mime_header(from_name)),
                        'subject': to_ascii(decode_mime_header(msg.get("Subject", ""))),
                        'date': msg.get("Date", ""),
                        'body': to_ascii(get_email_body(msg)),
                        'account': account['email'],
                    })

        imap.logout()
    except Exception as e:
        print(f"  Error fetching from {account['email']}: {e}")

    return emails


def classify_with_llm(email_data):
    """Classify email using LM Studio."""
    categories_str = "\n".join([f"- {k}: {v}" for k, v in CATEGORIES.items()])

    prompt = f"""Classify this email into one of these categories:
{categories_str}

Email:
From: {email_data['from_name']} <{email_data['from_email']}>
Subject: {email_data['subject']}
Body: {email_data['body'][:500]}

Respond with JSON only:
{{"category": "CATEGORY_NAME", "priority": "high/medium/low", "summary": "brief summary", "suggested_action": "what to do"}}"""

    try:
        response = httpx.post(
            LLM_URL,
            json={
                "model": "local-model",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
            },
            timeout=30.0
        )

        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            # Extract JSON from response
            try:
                # Find JSON in response
                start = content.find('{')
                end = content.rfind('}') + 1
                if start >= 0 and end > start:
                    return json.loads(content[start:end])
            except:
                pass
    except Exception as e:
        pass

    return {"category": "OTHER", "priority": "medium", "summary": "Could not classify", "suggested_action": "Review manually"}


def suggest_response(email_data, classification):
    """Generate response suggestion using LLM."""
    if classification['category'] in ['SPAM', 'BOUNCE']:
        return None

    prompt = f"""Write a brief professional response to this email in the same language as the original.
Keep it short (2-3 sentences).

Email:
From: {email_data['from_name']}
Subject: {email_data['subject']}
Body: {email_data['body'][:300]}

Classification: {classification['category']}

Write ONLY the response text, no greeting or signature (those will be added automatically):"""

    try:
        response = httpx.post(
            LLM_URL,
            json={
                "model": "local-model",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 150,
            },
            timeout=30.0
        )

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content'].strip()
    except:
        pass

    return None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', type=str, help='Specific account to check')
    parser.add_argument('--days', type=int, default=3, help='Days to look back')
    parser.add_argument('--limit', type=int, default=30, help='Max emails per account')
    parser.add_argument('--no-llm', action='store_true', help='Skip LLM classification')
    args = parser.parse_args()

    print("=" * 70)
    print("EMAIL ORGANIZER")
    print("=" * 70)
    print(f"Days: {args.days} | Limit: {args.limit}/account")
    print()

    # Check LLM availability
    llm_available = False
    if not args.no_llm:
        try:
            r = httpx.get("http://localhost:1234/v1/models", timeout=5.0)
            llm_available = r.status_code == 200
        except:
            pass

    if llm_available:
        print("LLM: Available (LM Studio)")
    else:
        print("LLM: Not available - basic classification only")
    print()

    # Select accounts
    accounts = ACCOUNTS
    if args.account:
        accounts = [a for a in ACCOUNTS if args.account in a['email']]
        if not accounts:
            print(f"Account not found: {args.account}")
            return

    # Fetch emails
    all_emails = []
    for account in accounts:
        print(f"Fetching: {account['name']} ({account['email']})...")
        emails = fetch_emails(account, days=args.days, limit=args.limit)
        print(f"  Found: {len(emails)} emails")
        all_emails.extend(emails)

    if not all_emails:
        print("\nNo emails found.")
        return

    print(f"\nTotal emails: {len(all_emails)}")
    print()

    # Classify emails
    classified = {'high': [], 'medium': [], 'low': []}

    for i, em in enumerate(all_emails):
        print(f"Processing {i+1}/{len(all_emails)}: {em['subject'][:40]}...", end=" ")

        if llm_available:
            classification = classify_with_llm(em)
        else:
            # Basic classification
            subject_lower = em['subject'].lower()
            body_lower = em['body'].lower()

            if any(w in subject_lower for w in ['unsubscribe', 'stop', 'dezabonare']):
                classification = {"category": "UNSUBSCRIBE", "priority": "high", "summary": "Unsubscribe request", "suggested_action": "Remove from list"}
            elif any(w in subject_lower for w in ['delivery', 'undeliverable', 'failure', 'bounce']):
                classification = {"category": "BOUNCE", "priority": "low", "summary": "Delivery failure", "suggested_action": "Add to blacklist"}
            elif any(w in body_lower for w in ['cv', 'resume', 'aplicatie', 'candidatura']):
                classification = {"category": "CV_APPLICATION", "priority": "high", "summary": "Job application", "suggested_action": "Review CV"}
            elif any(w in body_lower for w in ['interesat', 'interested', 'da', 'yes', 'acceptam']):
                classification = {"category": "POSITIVE_INTEREST", "priority": "high", "summary": "Positive response", "suggested_action": "Follow up"}
            elif any(w in body_lower for w in ['nu', 'no', 'not interested', 'nu avem nevoie']):
                classification = {"category": "NEGATIVE_REPLY", "priority": "low", "summary": "Not interested", "suggested_action": "Mark as closed"}
            else:
                classification = {"category": "OTHER", "priority": "medium", "summary": "Needs review", "suggested_action": "Review manually"}

        em['classification'] = classification

        # Get response suggestion for important emails
        if llm_available and classification['priority'] == 'high' and classification['category'] not in ['BOUNCE', 'SPAM']:
            em['suggested_response'] = suggest_response(em, classification)

        print(f"[{classification['category']}]")

        classified[classification['priority']].append(em)

    # Display results
    print("\n" + "=" * 70)
    print("RESULTS BY PRIORITY")
    print("=" * 70)

    for priority in ['high', 'medium', 'low']:
        emails = classified[priority]
        if emails:
            print(f"\n### {priority.upper()} PRIORITY ({len(emails)}) ###\n")
            for em in emails:
                c = em['classification']
                print(f"From: {em['from_email']}")
                print(f"Subject: {em['subject'][:60]}")
                print(f"Category: {c['category']} | Action: {c['suggested_action']}")
                if em.get('suggested_response'):
                    print(f"Suggested response: {em['suggested_response'][:100]}...")
                print("-" * 50)

    # Summary by category
    print("\n" + "=" * 70)
    print("SUMMARY BY CATEGORY")
    print("=" * 70)

    by_category = {}
    for em in all_emails:
        cat = em['classification']['category']
        by_category.setdefault(cat, []).append(em)

    for cat, emails in sorted(by_category.items(), key=lambda x: -len(x[1])):
        print(f"{cat}: {len(emails)}")

    # Save results
    output_file = Path('/tmp/email_organizer_results.json')
    with open(output_file, 'w') as f:
        json.dump(all_emails, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")


if __name__ == '__main__':
    main()
