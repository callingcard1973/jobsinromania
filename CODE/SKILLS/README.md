# Skills Directory

This directory contains Claude Code skills for InterJob operations.

## Subagents

All subagents are defined in `.claude/agents/`:

- **brevo-sender.md** — Email campaigns, quota, bounce monitoring (13 Brevo accounts)
- **cpanel-deployer.md** — A2 Hosting production deployments (cPanel API only)
- **pg-enricher.md** — PostgreSQL enrichment pipeline steps 1-46
- **madr-scraper.md** — agroevolution.com MADR land listings (9,658 listings)
- **cso-reviewer.md** — Pre-deploy security audits (OWASP Top 10)

## Usage

```bash
# Import/dispatch a subagent
Agent(description="Send campaign", subagent_type="brevo-sender", prompt="...")
Agent(description="Deploy to A2", subagent_type="cpanel-deployer", prompt="...")
Agent(description="Query enrichment", subagent_type="pg-enricher", prompt="...")
Agent(description="Scrape MADR", subagent_type="madr-scraper", prompt="...")
Agent(description="Security review", subagent_type="cso-reviewer", prompt="...")
```

## Syncing from raspibig

To pull additional skills from raspibig `/opt/ACTIVE/INFRA/SKILLS/`:

1. **Set up SSH key** (currently missing):
   ```bash
   # Generate new key or import existing
   ssh-keygen -t rsa -f ~/.ssh/raspibig_key
   ssh-copy-id -i ~/.ssh/raspibig_key.pub -p 22 tudor@192.168.100.21
   ```

2. **Sync skills from raspibig**:
   ```bash
   rsync -avz tudor@192.168.100.21:/opt/ACTIVE/INFRA/SKILLS/*.py ./
   ```

3. **Register in Claude Code**:
   - Add each skill to `.claude/settings.json` under `skills`
   - Or keep in `.claude/agents/` for automatic discovery

## Local Sync Status

✓ All 5 subagents defined locally
✓ Ready to use
⏳ Awaiting SSH key setup for full raspibig sync
