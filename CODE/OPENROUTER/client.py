#!/usr/bin/env python3
"""OpenRouter client for free LLM models."""

import os
import httpx
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env from current directory if it exists
if Path(__file__).parent.joinpath(".env").exists():
    load_dotenv(Path(__file__).parent / ".env")

class OpenRouterClient:
    """Simple async client for OpenRouter API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_DEFAULT_MODEL", "openrouter/auto")
        self.base_url = base_url

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment or constructor")

    async def chat(
        self,
        messages: list[dict],
        max_tokens: int = 2048,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> dict:
        """Send chat request to OpenRouter."""
        model = model or self.model

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://interjob.ro",
                    "X-Title": "Universal Classified Ads Platform",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        """Simple text completion."""
        result = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=max_tokens,
        )
        return result["choices"][0]["message"]["content"]


async def quick_complete(prompt: str, model: str = "openrouter/auto") -> str:
    """One-off completion without state."""
    client = OpenRouterClient(model=model)
    return await client.complete(prompt)


if __name__ == "__main__":
    import asyncio

    async def test():
        client = OpenRouterClient()
        response = await client.chat(
            messages=[{"role": "user", "content": "Say 'Hello from OpenRouter'"}],
            max_tokens=100,
        )
        print(response["choices"][0]["message"]["content"])

    asyncio.run(test())
