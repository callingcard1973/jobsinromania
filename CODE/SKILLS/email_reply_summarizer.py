#!/usr/bin/env python3
"""
Email Reply Summarizer - Uses Ollama to analyze and summarize campaign replies
Categorizes: INTERESTED, NOT_INTERESTED, AUTO_REPLY, BOUNCE, QUESTION, SPAM
"""

import imaplib
import email
import json
import requests
import sys
from email.header import decode_header
from datetime import datetime, timedelta
from pathlib import Path

# Gmail accounts to check
GMAIL_ACCOUNTS = [
    {'email': 'manpowerdristor@gmail.com', 'password': 'dmrsuqiudvqtrpzu', 'name': 'Manpower Dristor'},
    {'email': 'elena.manpower.dristor@gmail.com', 'password': 'wmfnpikkcierkmrq', 'name': 'Elena'},
]

# LM Studio API (OpenAI-compatible endpoint)
# Try localhost first, then Windows laptop
LMSTUDIO_ENDPOINTS = [
    "http://localhost:1234/v1/chat/completions",      # Local LM Studio
    "http://192.168.100.100:1234/v1/chat/completions", # Windows laptop
]
MODEL = "local-model"  # LM Studio uses whatever model is loaded

CACHE_FILE = Path("/tmp/email_reply_cache.json")

def decode_header_value(value):
    """Decode email header value."""
    if not value:
        return ""
    decoded = decode_header(value)
    parts = []
    for part, enc in decoded:
        if isinstance(part, bytes):
            parts.append(part.decode(enc or 'utf-8', errors='ignore'))
        else:
            parts.append(str(part))
    return ''.join(parts)

def get_body(msg):
    """Extract plain text body from email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
    try:
        return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    except:
        return ""

def is_auto_reply(subject, from_addr, body):
    """Quick check for auto-replies without LLM."""
    subject_lower = subject.lower()
    from_lower = from_addr.lower()
    body_lower = body.lower()[:500]

    auto_keywords = [
        'mailer-daemon', 'postmaster', 'noreply', 'no-reply', 'auto-reply',
        'autoreply', 'autosvar', 'automatic reply', 'out of office',
        'delivery status', 'undeliverable', 'failure notice', 'returned mail',
        'vacation', 'holiday', 'away from', 'be back', 'ikke tilgjengelig'
    ]

    for kw in auto_keywords:
        if kw in subject_lower or kw in from_lower or kw in body_lower:
            return True
    return False

def is_bounce(subject, from_addr, body):
    """Quick check for bounces."""
    indicators = ['delivery status notification', 'undeliverable', 'failed',
                  'rejected', 'address not found', 'message blocked']
    text = (subject + from_addr + body[:300]).lower()
    return any(ind in text for ind in indicators)

def classify_without_llm(from_addr, subject, body):
    """Fallback rule-based classifier when LM Studio unavailable."""
    text = (subject + ' ' + body).lower()

    # Interest indicators
    interested_keywords = ['interested', 'yes', 'send me', 'more info', 'contact me',
                          'call me', 'workers available', 'can provide', 'collaboration',
                          'partnership', 'da, suntem', 'avem disponibili', 'ne intereseaza']

    # Not interested indicators
    not_interested_keywords = ['not interested', 'no thank', 'unsubscribe', 'remove',
                              'stop sending', 'nu multumesc', 'nu ne intereseaza',
                              'please remove', 'gdpr', 'do not contact']

    # Question indicators
    question_keywords = ['?', 'how much', 'what is', 'when can', 'where are',
                        'cat costa', 'ce conditii', 'details', 'information']

    for kw in interested_keywords:
        if kw in text:
            return {"category": "INTERESTED", "summary": "Shows interest (keyword match)",
                   "action": "Reply with details", "language": "unknown", "urgency": "HIGH"}

    for kw in not_interested_keywords:
        if kw in text:
            return {"category": "NOT_INTERESTED", "summary": "Declined (keyword match)",
                   "action": "Remove from list", "language": "unknown", "urgency": "LOW"}

    for kw in question_keywords:
        if kw in text:
            return {"category": "QUESTION", "summary": "Has questions (keyword match)",
                   "action": "Answer questions", "language": "unknown", "urgency": "MEDIUM"}

    return {"category": "OTHER", "summary": "Needs manual review",
           "action": "Review and respond", "language": "unknown", "urgency": "MEDIUM"}

def summarize_with_lmstudio(from_addr, subject, body):
    """Use LM Studio to categorize and summarize the email."""
    # Truncate body to avoid token limits
    body_clean = body[:1500].replace('\r\n', '\n').strip()

    system_prompt = """You are an email analyzer for a recruitment agency. Analyze replies and respond ONLY with valid JSON, no other text."""

    user_prompt = f"""Analyze this email reply to a recruitment campaign.

