#!/usr/bin/env python3
"""
Email Content Scorer - Pre-send spam risk analysis using local LLM.

Analyzes email subject + body BEFORE sending to predict spam filter triggers.
Uses laptop LLM (32GB + GPU) for fast analysis.

Usage:
    # Score a template file
    python3 email_content_scorer.py --file /path/to/template.txt

    # Score text directly
    python3 email_content_scorer.py --subject "Job offer" --body "We have workers..."

    # Score all templates in a campaign
    python3 email_content_scorer.py --campaign POLAND

    # JSON output
    python3 email_content_scorer.py --file template.txt --json

Author: INTERJOB SOLUTIONS EUROPE SRL
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, '/opt/ACTIVE/LLM')
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from AI.lmstudio_client import get_laptop_client, query_fast

# Spam trigger patterns (rule-based pre-check)
SPAM_WORDS = [
    'free', 'winner', 'congratulations', 'urgent', 'act now', 'limited time',
    'click here', 'buy now', 'order now', 'special offer', 'exclusive deal',
    'no obligation', 'risk free', 'guarantee', 'cheap', 'discount', 'save big',
    'make money', 'earn cash', 'work from home', 'double your', 'million',
    'credit card', 'no credit check', 'loans', 'casino', 'viagra', 'pills'
]

URGENCY_PHRASES = [
    'act now', 'limited time', 'expires', 'last chance', 'don\'t miss',
    'hurry', 'immediately', 'urgent', 'deadline', 'today only'
]


@dataclass
class SpamScore:
    """Spam analysis result."""
    overall_score: int  # 1-10 (10 = definitely spam)
    risk_level: str  # low, medium, high, critical
    issues: List[str]
    suggestions: List[str]
    details: Dict[str, any]


def analyze_rules(subject: str, body: str) -> Dict:
    """Rule-based analysis (fast, no LLM)."""
    text = f"{subject} {body}".lower()
    issues = []

    # Check caps ratio
    caps_count = sum(1 for c in subject + body if c.isupper())
    total_chars = len(subject + body)
    caps_ratio = caps_count / max(total_chars, 1)

    if caps_ratio > 0.3:
        issues.append(f"Excessive caps ({caps_ratio:.0%} uppercase)")

    # Check spam words
    found_spam_words = [w for w in SPAM_WORDS if w in text]
    if found_spam_words:
        issues.append(f"Spam trigger words: {', '.join(found_spam_words[:5])}")

    # Check urgency phrases
    found_urgency = [p for p in URGENCY_PHRASES if p in text]
    if found_urgency:
        issues.append(f"Urgency language: {', '.join(found_urgency[:3])}")

    # Check link count
    links = re.findall(r'https?://|www\.', text)
    if len(links) > 3:
        issues.append(f"Too many links ({len(links)} found)")

    # Check for ALL CAPS words
    all_caps_words = re.findall(r'\b[A-Z]{4,}\b', subject + body)
    if len(all_caps_words) > 2:
        issues.append(f"ALL CAPS words: {', '.join(all_caps_words[:3])}")

    # Check exclamation marks
    exclamations = (subject + body).count('!')
    if exclamations > 3:
        issues.append(f"Too many exclamation marks ({exclamations})")

    # Check for money symbols
    money = re.findall(r'[$€£]\d+|\d+[$€£]', text)
    if money:
        issues.append(f"Money amounts in text: {', '.join(money[:3])}")

    # Calculate rule-based score
    score = min(10, len(issues) * 2)

    return {
        "score": score,
        "issues": issues,
        "caps_ratio": caps_ratio,
        "spam_words": found_spam_words,
        "link_count": len(links),
    }


def analyze_with_llm(subject: str, body: str) -> Optional[Dict]:
    """LLM-based deep analysis."""
    client = get_laptop_client()
    if not client:
        return None

    prompt = f"""Analyze this email for spam filter triggers. Score 1-10 (1=safe, 10=spam).

Subject: {subject}

Body:
{body[:1500]}

Check for:
1. Spam trigger words/phrases
2. Excessive urgency or pressure
3. Unprofessional formatting
4. Suspicious claims or promises
5. Missing personalization
6. Salesy/promotional tone

