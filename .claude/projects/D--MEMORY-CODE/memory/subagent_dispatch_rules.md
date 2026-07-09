---
name: Subagent Dispatch Rules
description: Smart routing of tasks to specialized subagents based on keywords, patterns, and context
type: feedback
---

# Subagent Dispatch Rules

## Smart Routing Matrix

### 1. BREVO-SENDER (Sonnet Model)
**Invoked when**: Task involves email campaigns, quotas, bounce rates, sender management

**Trigger Keywords**: 
- send, campaign, email, bounce, quota, Brevo, sender, delivery, unsubscribe, engagement

**Task Patterns**:
- "Send campaign to..." → BREVO-SENDER
- "Check bounce rate..." → BREVO-SENDER
- "What's the quota..." → BREVO-SENDER
- "Monitor sender health..." → BREVO-SENDER
- "Warm up email..." → BREVO-SENDER

**Skip if**: Task is about creating email content/templates (use native Claude instead)

---

### 2. CPANEL-DEPLOYER (Haiku Model)
**Invoked when**: Deploying to A2 Hosting, managing docroots, updating HTML/PHP files

**Trigger Keywords**:
- deploy, production, A2, cPanel, docroot, HTML, PHP, file upload, website update, production deploy

**Task Patterns**:
- "Deploy HTML to warehouseworkers.eu..." → CPANEL-DEPLOYER
- "Update the landing page..." → CPANEL-DEPLOYER
- "What's the docroot for..." → CPANEL-DEPLOYER
- "Push changes to production..." → CPANEL-DEPLOYER
- "Upload CSS/JS files..." → CPANEL-DEPLOYER

**Safety**: ALWAYS invoke cso-reviewer BEFORE cpanel-deployer for any production change

---

### 3. PG-ENRICHER (Sonnet Model)
**Invoked when**: Database pipeline steps, enrichment queries, schema inspection, PostgreSQL operations

**Trigger Keywords**:
- step, pipeline, enrichment, SQL, PostgreSQL, step22, step29, query, row count, schema, interjob_master

**Task Patterns**:
- "Run step 22..." → PG-ENRICHER
- "How many companies in enrichment..." → PG-ENRICHER
- "Check what step 45 does..." → PG-ENRICHER
- "Query companies_clean table..." → PG-ENRICHER
- "Inspect database schema..." → PG-ENRICHER

**Database Connection**: Uses port 5433, user tudor, db interjob_master

---

### 4. MADR-SCRAPER (Haiku Model)
**Invoked when**: Scraping agroevolution.com, MADR land listings, county pages, parsing agricultural data

**Trigger Keywords**:
- scrape, MADR, agroevolution, county, land sale, teren, acre, hectare, price RON, agricultural listing

**Task Patterns**:
- "Scrape Alba county..." → MADR-SCRAPER
- "Parse MADR listing..." → MADR-SCRAPER
- "Update agroevolution catalog..." → MADR-SCRAPER
- "What's the listing data..." → MADR-SCRAPER
- "Total listings in Bucharest..." → MADR-SCRAPER

**Data**: 9,658 total listings across 42 counties + Bucharest

---

### 5. CSO-REVIEWER (Opus Model)
**Invoked when**: Security audits, OWASP checks, pre-deployment reviews, credential leaks

**Trigger Keywords**:
- security, audit, OWASP, vulnerability, deploy, production, endpoint, credentials, hack, breach, XSS, SQL injection

**Mandatory Triggers** (ALWAYS use):
- Before ANY production deployment
- Before launching new API endpoint
- When handling authentication/authorization
- When adding external API integration
- When dealing with sensitive data

**Task Patterns**:
- "Review this code for security..." → CSO-REVIEWER
- "Should we deploy this..." → CSO-REVIEWER
- "Check for OWASP..." → CSO-REVIEWER
- "New endpoint at /api/..." → CSO-REVIEWER (MANDATORY)

**Safety Rule**: Block deploy if critical vulnerabilities found

---

### 6. ORACLE (Opus Model)
**Invoked when**: Complex bugs, architectural decisions, deep debugging, second opinions

**Trigger Keywords**:
- debug, analyze, review, complex, bug, architecture, refactor, design, performance, optimize, "why doesn't", "what's wrong", tricky

**Task Patterns**:
- "Why is this failing..." → ORACLE
- "Second opinion on..." → ORACLE
- "How should we architect..." → ORACLE
- "What's the best approach..." → ORACLE
- "This bug is weird..." → ORACLE

**Note**: Oracle falls back to native Claude if z.ai unavailable (which it is)

---

## Dispatch Algorithm

```
IF task mentions email/Brevo/campaign/bounce
  → BREVO-SENDER
ELSE IF task mentions deploy/production/A2/docroot/HTML
  → (CSO-REVIEWER first if new code)
  → CPANEL-DEPLOYER
ELSE IF task mentions step/pipeline/SQL/enrichment/database
  → PG-ENRICHER
ELSE IF task mentions scrape/MADR/agroevolution/county/land
  → MADR-SCRAPER
ELSE IF task mentions security/audit/OWASP/vulnerability/endpoint
  → CSO-REVIEWER
ELSE IF task is complex/architectural/debugging
  → ORACLE
ELSE
  → Use native Claude directly
```

## Integration Points

### Pre-task Checks
- Is z.ai available? (It isn't - use native Claude models)
- Does task require security review? (If deploying: YES)
- Is this a known subagent pattern? (Check keywords)

### Dispatch Decision
1. Extract keywords from user prompt
2. Check against trigger patterns
3. If match found, dispatch to primary subagent
4. Pass only relevant context (don't dump full codebase)
5. Set appropriate tool scope (don't over-permit)

### Post-execution
- Was subagent successful?
- Should we escalate to oracle?
- Should we cache the result?

## When NOT to Dispatch

- Simple read operations (Grep/Glob) → Use directly
- Code explanations → Use native Claude
- Writing non-executable content → Use native Claude
- Making minor edits → Use native Claude directly
- User explicitly says "just you" → Never dispatch

## Cost Optimization

- Haiku agents (cpanel-deployer, madr-scraper) for quick, straightforward tasks
- Sonnet agents (brevo-sender, pg-enricher) for domain expertise
- Opus agents (cso-reviewer, oracle) only when necessary (security, complex problems)
- Use native Claude (Haiku default) for everything else

## Examples

| User Request | Subagent | Why |
|---|---|---|
| "Send campaign to 500 companies" | brevo-sender | Email + campaign keywords |
| "Update homepage HTML" | cso-reviewer → cpanel-deployer | Security audit first, then deploy |
| "Scrape county pages" | madr-scraper | MADR + agroevolution keywords |
| "Check pipeline step 22" | pg-enricher | step + pipeline keywords |
| "Why is bounce rate high?" | brevo-sender | Bounce + email keywords |
| "Fix authentication bug" | oracle | Complex debugging + security |
| "Refactor campaign sender" | oracle | Architecture change |
| "Explain how enrichment works" | (native Claude) | Educational, no execution |
| "Deploy API endpoint" | cso-reviewer → cpanel-deployer | MANDATORY security review |

## Status

✅ Rules defined
✅ Triggers identified
✅ Safety checks documented
⏳ Automated dispatch not yet implemented (requires Claude Code integration)
