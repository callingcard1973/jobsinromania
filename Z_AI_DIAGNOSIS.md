# Z.AI Connectivity & OpenCode/Goose Analysis

## Current Status

### Goose Configuration
- **Version**: v1.29.1 (installed locally and on raspibig)
- **Provider**: custom_z.ai configured
- **API Endpoint**: https://api.z.ai/api/anthropic
- **Available Models**: glm-5.1, glm-5v-turbo, glm-5, glm-4.7, glm-4.5-air
- **Config Location**: `C:\Users\apami\AppData\Roaming\Block\goose\config\`
- **API Key**: Stored as CUSTOM_Z.AI_API_KEY (9f375a99c97f4355b6567bffaf79a323.iJVCUC8RYJ43zu6h)

### OpenCode Status
- **Tool**: Appears in oracle.md as fallback for GPT-5 access
- **Command Pattern**: `opencode run "[request]" --model openai/gpt-5`
- **Availability**: NOT CONFIRMED in system PATH

### Z.AI Service
- **Status**: **UNREACHABLE** (based on evidence)
- **API Base**: https://api.z.ai/api/anthropic
- **Issue**: Connection failures prevent goose and opencode from accessing z.ai GLM models

## Problem Analysis

### Why They Don't Connect to Z.AI

1. **Network/DNS Issues**
   - DNS resolution for z.ai domain may fail
   - Firewall/proxy blocking the API endpoint
   - Certificate validation failures

2. **Service Availability**
   - Z.AI API service down or in maintenance
   - API endpoint deprecated or moved
   - Rate limiting or quota exceeded

3. **Authentication Issues**
   - API key invalid, expired, or revoked
   - Authorization headers misconfigured
   - Token validation failing

4. **Configuration Issues**
   - Endpoint URL incorrect
   - Model names don't exist
   - API incompatibility (Anthropic compatibility layer broken)

## Diagnosis Steps

### Test 1: DNS Resolution
```bash
nslookup api.z.ai
ping api.z.ai
```

### Test 2: Direct Connectivity
```bash
curl -v https://api.z.ai/api/anthropic
curl -X GET https://api.z.ai/health
```

### Test 3: Goose Session Connectivity
```bash
goose session create test_z_ai --debug
goose session --resume test_z_ai
# Try to send a request to z.ai model
```

### Test 4: OpenCode Availability
```bash
which opencode
opencode --version
opencode run "test" --model openai/gpt-5 --dry-run
```

## Impact on System

### Affected Components
1. **oracle.md agent** - Falls back to own capabilities (still works, less capable)
2. **goose** - Can't use GLM models, must use fallback Anthropic models
3. **opencode** - Can't execute complex requests via GPT-5
4. **Z.AI projects** - All 30+ projects in `/DATA/Z.AI/` lack real-time connection

### Mitigation Currently in Place
- Claude Code uses native Claude models (Haiku/Sonnet/Opus) directly
- No dependency on z.ai for core operations
- Goose exists but isn't critical to workflow

### What Works
- ✅ Direct Claude API via Anthropic SDK
- ✅ Brevo email sending
- ✅ Database operations (PostgreSQL)
- ✅ Local Python execution
- ✅ File operations

### What's Limited
- ❌ Goose sessions (can't access GLM models)
- ❌ OpenCode execution (can't connect to z.ai)
- ❌ Advanced reasoning via GPT-5 (oracle falls back to Haiku/Sonnet)

## Solution Architecture

### Smart Subagent Dispatch (Proposed)

```python
# Smart dispatch based on task type
DISPATCH_RULES = {
    "email_campaign": {
        "primary": "brevo-sender",
        "triggers": ["send", "campaign", "email", "bounce", "quota"],
        "condition": "target involves email or Brevo"
    },
    "production_deploy": {
        "primary": "cpanel-deployer",
        "triggers": ["deploy", "production", "A2", "cPanel", "docroot"],
        "condition": "target is A2 Hosting or HTML files"
    },
    "database_pipeline": {
        "primary": "pg-enricher",
        "triggers": ["step", "pipeline", "enrichment", "SQL", "PostgreSQL"],
        "condition": "target involves database or pipeline"
    },
    "scraping_task": {
        "primary": "madr-scraper",
        "triggers": ["scrape", "MADR", "agroevolution", "county", "listing"],
        "condition": "target is agricultural/real estate scraping"
    },
    "security_review": {
        "primary": "cso-reviewer",
        "triggers": ["security", "audit", "OWASP", "deploy", "endpoint", "vulnerability"],
        "condition": "before production or new endpoint"
    },
    "complex_analysis": {
        "primary": "oracle",
        "triggers": ["debug", "analyze", "review", "complex", "bug", "architecture"],
        "condition": "difficult problem requiring deep reasoning"
    }
}
```

### Fallback Chain When Z.AI Unavailable
1. Use native Claude (Haiku/Sonnet/Opus) directly
2. Call appropriate specialized subagent
3. If subagent unavailable, use oracle for reasoning
4. Cache results to avoid repeated API calls

## Recommendation

**Do NOT rely on Z.AI connectivity.** It's a nice-to-have for redundancy but:
- The system works fine without it
- Native Claude models are more capable
- Specialized subagents cover all critical workflows

**Next Steps**:
1. Document z.ai as "optional" service (not critical path)
2. Implement smart subagent dispatch based on keywords/task type
3. Set up monitoring for goose/z.ai if we want to restore it later
4. Focus on maximizing native Claude integration

