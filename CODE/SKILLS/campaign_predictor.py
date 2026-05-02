#!/usr/bin/env python3
"""
Campaign Performance Predictor using LM Studio
Predict email campaign metrics before sending.

Usage:
    python3 campaign_predictor.py --subject "Job opportunity" --sender factoryjobs.eu --audience 500
    python3 campaign_predictor.py --analyze /opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY/

# [AI: Claude Code]
Author: INTERJOB SOLUTIONS EUROPE SRL
"""

import sys
import os
import json
import argparse
from typing import Dict, Optional

sys.path.insert(0, '/opt/ACTIVE/LLM/AI')
from lmstudio_client import LMStudioClient, is_lmstudio_available

# Historical averages (rough estimates)
BASELINE = {
    'open_rate': 22,
    'click_rate': 3,
    'bounce_rate': 5,
    'spam_rate': 0.5
}

# Spam trigger words
SPAM_TRIGGERS = [
    'free', 'urgent', 'act now', 'limited time', 'guarantee',
    'click here', 'winner', 'congratulations', 'no obligation'
]


def analyze_subject(subject: str) -> Dict:
    """Analyze subject line for spam signals."""
    subject_lower = subject.lower()
    issues = []

    # Length check
    if len(subject) > 60:
        issues.append('Subject too long (>60 chars)')
    if len(subject) < 10:
        issues.append('Subject too short (<10 chars)')

    # Spam triggers
    for trigger in SPAM_TRIGGERS:
        if trigger in subject_lower:
            issues.append(f'Spam trigger: "{trigger}"')

    # All caps
    if subject.isupper():
        issues.append('All caps detected')

    # Excessive punctuation
    if subject.count('!') > 1:
        issues.append('Multiple exclamation marks')
    if subject.count('?') > 1:
        issues.append('Multiple question marks')

    return {
        'length': len(subject),
        'issues': issues,
        'spam_risk': min(len(issues) * 2, 10)
    }


def predict_metrics(
    subject: str,
    sender_domain: str,
    audience_size: int,
    sector: str = None
) -> Dict:
    """Predict campaign metrics."""
    subject_analysis = analyze_subject(subject)

    # Adjust baseline based on factors
    open_rate = BASELINE['open_rate']
    click_rate = BASELINE['click_rate']
    bounce_rate = BASELINE['bounce_rate']

    # Spam risk reduces open rate
    open_rate -= subject_analysis['spam_risk'] * 2

    # Domain reputation (simplified)
    trusted_domains = ['interjob.ro', 'factoryjobs.eu', 'buildjobs.eu']
    if sender_domain in trusted_domains:
        open_rate += 5
    elif '.eu' in sender_domain:
        open_rate += 2

    # Audience size impact
    if audience_size > 1000:
        bounce_rate += 2
    if audience_size > 5000:
        bounce_rate += 3

    # Clamp values
    open_rate = max(5, min(40, open_rate))
    click_rate = max(0.5, min(10, click_rate))
    bounce_rate = max(1, min(20, bounce_rate))

    return {
        'subject_analysis': subject_analysis,
        'predictions': {
            'open_rate': round(open_rate, 1),
            'click_rate': round(click_rate, 1),
            'bounce_rate': round(bounce_rate, 1),
            'expected_opens': int(audience_size * open_rate / 100),
            'expected_clicks': int(audience_size * click_rate / 100),
            'expected_bounces': int(audience_size * bounce_rate / 100)
        },
        'recommendations': get_recommendations(subject_analysis)
    }


def get_recommendations(analysis: Dict) -> list:
    """Get improvement recommendations."""
    recs = []
    if analysis['spam_risk'] > 5:
        recs.append('Rewrite subject to avoid spam triggers')
    if analysis['length'] > 50:
        recs.append('Shorten subject line for better mobile display')
    if analysis['length'] < 20:
        recs.append('Add more context to subject line')
    if not recs:
        recs.append('Subject looks good!')
    return recs


def predict_with_llm(subject: str, context: str = "") -> Optional[Dict]:
    """Get LLM prediction."""
    if not is_lmstudio_available():
        return None

    prompt = f"""Predict email campaign metrics for this subject line.

SUBJECT: {subject}
{context}

Reply with:
OPEN_RATE: [percent]
RISK: [1-10]
SUGGESTION: [one improvement]"""

    client = LMStudioClient(timeout=120)
    response = client.query(prompt, temperature=0.3, max_tokens=100)

    if response:
        result = {}
        for line in response.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                result[key.strip().lower()] = val.strip()
        return result
    return None


def main():
    parser = argparse.ArgumentParser(description='Predict campaign performance')
    parser.add_argument('--subject', help='Email subject line')
    parser.add_argument('--sender', default='interjob.ro',
                        help='Sender domain')
    parser.add_argument('--audience', type=int, default=100,
                        help='Audience size')
    parser.add_argument('--sector', default=None,
                        help='Industry sector')
    parser.add_argument('--llm', action='store_true',
                        help='Use LLM for prediction')
    parser.add_argument('--analyze', help='Analyze campaign directory')
    parser.add_argument('--test', action='store_true',
                        help='Test mode')

    args = parser.parse_args()

    if args.test:
        print("Testing predictor...")
        result = predict_metrics("Test Subject Line", "test.com", 100)
        print(f"Predictions: {result['predictions']}")
        return

    if args.analyze:
        # Analyze campaign from directory
        state_file = os.path.join(args.analyze, 'state.json')
        if os.path.exists(state_file):
            with open(state_file) as f:
                state = json.load(f)
            print(f"Campaign: {args.analyze}")
            print(f"State: {json.dumps(state, indent=2)}")
        else:
            print(f"[ERROR] No state.json in {args.analyze}")
        return

    if not args.subject:
        print("[ERROR] --subject required")
        sys.exit(1)

    # Predict
    result = predict_metrics(
        subject=args.subject,
        sender_domain=args.sender,
        audience_size=args.audience,
        sector=args.sector
    )

    # LLM enhancement
    if args.llm and is_lmstudio_available():
        llm_result = predict_with_llm(args.subject)
        if llm_result:
            result['llm_prediction'] = llm_result

    # Output
    print(f"Subject: {args.subject}")
    print(f"Sender: {args.sender}")
    print(f"Audience: {args.audience}")
    print()
    print("=== PREDICTIONS ===")
    for key, val in result['predictions'].items():
        print(f"  {key}: {val}")
    print()
    print("=== SUBJECT ANALYSIS ===")
    print(f"  Length: {result['subject_analysis']['length']}")
    print(f"  Spam risk: {result['subject_analysis']['spam_risk']}/10")
    if result['subject_analysis']['issues']:
        print(f"  Issues: {', '.join(result['subject_analysis']['issues'])}")
    print()
    print("=== RECOMMENDATIONS ===")
    for rec in result['recommendations']:
        print(f"  - {rec}")


if __name__ == '__main__':
    main()
