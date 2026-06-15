#!/usr/bin/env python3
"""OpenRouter usage examples."""

import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from client import OpenRouterClient, quick_complete

# Load .env from this directory
load_dotenv(Path(__file__).parent / ".env")


async def example_1_auto_routing():
    """Use default auto-routing (free tier)."""
    print("=== Example 1: Auto-routing ===")
    client = OpenRouterClient()
    response = await client.chat(
        messages=[
            {"role": "user", "content": "Write a 2-line Python function that adds two numbers"}
        ],
        max_tokens=200,
    )
    print(response["choices"][0]["message"]["content"])


async def example_2_specific_model():
    """Use a specific free model."""
    print("\n=== Example 2: Specific model (Llama 3) ===")
    client = OpenRouterClient(model="meta-llama/llama-3-8b-instruct:free")
    try:
        response = await client.chat(
            messages=[
                {"role": "user", "content": "Explain the concept of async/await in Python"}
            ],
            max_tokens=300,
        )
        print(response["choices"][0]["message"]["content"])
    except Exception as e:
        # Fallback to auto-routing
        print(f"Model unavailable, using auto-routing: {e}")
        client = OpenRouterClient(model="openrouter/auto")
        response = await client.chat(
            messages=[
                {"role": "user", "content": "Explain the concept of async/await in Python"}
            ],
            max_tokens=300,
        )
        print(response["choices"][0]["message"]["content"])


async def example_3_quick_completion():
    """One-off completion without state."""
    print("\n=== Example 3: Quick completion ===")
    result = await quick_complete(
        "List 3 free LLM models suitable for web applications"
    )
    print(result)


async def example_4_multi_turn_conversation():
    """Multi-turn conversation."""
    print("\n=== Example 4: Multi-turn conversation ===")
    client = OpenRouterClient()
    messages = [
        {"role": "user", "content": "What is the capital of France?"},
    ]
    response = await client.chat(messages=messages, max_tokens=100)
    print(f"Q: What is the capital of France?\nA: {response['choices'][0]['message']['content']}")

    messages.append(response["choices"][0]["message"])
    messages.append({"role": "user", "content": "What is its population?"})
    response = await client.chat(messages=messages, max_tokens=100)
    print(f"\nQ: What is its population?\nA: {response['choices'][0]['message']['content']}")


async def example_5_ad_generation():
    """Generate classified ad descriptions (use case)."""
    print("\n=== Example 5: Ad generation (classified ads platform) ===")
    prompt = """Generate a compelling classified ad description for a used bicycle.
    Include: condition, features, price range, and call-to-action.
    Keep it under 100 words."""

    try:
        result = await quick_complete(prompt, model="meta-llama/llama-3-8b-instruct:free")
        print(result)
    except:
        # Fallback to auto-routing
        result = await quick_complete(prompt)
        print(result)


async def example_6_code_review():
    """Use LLM for code analysis."""
    print("\n=== Example 6: Code review ===")
    code_to_review = """
def calculate_price(items, tax_rate):
    total = 0
    for item in items:
        total = total + item['price'] * item['quantity']
    return total + (total * tax_rate)
"""
    prompt = f"Review this Python code and suggest improvements:\n{code_to_review}"

    try:
        result = await quick_complete(prompt, model="meta-llama/llama-3-8b-instruct:free")
        print(result)
    except:
        # Fallback to auto-routing
        result = await quick_complete(prompt)
        print(result)


async def main():
    """Run all examples."""
    examples = [
        example_1_auto_routing,
        example_2_specific_model,
        example_3_quick_completion,
        example_4_multi_turn_conversation,
        example_5_ad_generation,
        example_6_code_review,
    ]

    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