Respond in JSON only:
{{"score": 5, "risk": "medium", "issues": ["issue1", "issue2"], "suggestions": ["fix1", "fix2"], "tone": "professional/salesy/neutral"}}
"""

    try:
        result = client.query(
            prompt,
            model="google/gemma-3-4b",
            temperature=0.1,
            max_tokens=500
        )

        if result:
            # Extract JSON
            result = result.strip()
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0]
            elif "```" in result:
                result = result.split("```")[1].split("```")[0]

            return json.loads(result.strip())
    except Exception as e:
        print(f"  [WARN] LLM analysis error: {e}")

    return None


def score_email(subject: str, body: str, use_llm: bool = True) -> SpamScore:
    """
    Score email content for spam risk.

    Args:
        subject: Email subject line
        body: Email body text
        use_llm: Whether to use LLM for deep analysis

    Returns:
        SpamScore with overall score, issues, and suggestions
    """
    # Rule-based analysis (always run)
    rules = analyze_rules(subject, body)

    issues = rules["issues"].copy()
    suggestions = []
    details = {
        "method": "rules",
        "caps_ratio": rules["caps_ratio"],
        "link_count": rules["link_count"],
        "spam_words_found": rules["spam_words"],
    }

    # LLM analysis
    llm_result = None
    if use_llm:
        llm_result = analyze_with_llm(subject, body)
        if llm_result:
            details["method"] = "llm+rules"
            details["llm_score"] = llm_result.get("score", 5)
            details["tone"] = llm_result.get("tone", "unknown")

            # Add LLM issues
            for issue in llm_result.get("issues", []):
                if issue not in issues:
                    issues.append(issue)

            suggestions = llm_result.get("suggestions", [])

    # Calculate final score
    if llm_result:
        # Average of rule score and LLM score
        final_score = (rules["score"] + llm_result.get("score", 5)) // 2
    else:
        final_score = rules["score"]

    # Determine risk level
    if final_score <= 2:
        risk = "low"
    elif final_score <= 4:
        risk = "medium"
    elif final_score <= 7:
        risk = "high"
    else:
        risk = "critical"

    # Default suggestions if none from LLM
    if not suggestions:
        if rules["caps_ratio"] > 0.2:
            suggestions.append("Reduce uppercase letters")
        if rules["spam_words"]:
            suggestions.append("Replace spam trigger words with neutral alternatives")
        if rules["link_count"] > 2:
            suggestions.append("Reduce number of links")
        if not suggestions:
            suggestions.append("Email looks good - no major issues found")

    return SpamScore(
        overall_score=final_score,
        risk_level=risk,
        issues=issues,
        suggestions=suggestions,
        details=details
    )


def parse_template_file(filepath: str) -> Tuple[str, str]:
    """Parse template file to extract subject and body."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Look for Subject: line
    subject = "No subject"
    body = content

    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.lower().startswith('subject:'):
            subject = line.split(':', 1)[1].strip()
            body = '\n'.join(lines[i+1:]).strip()
            break

    return subject, body


def score_campaign_templates(campaign_name: str) -> List[Dict]:
    """Score all templates in a campaign folder."""
    campaign_path = Path(f"/opt/ACTIVE/EMAIL/CAMPAIGNS/{campaign_name}/templates")

    if not campaign_path.exists():
        print(f"Campaign not found: {campaign_path}")
        return []

    results = []
    for template_file in sorted(campaign_path.glob("*.txt")):
        print(f"\n--- {template_file.name} ---")
        subject, body = parse_template_file(str(template_file))
        score = score_email(subject, body)

        results.append({
            "file": template_file.name,
            "subject": subject[:50],
            "score": score.overall_score,
            "risk": score.risk_level,
            "issues": score.issues,
        })

        # Print summary
        risk_emoji = {"low": "✅", "medium": "⚠️", "high": "🔶", "critical": "🔴"}
        print(f"{risk_emoji.get(score.risk_level, '?')} Score: {score.overall_score}/10 ({score.risk_level})")
        if score.issues:
            for issue in score.issues[:3]:
                print(f"  - {issue}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Email Content Spam Scorer")
    parser.add_argument("--file", help="Template file to score")
    parser.add_argument("--subject", help="Email subject")
    parser.add_argument("--body", help="Email body")
    parser.add_argument("--campaign", help="Score all templates in campaign")
    parser.add_argument("--no-llm", action="store_true", help="Rules only, no LLM")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args()

    # Campaign mode
    if args.campaign:
        results = score_campaign_templates(args.campaign)
        if args.json:
            print(json.dumps(results, indent=2))
        return

    # Get subject and body
    if args.file:
        subject, body = parse_template_file(args.file)
    elif args.subject and args.body:
        subject = args.subject
        body = args.body
    else:
        print("Provide --file or both --subject and --body")
        return

    # Score
    score = score_email(subject, body, use_llm=not args.no_llm)

    if args.json:
        print(json.dumps(asdict(score), indent=2))
    else:
        risk_emoji = {"low": "✅", "medium": "⚠️", "high": "🔶", "critical": "🔴"}
        print(f"\n{'='*50}")
        print(f"SPAM SCORE: {score.overall_score}/10 {risk_emoji.get(score.risk_level, '')}")
        print(f"Risk Level: {score.risk_level.upper()}")
        print(f"{'='*50}")

        if score.issues:
            print(f"\nIssues Found ({len(score.issues)}):")
            for issue in score.issues:
                print(f"  ❌ {issue}")

        if score.suggestions:
            print(f"\nSuggestions:")
            for suggestion in score.suggestions:
                print(f"  💡 {suggestion}")

        print(f"\nDetails: {score.details.get('method', 'unknown')} analysis")


if __name__ == "__main__":
    main()
