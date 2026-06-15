# Using OpenRouter Like Claude API

You now have a unified LLM interface (`llm.py`) that works like Claude's API.

---

## Quick Start

### Import
```python
from openrouter.llm import LLM, complete, chat
import asyncio
```

### Simple Completion
```python
async def main():
    llm = LLM()
    response = await llm.complete("What is Python?")
    print(response)

asyncio.run(main())
```

### Without Instance (Shortcuts)
```python
result = await complete("Explain machine learning")
print(result)
```

---

## Real Examples

### 1. **Classify Text**
```python
from openrouter.llm import complete
import asyncio

async def classify_job(job_title, description):
    """Classify job into sector."""
    prompt = f"""Classify this job into ONE category:

Title: {job_title}
Description: {description[:200]}

Categories: Agriculture, Construction, IT, Healthcare, Other

Return ONLY the category."""
    
    result = await complete(prompt)
    return result.strip()

# Usage
sector = asyncio.run(classify_job(
    "Farm Worker",
    "Harvest potatoes in Arges county..."
))
print(f"Sector: {sector}")
```

### 2. **Generate Content**
```python
from openrouter.llm import complete

async def generate_email(recipient, subject):
    """Write cold outreach email."""
    response = await complete(
        f"Write professional email to {recipient} about {subject}",
        system="You are an expert business development manager"
    )
    return response

email = asyncio.run(generate_email("mayor@city.ro", "agricultural opportunities"))
print(email)
```

### 3. **Chat Format (Multi-turn)**
```python
from openrouter.llm import chat
import asyncio

async def conversational_qa():
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "What crops grow in Romania?"},
    ]
    
    response = await chat(messages)
    print(f"Assistant: {response}")
    
    # Add follow-up
    messages.append({"role": "assistant", "content": response})
    messages.append({"role": "user", "content": "How much do they cost?"})
    
    response2 = await chat(messages)
    print(f"Assistant: {response2}")

asyncio.run(conversational_qa())
```

### 4. **Streaming (Real-time)**
```python
from openrouter.llm import LLM
import asyncio

async def stream_response():
    llm = LLM()
    async for token in llm.stream("Write a poem about farming"):
        print(token, end="", flush=True)
    print()

asyncio.run(stream_response())
```

### 5. **JSON Mode**
```python
from openrouter.llm import LLM
import asyncio

async def extract_data():
    llm = LLM()
    schema = """
    {
        "name": "string",
        "email": "string",
        "phone": "string",
        "location": "string"
    }
    """
    
    text = "John Smith, email john@example.com, +40 123 456, Bucharest"
    result = await llm.json_mode(
        f"Extract contact info: {text}",
        schema=schema
    )
    print(result)  # Returns parsed JSON

asyncio.run(extract_data())
```

---

## In Existing Code

### Replace Ad Service (Original)
**Before:**
```python
from app.services.ai_service import get_ai_service

async def create_ad(ad_data):
    ai_service = get_ai_service()
    title = await ai_service.generate_title(description, category)
```

**After:**
```python
from openrouter.llm import complete

async def create_ad(ad_data):
    title = await complete(
        f"Generate ad title for: {description}",
        system="Create compelling classified ad titles"
    )
```

### In Skills
**Before:**
```python
#!/usr/bin/env python3
from openrouter.client import quick_complete

result = await quick_complete("Your prompt")
```

**After (same interface, more powerful):**
```python
#!/usr/bin/env python3
from openrouter.llm import complete

result = await complete("Your prompt")

# Or with system prompt:
result = await complete(
    "Your prompt",
    system="You are a job classifier"
)
```

### In FastAPI Routes
```python
from fastapi import APIRouter
from openrouter.llm import complete

router = APIRouter()

@router.post("/api/analyze")
async def analyze_text(text: str):
    analysis = await complete(
        f"Analyze this text: {text}",
        system="You are a data analyst"
    )
    return {"analysis": analysis}
```

### In Database Processing
```python
import asyncio
from openrouter.llm import complete

async def enrich_companies(companies):
    """Add AI descriptions to company data."""
    for company in companies:
        description = await complete(
            f"Write 2-sentence company summary: {company['name']}, {company['industry']}"
        )
        company['ai_description'] = description
    return companies

# Usage
results = asyncio.run(enrich_companies(company_list))
```

---

## Models

Switch models easily:

```python
# Use best quality (slower but free)
llm = LLM(model="nvidia/nemotron-3-ultra")

# Use fastest (free)
llm = LLM(model="nvidia/nemotron-3-super")

# Use specific model
llm = LLM(model="meta-llama/llama-3-8b-instruct:free")

# Default auto-routing
llm = LLM()  # Uses OPENROUTER_DEFAULT_MODEL
```

---

## System Prompts

Like Claude's system parameter:

```python
# Classifier
await complete(prompt, system="You are a job classifier. Return ONLY the category.")

# Writer
await complete(prompt, system="You are a professional copywriter. Be compelling.")

# Analyst
await complete(prompt, system="You are a data analyst. Be precise and factual.")

# Coder
await complete(prompt, system="You are an expert Python developer.")
```

---

## Error Handling

```python
from openrouter.llm import complete

try:
    result = await complete("Your prompt")
except ValueError as e:
    print(f"Config error: {e}")
except httpx.TimeoutException:
    print("API timeout - try again")
except Exception as e:
    print(f"API error: {e}")
```

---

## Performance Tips

1. **Reuse instance for multiple calls:**
```python
# ✓ Good
llm = LLM()
result1 = await llm.complete("prompt1")
result2 = await llm.complete("prompt2")

# ✗ Slow
result1 = await complete("prompt1")
result2 = await complete("prompt2")  # Creates new instance
```

2. **Use streaming for long responses:**
```python
async for token in llm.stream("Write long article"):
    print(token, end="")  # Show as it generates
```

3. **Batch operations:**
```python
import asyncio

tasks = [
    complete(f"Classify: {text}") 
    for text in texts
]
results = await asyncio.gather(*tasks)
```

---

## Configuration

### Environment Variables
```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_DEFAULT_MODEL=openrouter/auto
```

### Runtime Override
```python
# Use different API key for this instance
llm = LLM(api_key="sk-or-v1-different-key")

# Use different model
llm = LLM(model="nvidia/nemotron-3-ultra")
```

---

## Cost

**All free models:** $0 per request, no payment method needed

---

## Next: Replace Claude in Your Code

Now you can use OpenRouter anywhere you'd use Claude API:

- **Ads platform** — Generate titles, descriptions, tags
- **Skills** — Classify jobs, extract data, generate content
- **Campaigns** — Write emails, social posts, landing pages
- **Scrapers** — Enrich data, deduplicate, classify
- **Backend** — Any API endpoint needing AI

Replace `from anthropic import Anthropic` with `from openrouter.llm import LLM` and you're set.
