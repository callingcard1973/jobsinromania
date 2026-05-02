# SDD Workspace: Memory

## Project Identity
- **Name**: Memory / Z.AI Root
- **Scope**: Multi-project management, automation, and central archive.
- **Base Paths**: `d:\MEMORY\Z.AI`, `d:\MEMORY\ARCHIVE`, `d:\MEMORY\SANDBOX`
- **Infrastructure**: raspibig (Ubuntu), Node-RED, PostgreSQL

## Major Projects
- **Bulgaria Procurement**: [d:\MEMORY\Z.AI\BULGARIA](d:\MEMORY\Z.AI\BULGARIA)
- **OpenSpec/SDD Skills**: [d:\MEMORY\openspec](d:\MEMORY\openspec)
- **Claude Desktop Skills**: [d:\MEMORY\.claude](d:\MEMORY\.claude)

## Infrastructure (raspibig)
- **IP**: raspibig.local
- **Role**: Primary automation and data storage host.
- **Key Directories**: `/opt/ACTIVE/`, `/opt/BACKUP/`
- **Database**: PostgreSQL (interjob_master)

## Conventions
- **Naming**: `scrape_*`, `enrich_*`, `agents/`
- **Deployment**: `deploy_to_raspibig.sh` (rsync based)
- **Monitoring**: Telegram bot alerts via Node-RED
