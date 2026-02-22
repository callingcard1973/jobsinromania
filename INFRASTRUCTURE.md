# Infrastructure Reference

**Single source of truth for all infrastructure details across 28 domains and 3 machines.**

## Machines

### Laptop (Windows 11 Pro)
- **IP (LAN)**: 192.168.100.25
- **Tailscale**: 100.81.18.34
- **Services**: LM Studio (port 1234), Claude Code, Python 3.12, Git
- **Storage**: D:\MEMORY (all projects)

### raspibig (Debian 13, aarch64)
- **IP (eth0)**: 192.168.100.21
- **IP (wlan0)**: 192.168.100.23
- **Tailscale**: 100.124.99.56
- **SSH**: `tudor@192.168.100.21` pw: `bucare`
- **RAM**: 16GB, **Storage**: 235GB NVMe (65% used)
- **Services**: PostgreSQL(5433), Node-RED(1880), nginx, fail2ban, FreeSCOUT, signal-cli, Portainer, Odoo(8069)
- **Email**: 24/7 campaigns via Brevo+A2 SMTP, bounce management
- **Scrapers**: 20 countries (EURES, Nordic, Western, Romania, UK, Poland, Moldova, etc.)
- **Claude Code**: 200+ skills at `~/.claude/skills/`

### raspi (Debian, armv7)
- **IP**: 192.168.100.20
- **Tailscale**: N/A
- **RAM**: 4GB, **Storage**: 880GB
- **SSH**: `tudor@192.168.100.20` (password-less key auth from raspibig)
- **Services**: PostgreSQL(5432), Node-RED(1880), nginx, fail2ban
- **Role**: Backup system, applicant dashboard, Fix API

## SSH Access

From **Windows laptop** to raspibig:
```bash
plink -ssh tudor@192.168.100.21 -pw bucare
# or: ssh raspibig (if key auth configured)
```

From **raspibig** to raspi:
```bash
ssh raspi  # or ssh tudor@192.168.100.20
```

## File Paths

### Laptop
- `D:\MEMORY\CLAUDE\` — all 270+ projects
- `D:\MEMORY\Z.AI\` — z.ai projects
- `D:\MEMORY\OPT\` — partial copy of raspibig /opt/
- `D:\MEMORY\ai.cmd` — Local AI CLI wrapper
- `D:\MEMORY\assistant.py` — LM Studio connector

### raspibig
- `/opt/` — root for all scrapers, email, data, skills
- `/opt/SCRAPERS/` — scrapers for 20 countries
- `/opt/EMAIL/` — Brevo + A2 SMTP campaigns (24/7)
- `/opt/SKILLS/` — 80+ raspibig skills
- `/opt/DATA/` — Enriched employer data, CV database
- `/opt/.env` — Credentials (A2 hosting, MainWP, WordPress, Yahoo, E-bloc)
- `/opt/LOGS/` — Centralized logging

### raspi
- `/opt/BACKUPS/` — Daily backups from raspibig

## Credentials

### A2 Hosting (nl1-cl8-ats1.a2hosting.com)
- **SSH**: Port 7822, user `loaiidil`, key auth
- **cPanel**: `loaiidil` (see settings.json for password)
- **SMTP**: 465/587, credentials in `OPT/opt/EMAIL/.env`
- **Docroot**: `~/domainname/` (NOT `~/public_html/`)

### Email Accounts (30 total)
- **Brevo**: 12 active campaigns, 290/day per sender
- **Gmail**: 7 warmup accounts for Yahoo recipients (see email_campaigns.md)
- **A2 SMTP**: 7 domain senders (350/day each)

### APIs
- **OpenCage**: OPENCAGE_API_KEY (geocoding)
- **LM Studio**: localhost:1234/v1/chat/completions
- **Odoo CRM**: http://raspibig:8069 (login: apaminerala@yahoo.com)

## Domains (28 Total)

**Job Sites (15)**: careworkers.eu, factoryjobs.eu, buildjobs.eu, electricjobs.eu, farmworkers.eu, horecaworkers.eu, meatworkers.eu, mechanicjobs.eu, warehouseworkers.eu, aluminumrecyclehub.com, expatsinromania.org, interjob.ro, mivromania.info, mivromania.online, nepalezi.com

**Static (5)**: internaltransfers.eu, horecaworkers2026.com, horecaworkers2026.eu, horecaworkers2026.online, weddnesday.org

**WordPress (8)**: cumparlegume.com, seicarescu.com, agroevolution.com, ajwang.org, baneasa39.com, cifn.info, haritina.com, mivromania.com

## Conventions

- SSH paths: Use `192.168.100.21`, not hostname (Tailscale routing issue)
- Windows SCP: Use forward slashes `"D:/MEMORY/path/"`
- Windows SSH: Single quotes around commands
- RTL languages (ar, ur, ps): Include `dir="rtl"` in HTML
- All apply links → `https://interjob.ro/apply.html`
- Sensitive files (do not share): `raspi.json`, `.env` files, OpenCage API key
