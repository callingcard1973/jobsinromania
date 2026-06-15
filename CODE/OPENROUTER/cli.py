#!/usr/bin/env python3
"""Command-line interface for OpenRouter LLM."""

import sys
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv
from llm import LLM

# Load .env
if Path(__file__).parent.joinpath(".env").exists():
    load_dotenv(Path(__file__).parent / ".env")


def main():
    parser = argparse.ArgumentParser(
        description="OpenRouter LLM from terminal",
        epilog="Examples:\n"
               "  python cli.py 'What is 2+2?'\n"
               "  python cli.py 'Classify this text' --system 'Return only the category'\n"
               "  echo 'Hello' | python cli.py --stdin\n"
               "  python cli.py --stream 'Write a poem'\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="The prompt to send to the LLM"
    )

    parser.add_argument(
        "--system",
        "-s",
        help="System prompt (instructions for the AI)"
    )

    parser.add_argument(
        "--model",
        "-m",
        help="Model to use (default: openrouter/auto)"
    )

    parser.add_argument(
        "--stream",
        "-t",
        action="store_true",
        help="Stream the response token by token"
    )

    parser.add_argument(
        "--stdin",
        "-i",
        action="store_true",
        help="Read prompt from stdin (pipe input)"
    )

    parser.add_argument(
        "--json",
        "-j",
        help="Parse response as JSON (provide schema)"
    )

    parser.add_argument(
        "--tokens",
        type=int,
        default=2048,
        help="Max tokens in response (default: 2048)"
    )

    parser.add_argument(
        "--temp",
        type=float,
        default=0.7,
        help="Temperature (0-1, default: 0.7)"
    )

    args = parser.parse_args()

    # Get prompt
    if args.stdin:
        prompt = sys.stdin.read().strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        parser.print_help()
        sys.exit(1)

    try:
        llm = LLM(model=args.model)

        if args.stream:
            # Streaming mode
            asyncio.run(_stream(llm, prompt, args.system, args.tokens))
        elif args.json:
            # JSON mode
            asyncio.run(_json(llm, prompt, args.json, args.system, args.tokens))
        else:
            # Normal mode
            result = asyncio.run(_complete(llm, prompt, args.system, args.tokens, args.temp))
            print(result)

    except KeyboardInterrupt:
        print("\n[Interrupted]", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def _complete(llm, prompt, system, tokens, temp):
    """Simple completion."""
    return await llm.complete(prompt, system=system or "", max_tokens=tokens, temperature=temp)


async def _stream(llm, prompt, system, tokens):
    """Streaming completion."""
    async for token in llm.stream(prompt, system=system or "", max_tokens=tokens):
        print(token, end="", flush=True)
    print()


async def _json(llm, prompt, schema, system, tokens):
    """JSON mode completion."""
    result = await llm.json_mode(prompt, schema=schema, system=system or "", max_tokens=tokens)
    import json
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
