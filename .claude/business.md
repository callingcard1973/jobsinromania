# business.md — Business Projects, Publishing, Daily Commands

## SEAP Bidding Assistant (IDEA-160, LIVE)

**Location:** `D:\MEMORY\BUSINESS\IDEAS\SEAP_BIDDING_ASSISTANT\`
- `seap_scraper.py` — scrape e-licitatie.ro (2019-2026)
- `bid_analyzer.py` — CPV/keyword → top winners, price stats from ted_awards
- `bid_writer.py` — CLI: generate bid proposal in Romanian via LM Studio :1234
- `bid_api.py` — FastAPI port 5077: POST /analyze + POST /write
- Model: EUR 200-500/proposal + 5% success fee

```bash
python bid_writer.py --cpv 45233140 --title "Lucrari asfaltare" --buyer "CJ Ilfov" --value 2000000
python bid_api.py  # port 5077
```

## Publishing Setup (LIVE)

Email: apaminerala@yahoo.com | Password: 5c5Kr1&C&d2Jr8da
Platforms: Lulu (INSCRIS), Amazon KDP, Draft2Digital, BookVault
Code: `D:\MEMORY\BUSINESS\TUDOR SEICARESCU LIFE STRATEGY\PRINTING\` — lulu_client.py + stripe_handler.py
**Missing**: Lulu API client_id/secret (get from lulu.com/account/api)

First book: "European Jobs Guide for Nepali Workers" — 2 days, €9.99 KDP + €19 Gumroad
Other Gumroad products: Norway Construction Winners (€49), RO Insolvent Companies (€79), RO Farms (€29), SEAP Winners (€59)

## Delecroix Partnership

**Dosar**: `D:\MEMORY\BUSINESS\COOP\DELECROIX\claude.md`
Delecroix FR produce harvesting belts/trailers/sorting stations. Tudor = business finder (~10% commission).
Distributor RO: Agri Alianta (CONTRACTED, 6 branches, 0755 405 555)
Revenue: 5K-60K EUR/year (5-35 units × ~1,500 EUR commission)
Contact: Toubeaux +33 6 08 09 97 20, contact@delecroix-harvesting.com
**Rule**: Never name Delecroix publicly on sites.

## Second Brain

Vault: `D:\MEMORY\CODE\INFRA\SECOND_BRAIN\vault\`
- SOUL.md — agent rules | MEMORY.md — active projects | HABITS.md — 5 daily pillars
- Scripts: `scripts/morning_digest.py` → PG18 + Telegram digest
- CLI: `python scripts/query.py pg warm-leads|solonet|campaigns`

## IDEAS

- **MASTER.csv**: `D:\MEMORY\BUSINESS\IDEAS\MASTER.csv` — 159 ideas, source of truth
- 102 unique active (57 merged), flat dirs with clear names, no IDEA-NNN prefix
- Each dir has `claude.md` with purpose + revenue estimate

## Daily Slash Commands

Defined in `~/.claude/commands/`:

### /morning
Check: (1) raspibig service health via SSH, (2) today's campaign stats from PG, (3) new warm leads, (4) HABITS.md pillars.
`SSH: tudor@192.168.100.21` | `PGPASSWORD=tudor psql -U tudor -h 127.0.0.1 -p 5433 -d interjob_master`

### /ship
Deploy: (1) git add + commit, (2) SCP to raspibig /opt/ACTIVE/, (3) restart service, (4) verify.

### /review
Code review: file sizes (<250 lines), security (no hardcoded creds), patterns match style.

### /standup
Report: git log --since=midnight, systemctl list-units --state=running on raspibig, blockers.

## Key Rules (Sites + Content)

- No WhatsApp on sites
- No member counts on OIPA
- CTA = "Write a short note" → email
- Never auto-publish articles to WordPress — draft only, publish on explicit approval
- cPanel DNS: edit_zone_record ADDS duplicates — always delete+add, re-query indices between deletions
- WordPress MCP: registered in settings.json as "wordpress" — direct WP management from Claude

## SDD (Spec-Driven Development)

Local: `D:\MEMORY\openspec/` + `D:\MEMORY\.atl/skill-registry.md`
raspibig: `/opt/openspec/` + `/opt/.atl/skill-registry.md`
Commands: `/sdd-explore`, `/sdd-propose`, `/sdd-spec`, `/sdd-design`, `/sdd-tasks`, `/sdd-apply`, `/sdd-verify`, `/sdd-archive`
