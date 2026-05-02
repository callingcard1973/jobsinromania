#!/usr/bin/env python3
"""
LLM CLI - Command-line wrappers for local LLM operations

Zero-token alternatives to Claude for common tasks.
Routes through smart_router for optimal endpoint selection.

Usage:
    llm-classify "Is this spam?"
    llm-spam "FREE MONEY!!!"
    llm-translate "Hello" --to polish
    llm-code "fix syntax error" --file script.py
    llm-intent "I'm interested in your offer"

Or via main script:
    python3 llm_cli.py classify "Is this spam?"
    python3 llm_cli.py spam "FREE MONEY!!!"
    python3 llm_cli.py translate "Hello" --to polish
"""

import os
import sys
import json
import argparse

# Add paths
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from smart_router import SmartRouter, route_query, classify, spam_score


def cmd_classify(args):
    """Classify text intent"""
    result = classify(args.text)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        intent = result.get('intent', 'unknown')
        confidence = result.get('confidence', 0)
        print(f"Intent: {intent} ({confidence}% confidence)")
    return 0 if result.get('intent') else 1


def cmd_spam(args):
    """Score text for spam"""
    result = spam_score(args.text, subject=args.subject or "")
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        score = result.get('score', 50)
        reason = result.get('reason', 'N/A')
        emoji = "🔴" if score > 70 else ("⚠️" if score > 40 else "✅")
        print(f"{emoji} Spam score: {score}/100")
        if reason:
            print(f"   Reason: {reason}")
    return 0


def cmd_intent(args):
    """Detect intent in email reply"""
    result = route_query("intent", text=args.text)
    if result.success:
        try:
            data = result.response if isinstance(result.response, dict) else json.loads(result.response)
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                intent = data.get('intent', 'unknown')
                confidence = data.get('confidence', 0)
                emoji = {
                    'interested': '✅',
                    'not_interested': '❌',
                    'question': '❓',
                    'auto_reply': '🤖',
                    'bounce': '📭',
                    'unsubscribe': '🚫'
                }.get(intent, '❔')
                print(f"{emoji} Intent: {intent} ({confidence}%)")
        except:
            print(f"Response: {result.response}")
    else:
        print(f"Error: {result.error}")
        return 1
    return 0


def cmd_translate(args):
    """Translate text"""
    result = route_query("translate", text=args.text, target_language=args.to)
    if result.success:
        print(result.response)
    else:
        print(f"Error: {result.error}")
        return 1
    return 0


def cmd_enrich(args):
    """Enrich company lead"""
    result = route_query("lead_enrich", company=args.company, country=args.country or "")
    if result.success:
        if args.json:
            print(json.dumps(result.response, indent=2))
        else:
            try:
                data = result.response if isinstance(result.response, dict) else json.loads(result.response)
                print(f"Industry: {data.get('industry', 'N/A')}")
                print(f"Size: {data.get('size', 'N/A')}")
                print(f"Score: {data.get('recruitment_score', 'N/A')}")
            except:
                print(result.response)
    else:
        print(f"Error: {result.error}")
        return 1
    return 0


def cmd_code(args):
    """Code assistance (routes to laptop/cerebras)"""
    # Read file if provided
    content = ""
    if args.file:
        try:
            with open(args.file) as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {e}")
            return 1

    prompt = args.prompt
    if content:
        prompt = f"{prompt}\n\nCode:\n```\n{content[:3000]}\n```"

    result = route_query("code", prompt=prompt)
    if result.success:
        print(result.response)
        print(f"\n[Endpoint: {result.endpoint}, Latency: {result.latency_ms}ms]")
    else:
        print(f"Error: {result.error}")
        return 1
    return 0


def cmd_query(args):
    """General query (auto-routes)"""
    result = route_query(args.task, prompt=args.prompt)
    if args.json:
        print(json.dumps({
            'success': result.success,
            'endpoint': result.endpoint,
            'latency_ms': result.latency_ms,
            'response': result.response,
            'error': result.error
        }, indent=2))
    else:
        if result.success:
            print(result.response)
            print(f"\n[Endpoint: {result.endpoint}, Latency: {result.latency_ms}ms]")
        else:
            print(f"Error: {result.error}")
    return 0 if result.success else 1


def cmd_status(args):
    """Show router status"""
    router = SmartRouter()
    available = router.discover_available()

    print("LLM Router Status")
    print("=" * 40)
    print(f"\nEndpoints:")
    for name in ["local", "laptop", "cerebras", "picoclaw"]:
        status = "✅" if name in available else "❌"
        print(f"  {status} {name}")

    print(f"\nStatistics:")
    print(f"  Local calls: {router.stats.local_calls}")
    print(f"  Laptop calls: {router.stats.laptop_calls}")
    print(f"  Cerebras calls: {router.stats.cerebras_calls}")
    print(f"  PicoClaw calls: {router.stats.picoclaw_calls}")
    print(f"  Tokens saved: {router.stats.tokens_saved:,}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='LLM CLI - Zero-token local LLM commands',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  classify  Classify text intent (interested/not_interested/etc)
  spam      Score text for spam likelihood (0-100)
  intent    Detect email reply intent
  translate Translate text to target language
  enrich    Enrich company lead data
  code      Code assistance (fix, review, explain)
  query     General query (auto-routes to best endpoint)
  status    Show router status and stats

Examples:
  python3 llm_cli.py classify "STOP sending emails"
  python3 llm_cli.py spam "FREE MONEY NOW!!!"
  python3 llm_cli.py translate "Hello world" --to polish
  python3 llm_cli.py enrich "ACME Corp" --country DE
  python3 llm_cli.py code "fix syntax error" --file script.py
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # classify
    p = subparsers.add_parser('classify', help='Classify text intent')
    p.add_argument('text', help='Text to classify')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.set_defaults(func=cmd_classify)

    # spam
    p = subparsers.add_parser('spam', help='Score text for spam')
    p.add_argument('text', help='Text to score')
    p.add_argument('--subject', help='Email subject')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.set_defaults(func=cmd_spam)

    # intent
    p = subparsers.add_parser('intent', help='Detect email intent')
    p.add_argument('text', help='Email text')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.set_defaults(func=cmd_intent)

    # translate
    p = subparsers.add_parser('translate', help='Translate text')
    p.add_argument('text', help='Text to translate')
    p.add_argument('--to', default='english', help='Target language')
    p.set_defaults(func=cmd_translate)

    # enrich
    p = subparsers.add_parser('enrich', help='Enrich company lead')
    p.add_argument('company', help='Company name')
    p.add_argument('--country', help='Country code')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.set_defaults(func=cmd_enrich)

    # code
    p = subparsers.add_parser('code', help='Code assistance')
    p.add_argument('prompt', help='What to do')
    p.add_argument('--file', '-f', help='Code file to analyze')
    p.set_defaults(func=cmd_code)

    # query
    p = subparsers.add_parser('query', help='General query')
    p.add_argument('prompt', help='Query prompt')
    p.add_argument('--task', default='general', help='Task type')
    p.add_argument('--json', action='store_true', help='JSON output')
    p.set_defaults(func=cmd_query)

    # status
    p = subparsers.add_parser('status', help='Show router status')
    p.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
