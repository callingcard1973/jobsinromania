# CV Generator — Handoff 2026-04-18

## What's Live

**15 job sites** each have `/cv/` with upload form + Europass CV renderer:
factoryjobs.eu/cv/, careworkers.eu/cv/, buildjobs.eu/cv/, electricjobs.eu/cv/,
farmworkers.eu/cv/, horecaworkers.eu/cv/, meatworkers.eu/cv/, mechanicjobs.eu/cv/,
warehouseworkers.eu/cv/, aluminumrecyclehub.com/cv/, expatsinromania.org/cv/,
interjob.ro/cv/, mivromania.info/cv/, mivromania.online/cv/, nepalezi.com/cv/

**API on each site:** `https://DOMAIN/cv/api.php` — PHP, same-domain, rule-based parsing
**API on raspibig:** `http://192.168.100.21:5050/parse-cv` — FastAPI, LLM (qwen2.5:1.5b), LAN only

**Flow:** Worker uploads CV → PHP extracts text → returns structured JSON → Europass CV rendered in browser → Download PDF (window.print()) → Apply Now → interjob.ro/apply.html

**Vault:** LLM parser saves every CV to `cv_leads` table in `master_applicants.db` on raspibig.

## Files

```
CODE/cv_parser/
  app.py                  FastAPI routes (port 5050)
  parser.py               Text extraction + LLM + vault save
  api.php                 PHP parser (deployed on all 15 A2 sites)
  index.html              Dark-theme frontend
  deploy_all_sites.sh     Batch redeploy to all 14 sites (not factoryjobs.eu)
  cv-parser.service       Systemd unit
  HANDOFF.md              This file
```

## Raspibig Service

```bash
sudo systemctl status cv-parser    # check
sudo systemctl restart cv-parser   # restart
curl http://localhost:5050/health  # test
```

## Redeploy After Changes

```bash
# 1. Edit api.php or index.html locally
# 2. Copy to raspibig
scp "D:/MEMORY/PHONE CAMPAIGN/CODE/cv_parser/api.php" tudor@192.168.100.21:/tmp/cv_api.php
scp "D:/MEMORY/PHONE CAMPAIGN/CODE/cv_parser/index.html" tudor@192.168.100.21:/opt/ACTIVE/PHONE_CAMPAIGN/cv_parser/index.html

# 3. Deploy to all sites
ssh tudor@192.168.100.21 'bash /opt/ACTIVE/PHONE_CAMPAIGN/deploy_all_sites.sh'
```

## Why No Public LLM API

Raspibig is behind home router with no port forwarding. LAN-only.
PHP parser runs on A2 Hosting with full HTTPS — no infrastructure needed.

## Known Limitations (PHP parser)

- Experience entries on one line (`Role - Company YYYY-YYYY`) → handled via regex
- Scanned PDF images → not supported (pdftotext text-only)
- LinkedIn URL input → currently no server-side fetch from PHP (use LLM fallback)
- Accuracy: ~80% on well-formatted CVs

## Next Steps (optional)

- Add CV count to Telegram bot (`/cv_leads` command showing count from cv_leads table)
- Add `.ro` employer detection (if CV email is `.ro`, create solonet order draft)
- PDF with real page breaks (currently relies on browser print)
