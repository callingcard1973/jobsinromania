# EU_FUNDING — EU Grants & Funding Opportunities

Configuration-only local directory. Actual project lives on raspibig at `/opt/ACTIVE/EU_FUNDING/`.

## Status: REMOTE PROJECT — Active on raspibig

**Local**: Only `.claude/settings.local.json` (SSH permissions config)
**Remote**: Full project at `tudor@192.168.100.21:/opt/ACTIVE/EU_FUNDING/`

## Remote Structure

```
/opt/ACTIVE/EU_FUNDING/
  CLAUDE.md, openspec/, config.yaml
  SCRIPTS/           — Python automation
  CONFIG/            — wp_config.json
  TEMPLATES/         — base.html, index.html, programme.html
  ALERTS/            — Funding deadline notifications
  CAMPAIGNS/         — Outreach to beneficiaries
  RESEARCH/          — Funding program analysis
  DATA/              — Structured funding data
  OUTPUT/            — Generated HTML/CSS
```

**Database**: `cifn_eu` on raspibig PostgreSQL, table `calls` (funding calls).

## Connection to Other Projects

- **CIFN.EU** website (`cifn.info`) — WordPress portal for EU funds info
- **ASOCIATII** — NGOs as potential EU funding applicants
- **COOPERATIVA BUSINESS** — cooperative eligible for AFIR/AGRIP grants
- **PRODUS MONTAN** — AGRIP grant deadline April 23, 2026

## Access

```bash
ssh tudor@192.168.100.21 'ls /opt/ACTIVE/EU_FUNDING/'
ssh tudor@192.168.100.21 'cat /opt/ACTIVE/EU_FUNDING/CLAUDE.md'
```
