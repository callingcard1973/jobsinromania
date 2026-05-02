#!/usr/bin/env python3
"""
Bounce Analyzer with LLM Intelligence
Analyzes Brevo bounce events and decides whether to continue campaign.

Uses LM Studio when available, falls back to rule-based analysis.

Usage:
    bounce_analyzer_llm.py --domain factoryjobs.eu
    bounce_analyzer_llm.py --domain factoryjobs.eu --decide
    bounce_analyzer_llm.py --domain factoryjobs.eu --resume-if-safe
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/LLM/llm_tasks')

import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import requests

# Try LM Studio client
try:
    from lmstudio_client import LMStudioClient
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

# Domain to API key mapping
DOMAIN_KEYS = {
    'factoryjobs.eu': 'BREVO_FACTORYJOBS_API_KEY',
    'buildjobs.eu': 'BREVO_BUILDJOBS_API_KEY',
    'warehouseworkers.eu': 'BREVO_WAREHOUSEWORKERS_API_KEY',
    'careworkers.eu': 'BREVO_CAREWORKERS_API_KEY',
    'interjob.ro': 'BREVO_INTERJOB_API_KEY',
    'mivromania.info': 'BREVO_MIVROMANIA_API_KEY',
    'cifn.info': 'BREVO_CIFN_API_KEY',
}

BREVO_API = "https://api.brevo.com/v3"


def get_brevo_stats(domain: str) -> Dict:
    """Get Brevo statistics for domain."""
    key_name = DOMAIN_KEYS.get(domain)
    if not key_name:
        return {"error": f"Unknown domain: {domain}"}

    api_key = os.getenv(key_name)
    if not api_key:
        return {"error": f"No API key for {domain}"}

    headers = {"api-key": api_key}

    # Get aggregated stats
    r = requests.get(f"{BREVO_API}/smtp/statistics/aggregatedReport",
                     headers=headers, params={"days": 1}, timeout=15)
    stats = r.json() if r.status_code == 200 else {}

    # Get recent bounces
    bounces = []
    for event_type in ['hardBounces', 'softBounces']:
        r = requests.get(f"{BREVO_API}/smtp/statistics/events",
                         headers=headers,
                         params={"event": event_type, "limit": 10},
                         timeout=15)
        if r.status_code == 200:
            for e in r.json().get('events', []):
                bounces.append({
                    "email": e.get('email'),
                    "type": event_type,
                    "reason": e.get('reason', 'unknown')[:100],
                    "date": e.get('date')
                })

    # Get blocked contacts
    r = requests.get(f"{BREVO_API}/smtp/blockedContacts",
                     headers=headers, params={"limit": 10}, timeout=15)
    blocked = []
    if r.status_code == 200:
        for c in r.json().get('contacts', []):
            blocked.append({
                "email": c.get('email'),
                "reason": str(c.get('reason', {}))[:100]
            })

    return {
        "domain": domain,
        "stats": stats,
        "bounces": bounces,
        "blocked": blocked
    }


def rule_based_analysis(data: Dict) -> Tuple[str, str, bool]:
    """
    Rule-based bounce analysis when LLM unavailable.
    Returns: (decision, reason, safe_to_continue)
    """
    stats = data.get('stats', {})
    bounces = data.get('bounces', [])

    total = stats.get('requests', 0)
    hard = stats.get('hardBounces', 0)
    soft = stats.get('softBounces', 0)
    delivered = stats.get('delivered', 0)

    if total == 0:
        return "CONTINUE", "No sends yet - safe to start", True

    bounce_rate = (hard + soft) / total * 100
    hard_rate = hard / total * 100 if total > 0 else 0

    # Analyze bounce reasons
    temp_reasons = ['mailbox full', 'temporarily', 'try again', 'timeout', 'connection']
    perm_reasons = ['user unknown', 'does not exist', 'invalid', 'rejected', 'blocked']

    temp_count = sum(1 for b in bounces if any(r in b.get('reason', '').lower() for r in temp_reasons))
    perm_count = sum(1 for b in bounces if any(r in b.get('reason', '').lower() for r in perm_reasons))

    # Decision logic
    if hard_rate > 5:
        return "STOP", f"Hard bounce rate too high: {hard_rate:.1f}%", False

    if bounce_rate > 15:
        return "STOP", f"Total bounce rate too high: {bounce_rate:.1f}%", False

    if bounce_rate > 10 and hard > soft:
        return "CAUTION", f"Bounce rate {bounce_rate:.1f}% with more hard than soft bounces", False

    if bounce_rate > 10 and temp_count > perm_count:
        return "CONTINUE", f"Bounce rate {bounce_rate:.1f}% but mostly temporary issues ({temp_count} temp vs {perm_count} perm)", True

    if bounce_rate > 10 and total < 10:
        return "CONTINUE", f"Bounce rate {bounce_rate:.1f}% but sample too small ({total} sends)", True

    if bounce_rate <= 5:
        return "CONTINUE", f"Healthy bounce rate: {bounce_rate:.1f}%", True

    return "CAUTION", f"Bounce rate {bounce_rate:.1f}% - monitor closely", True


def llm_analysis(data: Dict) -> Tuple[str, str, bool]:
    """
    LLM-powered bounce analysis.
    Returns: (decision, reason, safe_to_continue)
    """
    if not HAS_LLM:
        return rule_based_analysis(data)

    try:
        client = LMStudioClient(timeout=60)
    except Exception:
        return rule_based_analysis(data)

    stats = data.get('stats', {})
    bounces = data.get('bounces', [])[:5]  # Limit for context

    prompt = f"""Analyze this email campaign bounce data and decide if it's safe to continue sending.

