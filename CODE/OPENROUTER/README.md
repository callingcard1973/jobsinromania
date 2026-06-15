# OpenRouter Integration

This directory provides free LLM model access via OpenRouter.

## Quick Start

### 1. Environment Setup

The `.env` file is pre-configured with your API key:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_DEFAULT_MODEL=openrouter/auto  # Uses free tier routing
```

For use in other directories, set:
```bash
export OPENROUTER_API_KEY=sk-or-v1-...
```

### 2. Python Usage

```python
from openrouter.client import OpenRouterClient
import asyncio

async def main():
    client = OpenRouterClient()
    response = await client.chat(
        messages=[{"role": "user", "content": "What is 2+2?"}],
        max_tokens=100,
    )
    print(response["choices"][0]["message"]["content"])

asyncio.run(main())
```

Or use the quick helper:
```python
from openrouter.client import quick_complete
import asyncio

result = asyncio.run(quick_complete("Explain Python async"))
print(result)
```

### 3. Command Line

```bash
python -m openrouter.client  # Run test
```

## Available Models (Free)

| Model | Speed | Capability | Use Case |
|-------|-------|-----------|----------|
| `openrouter/auto` | Fastest | Basic | Default; system chooses free tier |
| `nvidia/nemotron-3-super` | Fast | Good | Fast reasoning, general tasks |
| `nvidia/nemotron-3-ultra` | Balanced | Excellent | Coding, analysis, long-form |
| `meta-llama/llama-3-8b-instruct` | Fast | Good | Instruction following |
| `mistralai/mistral-7b-instruct` | Very Fast | Basic | Quick turnarounds |
| `owl-ai/owl-alpha` | Balanced | Experimental | Testing new models |

**Recommended:**
- **Default:** `openrouter/auto` (no cost, automatic routing)
- **Best quality:** `nvidia/nemotron-3-ultra` (free, excellent for complex tasks)
- **Fastest:** `nvidia/nemotron-3-super` (free, good for rapid iteration)

## Usage Patterns

### Pattern 1: Auto-Routing (Recommended)

```python
client = OpenRouterClient()  # Uses openrouter/auto
```

**Pros:** Zero cost, OpenRouter picks the best available free model  
**Cons:** Unpredictable model switching (but consistent results)

### Pattern 2: Fixed Model

```python
client = OpenRouterClient(model="nvidia/nemotron-3-ultra")
```

**Pros:** Consistent behavior, predictable performance  
**Cons:** Model may become unavailable

### Pattern 3: Per-Request Override

```python
response = await client.chat(
    messages=[...],
    model="meta-llama/llama-3-8b-instruct"  # Override for this call only
)
```

## Integration with Projects

### Universal Classified Ads Platform

Add to `backend/.env`:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=nvidia/nemotron-3-ultra
```

Use in code:
```python
# In app/services/ai_service.py
from openrouter.client import OpenRouterClient

client = OpenRouterClient()
response = await client.complete("Generate ad description...")
```

### Skills Library

Use in any skill:
```python
#!/usr/bin/env python3
"""AI-powered skill."""

from openrouter.client import quick_complete
import asyncio

async def main():
    description = await quick_complete("Describe this image context...")
    print(description)

if __name__ == "__main__":
    asyncio.run(main())
```

## Monitoring & Limits

- **Rate limit:** OpenRouter free tier has standard limits; see https://openrouter.ai/limits
- **Quota checking:** Run `curl https://openrouter.ai/api/v1/auth/keys` with your Bearer token
- **Cost:** $0 for all free models; no payment method required

## Troubleshooting

**Error: "Invalid API key"**
```bash
# Verify key is set
echo $OPENROUTER_API_KEY

# Or check .env
grep OPENROUTER_API_KEY .env
```

**Error: "Model not found"**
- Model may be unavailable; switch to `openrouter/auto`
- Check OpenRouter status page: https://status.openrouter.io

**Error: "Rate limit exceeded"**
- Wait 60 seconds before retry
- Use `nvidia/nemotron-3-super` (often has higher limits)

## References

- OpenRouter API docs: https://openrouter.ai/api/documentation
- Free models list: https://openrouter.ai
- Status page: https://status.openrouter.io

---

**Setup date:** 2026-06-15  
**Key added:** sk-or-v1-[your-key-here]
