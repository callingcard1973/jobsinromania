# web

WordPress site management for OIPA and Hambarul.

## Scope

- `MEMORY/CODE/WEB/` — WordPress plugins, MCP servers, configuration
- `MEMORY/BUSINESS/OIPA/` — OIPA business context
- Gazduire hosting (grem01.gazduire.ro) — cPanel shared hosting

## Key Sites

- **oipa.ro** — Producer enrichment (Yoast, Antispam, Claude enricher, worker)
- **hambarulromanesc.ro** — Product marketplace enrichment (same plugins)

## Infrastructure

- Hosting: Gazduire (FTP only, no SSH)
- DB: uamkawbd_wp441 (shared MySQL)
- Access: tudor user with app passwords
- LLM: Anthropic API (claude-3-5-sonnet)

## Related

- MCP: wordpress_mcp_server.py (REST API) + raspibig_mcp_server.py (SSH)
- Worker plugin: ManageWP integration (https://orion.managewp.com/)
- Business: OIPA producer catalog, Hambarul marketplace

## Status (Apr 19, 2026)

- Both sites 200 OK, plugins deployed, LLM configured
- Worker plugin active on oipa.ro, needs activation on hambarulromanesc.ro
- All 34 junk plugins cleaned from hambarulromanesc.ro