STATISTICS (last 24h):
- Sent: {stats.get('requests', 0)}
- Delivered: {stats.get('delivered', 0)}
- Hard bounces: {stats.get('hardBounces', 0)}
- Soft bounces: {stats.get('softBounces', 0)}
- Blocked: {stats.get('blocked', 0)}

RECENT BOUNCES:
{json.dumps(bounces, indent=2)}

RULES:
- Hard bounce rate > 5% = STOP
- Total bounce rate > 15% = STOP
- Soft bounces (mailbox full, temporary) are less serious
- Small sample sizes can have inflated rates
- Consider bounce REASONS, not just numbers

RESPOND WITH EXACTLY THIS FORMAT:
DECISION: [CONTINUE|STOP|CAUTION]
REASON: [One sentence explanation]
SAFE: [YES|NO]"""

    try:
        response = client.query(prompt, model="fast", max_tokens=200)

        # Parse response
        lines = response.strip().split('\n')
        decision = "CAUTION"
        reason = "LLM analysis unclear"
        safe = False

        for line in lines:
            if line.startswith('DECISION:'):
                decision = line.split(':', 1)[1].strip()
            elif line.startswith('REASON:'):
                reason = line.split(':', 1)[1].strip()
            elif line.startswith('SAFE:'):
                safe = 'YES' in line.upper()

        return decision, reason, safe

    except Exception as e:
        print(f"LLM failed: {e}, using rules")
        return rule_based_analysis(data)


def analyze_domain(domain: str, use_llm: bool = True) -> Dict:
    """Full analysis of a domain's bounce status."""
    data = get_brevo_stats(domain)

    if 'error' in data:
        return data

    if use_llm and HAS_LLM:
        decision, reason, safe = llm_analysis(data)
        method = "LLM"
    else:
        decision, reason, safe = rule_based_analysis(data)
        method = "rules"

    stats = data.get('stats', {})
    total = stats.get('requests', 0)
    hard = stats.get('hardBounces', 0)
    soft = stats.get('softBounces', 0)
    bounce_rate = (hard + soft) / total * 100 if total > 0 else 0

    return {
        "domain": domain,
        "method": method,
        "decision": decision,
        "reason": reason,
        "safe_to_continue": safe,
        "stats": {
            "sent_24h": total,
            "delivered": stats.get('delivered', 0),
            "hard_bounces": hard,
            "soft_bounces": soft,
            "bounce_rate": f"{bounce_rate:.1f}%"
        },
        "recent_bounces": data.get('bounces', [])[:3]
    }


def main():
    parser = argparse.ArgumentParser(description='Bounce Analyzer with LLM')
    parser.add_argument('--domain', required=True, help='Domain to analyze')
    parser.add_argument('--decide', action='store_true', help='Show decision')
    parser.add_argument('--resume-if-safe', action='store_true', help='Output resume command if safe')
    parser.add_argument('--no-llm', action='store_true', help='Use rules only')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    args = parser.parse_args()

    result = analyze_domain(args.domain, use_llm=not args.no_llm)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\n=== Bounce Analysis: {args.domain} ===")
    print(f"Method: {result.get('method', 'unknown')}")
    print(f"Decision: {result.get('decision')}")
    print(f"Reason: {result.get('reason')}")
    print(f"Safe to continue: {'YES' if result.get('safe_to_continue') else 'NO'}")
    print(f"\nStats (24h):")
    for k, v in result.get('stats', {}).items():
        print(f"  {k}: {v}")

    if result.get('recent_bounces'):
        print(f"\nRecent bounces:")
        for b in result.get('recent_bounces', []):
            print(f"  - {b.get('email')}: {b.get('reason', 'unknown')[:50]}")

    if args.resume_if_safe and result.get('safe_to_continue'):
        print(f"\n# Safe to resume - run:")
        print(f"cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && python3 send_campaign.py --config configs/bulgaria_contractors.json --sector ALL --limit 290")


if __name__ == '__main__':
    main()