FROM: {from_addr}
SUBJECT: {subject}

BODY:
{body_clean}

Respond in this exact JSON format only:
{{"category": "INTERESTED|NOT_INTERESTED|QUESTION|OTHER", "summary": "1-2 sentence summary", "action": "What to do next", "language": "detected language", "urgency": "HIGH|MEDIUM|LOW"}}"""

    # Try each endpoint
    for endpoint in LMSTUDIO_ENDPOINTS:
        try:
            response = requests.post(endpoint, json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 200
            }, timeout=30)

            if response.status_code == 200:
                result = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                # Try to parse JSON from response
                try:
                    start = result.find('{')
                    end = result.rfind('}') + 1
                    if start >= 0 and end > start:
                        return json.loads(result[start:end])
                except json.JSONDecodeError:
                    pass
                return {"category": "OTHER", "summary": result[:200], "action": "Review manually", "urgency": "LOW"}
        except requests.exceptions.ConnectionError:
            continue  # Try next endpoint
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            continue

    # Fallback to rule-based classification if LM Studio unavailable
    print("    (LM Studio unavailable, using rule-based classifier)")
    return classify_without_llm(from_addr, subject, body)

def fetch_replies(days=7, limit=50):
    """Fetch recent replies from all Gmail accounts."""
    all_replies = []

    for account in GMAIL_ACCOUNTS:
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com', timeout=30)
            mail.login(account['email'], account['password'])
            mail.select('INBOX')

            since = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
            _, msgs = mail.search(None, f'(SINCE {since})')

            if msgs[0]:
                ids = msgs[0].split()[-limit:]  # Last N messages

                for mid in ids:
                    _, data = mail.fetch(mid, '(RFC822)')
                    msg = email.message_from_bytes(data[0][1])

                    from_addr = decode_header_value(msg['From'])
                    subject = decode_header_value(msg['Subject'])
                    body = get_body(msg)
                    date = msg['Date']
                    msg_id = msg['Message-ID']

                    # Skip our own messages
                    if account['email'] in from_addr.lower():
                        continue

                    all_replies.append({
                        'inbox': account['name'],
                        'from': from_addr,
                        'subject': subject,
                        'body': body,
                        'date': date,
                        'msg_id': msg_id
                    })

            mail.logout()
        except Exception as e:
            print(f"Error with {account['email']}: {e}")

    return all_replies

def analyze_replies(replies, use_cache=True):
    """Analyze replies using quick checks and Ollama."""
    results = {
        'INTERESTED': [],
        'NOT_INTERESTED': [],
        'QUESTION': [],
        'AUTO_REPLY': [],
        'BOUNCE': [],
        'OTHER': []
    }

    # Load cache
    cache = {}
    if use_cache and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text())
        except:
            cache = {}

    for reply in replies:
        msg_id = reply.get('msg_id', '')

        # Check cache first
        if msg_id and msg_id in cache:
            cat = cache[msg_id].get('category', 'OTHER')
            results[cat].append({**reply, **cache[msg_id]})
            continue

        # Quick pre-filters
        if is_bounce(reply['subject'], reply['from'], reply['body']):
            analysis = {'category': 'BOUNCE', 'summary': 'Email delivery failed', 'action': 'Remove from list', 'urgency': 'LOW'}
        elif is_auto_reply(reply['subject'], reply['from'], reply['body']):
            analysis = {'category': 'AUTO_REPLY', 'summary': 'Automated response', 'action': 'Ignore', 'urgency': 'LOW'}
        else:
            # Use Ollama for real replies
            print(f"  Analyzing: {reply['from'][:40]}...")
            analysis = summarize_with_lmstudio(reply['from'], reply['subject'], reply['body'])

        # Map category
        cat = analysis.get('category', 'OTHER')
        if cat not in results:
            cat = 'OTHER'

        results[cat].append({**reply, **analysis})

        # Cache result
        if msg_id:
            cache[msg_id] = analysis

    # Save cache
    CACHE_FILE.write_text(json.dumps(cache, indent=2, default=str))

    return results

def print_summary(results):
    """Print actionable summary."""
    print("\n" + "="*70)
    print("EMAIL REPLY SUMMARY - ACTION REQUIRED")
    print("="*70)

    # INTERESTED - High priority
    if results['INTERESTED']:
        print(f"\n🟢 INTERESTED ({len(results['INTERESTED'])}) - RESPOND ASAP:")
        print("-"*60)
        for r in results['INTERESTED']:
            print(f"  From: {r['from'][:50]}")
            print(f"  Summary: {r.get('summary', 'N/A')}")
            print(f"  Action: {r.get('action', 'Reply')}")
            print(f"  Urgency: {r.get('urgency', 'MEDIUM')}")
            print()

    # QUESTIONS - Medium priority
    if results['QUESTION']:
        print(f"\n🟡 QUESTIONS ({len(results['QUESTION'])}) - CLARIFY:")
        print("-"*60)
        for r in results['QUESTION']:
            print(f"  From: {r['from'][:50]}")
            print(f"  Summary: {r.get('summary', 'N/A')}")
            print(f"  Action: {r.get('action', 'Answer question')}")
            print()

    # NOT INTERESTED - Low priority
    if results['NOT_INTERESTED']:
        print(f"\n🔴 NOT INTERESTED ({len(results['NOT_INTERESTED'])}):")
        print("-"*60)
        for r in results['NOT_INTERESTED'][:5]:  # Show max 5
            print(f"  {r['from'][:40]}: {r.get('summary', 'Declined')[:60]}")
        if len(results['NOT_INTERESTED']) > 5:
            print(f"  ... and {len(results['NOT_INTERESTED'])-5} more")

    # Stats
    print(f"\n📊 STATS:")
    print(f"  Auto-replies: {len(results['AUTO_REPLY'])}")
    print(f"  Bounces: {len(results['BOUNCE'])}")
    print(f"  Other: {len(results['OTHER'])}")

    total = sum(len(v) for v in results.values())
    actionable = len(results['INTERESTED']) + len(results['QUESTION'])
    print(f"\n  Total: {total} | Actionable: {actionable}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Email Reply Summarizer')
    parser.add_argument('--days', type=int, default=7, help='Days to look back')
    parser.add_argument('--limit', type=int, default=30, help='Max emails per inbox')
    parser.add_argument('--no-cache', action='store_true', help='Ignore cache')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    print("Fetching replies...")
    replies = fetch_replies(days=args.days, limit=args.limit)
    print(f"Found {len(replies)} replies")

    print("Analyzing with Ollama...")
    results = analyze_replies(replies, use_cache=not args.no_cache)

    if args.json:
        # Output JSON for further processing
        output = {cat: [{'from': r['from'], 'subject': r['subject'],
                        'summary': r.get('summary'), 'action': r.get('action'),
                        'urgency': r.get('urgency')}
                       for r in items]
                 for cat, items in results.items()}
        print(json.dumps(output, indent=2))
    else:
        print_summary(results)

if __name__ == '__main__':
    main()
