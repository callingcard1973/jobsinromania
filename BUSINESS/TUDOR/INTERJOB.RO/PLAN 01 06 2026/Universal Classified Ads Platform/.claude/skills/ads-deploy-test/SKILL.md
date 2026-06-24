---
name: ads-deploy-test
description: Use when deploying or testing the Universal Classified Ads Platform — run the 29 pytest suite, deploy laptop → raspibig, and verify cifn.eu. Triggers — "deploy classified ads", "run ads tests", "test the ads platform", "redeploy cifn.eu ads", "verify ads deploy".
---

# ads-deploy-test

Deploy + test the FastAPI classified ads platform (source on laptop, runs on raspibig:8000, frontend cifn.eu).

## Paths
- Source: `D:\MEMORY\CODE\ACTIVE\Universal Classified Ads Platform`
- Production: `/opt/ACTIVE/classified-ads` (raspibig)
- DB: PostgreSQL `classified_ads` on raspibig:5432

## Steps

### 1. Test locally (must be 29 passing)
```bash
cd "D:\MEMORY\CODE\ACTIVE\Universal Classified Ads Platform"
python -m pytest tests/ -v
```
Abort deploy if any test fails. (1 known WARNING is acceptable.)

### 2. Deploy laptop → raspibig
```powershell
cd "D:\MEMORY\CODE\ACTIVE\Universal Classified Ads Platform"
.\deploy.ps1 "<commit message>"
```
Falls back to manual sync via plink if deploy.ps1 is unavailable. Never push/commit unless the user asked.

### 3. Verify on raspibig
```bash
plink -batch -pw 'bucare' tudor@192.168.100.21 "cd /opt/ACTIVE/classified-ads && python -m pytest tests/ -q"
plink -batch -pw 'bucare' tudor@192.168.100.21 "curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/health"
```
Expect `200`.

### 4. Verify cifn.eu frontend
```bash
curl -s -o /dev/null -w '%{http_code}' https://cifn.eu
```
Expect `200`. cifn.eu WP changes go through cPanel API only — never SSH/FTP to A2.

## Guardrails
- Quote every path (spaces).
- Do NOT flip WP_ENABLED / POSTHOG_ENABLED / Stripe on without explicit approval.
- Do NOT run DB DROP/CREATE against production; archive-first + approval if ever needed.
- Report results, then stop.
