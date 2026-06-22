@echo off
rem Nightly two-way delta sync laptop companies_clean <-> raspibig public.companies.
rem --apply writes: adds enrichment columns on raspibig (first run), pulls new rows, pushes enrichment.
cd /d "%~dp0"
python delta_sync.py --apply all >> "%~dp0delta_sync_cron.log" 2>&1
