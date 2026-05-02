# Catalog Tentacle

## Scope
D:\MEMORY\CODE\CATALOG CREATE\ — HTML catalog generator system

## What It Does
Generates employer job catalogs in HTML/PDF for 28 InterJob sites.
2,665+ employers across 4 sectors: Factory 608, Construction 671, EU 1,102, CallCenter 284.

## Run
python D:\AUTOMATION\run_all_catalogs.py

## Key Files
CODE\CATALOG CREATE\templates\ — catalog HTML templates
CODE\CATALOG CREATE\themes\ — visual themes
CODE\CATALOG CREATE\tokens\ — LLM token configs

## Deploy
A2 Hosting via cPanel API. No SSH.
Doc root: ~/domainname/ (NOT ~/public_html/)

## Rules
- All apply links → interjob.ro/apply.html
- PDF via wkhtmltopdf or Playwright (laptop)
- Never auto-publish without approval
