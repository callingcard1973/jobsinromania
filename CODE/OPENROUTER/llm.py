#!/usr/bin/env python3
"""Unified LLM interface — use OpenRouter like Claude API."""

import os
import httpx
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional, AsyncGenerator

# Load .env
if Path(__file__).parent.joinpath(".env").exists():
    load_dotenv(Path(__file__).parent / ".env")


class LLM:
    """Simple LLM client that works like Claude API."""

    def __init__(
        self,
        provider: str = "openrouter",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """Initialize LLM client.

        Args:
            provider: "openrouter" or "claude" (future)
            model: Model name (defaults from env)
            api_key: API key (defaults from env)
        """
        self.provider = provider
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_DEFAULT_MODEL", "openrouter/auto")

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

    async def complete(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Simple text completion (like Claude)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Force free tier only
        if os.getenv("OPENROUTER_REQUIRE_FREE") == "true":
            payload["require_parameters"] = {"provider": {"allow_free": True, "disallow": ["Anthropic", "OpenAI", "Google"]}}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://interjob.ro",
                },
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str:
        """Chat completion (like Claude messages API)."""
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Force free tier only
        if os.getenv("OPENROUTER_REQUIRE_FREE") == "true":
            payload["require_parameters"] = {"provider": {"allow_free": True, "disallow": ["Anthropic", "OpenAI", "Google"]}}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://interjob.ro",
                },
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def stream(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Stream tokens one at a time (like Claude streaming)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        # Force free tier only
        if os.getenv("OPENROUTER_REQUIRE_FREE") == "true":
            payload["require_parameters"] = {"provider": {"allow_free": True, "disallow": ["Anthropic", "OpenAI", "Google"]}}

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://interjob.ro",
                },
                json=payload,
                timeout=60,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        text = line[5:].strip()
                        if text and text != "[DONE]":
                            try:
                                import json
                                data = json.loads(text)
                                delta = data.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except:
                                pass

    async def json_mode(
        self,
        prompt: str,
        schema: str,
        system: str = "",
        max_tokens: int = 2048,
    ) -> dict:
        """Get structured JSON response."""
        system_with_schema = f"{system}\n\nRespond ONLY with valid JSON matching this schema:\n{schema}"
        response = await self.complete(prompt, system=system_with_schema, max_tokens=max_tokens)
        import json
        return json.loads(response)


# Singleton instance
_llm = None


def get_llm(model: Optional[str] = None) -> LLM:
    """Get or create LLM instance."""
    global _llm
    if _llm is None:
        _llm = LLM(model=model)
    return _llm


# Shortcuts for quick use
async def complete(prompt: str, system: str = "", model: Optional[str] = None) -> str:
    """Quick completion without instantiating."""
    llm = LLM(model=model)
    return await llm.complete(prompt, system=system)


async def chat(messages: list[dict], model: Optional[str] = None) -> str:
    """Quick chat without instantiating."""
    llm = LLM(model=model)
    return await llm.chat(messages)


if __name__ == "__main__":
    import asyncio

    async def test():
        llm = LLM()

        # Test 1: Simple completion
        print("=== Test 1: Simple completion ===")
        result = await llm.complete("What is 2+2?")
        print(result)

        # Test 2: Chat format
        print("\n=== Test 2: Chat format ===")
        result = await llm.chat([
            {"role": "user", "content": "Hello, who are you?"}
        ])
        print(result)

        # Test 3: With system prompt
        print("\n=== Test 3: System prompt ===")
        result = await llm.complete(
            "Write a haiku about coding",
            system="You are a creative poet"
        )
        print(result)

        # Test 4: Streaming
        print("\n=== Test 4: Streaming ===")
        async for token in llm.stream("Count to 5"):
            print(token, end="", flush=True)
        print()

    asyncio.run(test())
