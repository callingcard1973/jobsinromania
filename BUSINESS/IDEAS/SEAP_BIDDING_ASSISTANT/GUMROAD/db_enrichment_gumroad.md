# 33M Company Database — EU Recruitment Prospecting Setup

**Price:** €500 one-time setup

---

## Description

Most recruitment agencies waste weeks scraping company websites, buying outdated lists, or manually exporting from LinkedIn. This setup gives you a working PostgreSQL database of 33 million companies across 28 EU countries — already cleaned, deduplicated, and enriched with emails, phone numbers, revenue tiers, sector classifications, and lead scores.

The pipeline is built on open data: national business registries (ONRC Romania, Brønnøysund Norway, AJPES Slovenia, and 25 others), EU procurement awards (6.2M TED records), ANOFM employer filings, and pattern-based email enrichment for domains without public contacts. The result is a prospecting database that a typical agency would spend 6-12 months and €10,000+ to build from scratch.

Setup includes: PostgreSQL schema installation, data import scripts, email enrichment pipeline (MX validation + domain pattern matching), lead scoring formula (max 100 points based on company size, revenue, procurement activity, and email quality), and campaign-ready CSV exports segmented by country and sector.

Designed for agencies placing workers in construction, manufacturing, logistics, hospitality, and care sectors across the EU. The same database structure is used in active campaigns sending 2,000+ emails per day.

After setup you own the database and all scripts. No subscription, no per-seat fees, no vendor lock-in.

---

## What You Get

- **33M company records** across 28 EU countries with name, address, sector (NACE/CAEN), registration number, and website where available
- **Email enrichment pipeline** — async MX validation for 1M+ emails, domain pattern matching (info@, jobs@, hr@) for companies without public contacts, quality tier scoring (1-4)
- **Lead scoring formula** — configurable 100-point score combining company size, 3-year revenue growth, TED procurement wins, email quality, and recency of activity
- **Campaign-ready exports** — pre-built SQL views and Python export scripts segmented by country, sector, and lead score threshold; outputs directly to CSV for Brevo, Mailchimp, or any bulk sender
- **Full documentation and runbook** — step-by-step setup guide, schema reference, troubleshooting notes, and example queries for the 10 most common prospecting scenarios

---

## Frequently Asked Questions

**Q: What are the system requirements?**
A: PostgreSQL 14 or higher, Python 3.10+, and at least 500GB of disk space for the full dataset. A dedicated server or VPS with 8GB RAM is recommended for comfortable query performance. The setup scripts are tested on Ubuntu 22.04 and Windows 11 with WSL2.

**Q: Does this include email sending infrastructure, or just the database?**
A: Database and enrichment pipeline only. The setup does not include a Brevo account, SMTP server, or campaign orchestration scripts. If you need the full sending stack (Postfix + DKIM + Brevo relay + campaign scheduler), that is available as a separate engagement — contact tudor@interjob.ro to discuss.

**Q: How current is the data, and how do I keep it updated?**
A: The base dataset reflects registrations current to Q1 2026. Incremental update scripts are included for the three highest-volume sources (Romania ONRC, Norway Brønnøysund, TED awards). Running them monthly keeps the database within acceptable drift for recruitment prospecting purposes. Full re-imports are not necessary after initial setup.

---

## How to Order

1. Purchase via this Gumroad link — you will receive a confirmation email within minutes
2. Reply with your server details (OS, PostgreSQL version, available disk) and your primary target countries and sectors
3. Setup is delivered as a ZIP archive containing schema SQL, import scripts, enrichment pipeline, and documentation
4. Optional: 1-hour onboarding call via Google Meet to walk through first query and export (included in the price)

Questions before ordering? Email tudor@interjob.ro.
