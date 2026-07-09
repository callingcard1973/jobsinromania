# Todo

## Session 2026-04-19 — DB sync + seed investors + Octogent workers tentacle

### Done
- Restarted Postgres (crashed at 09:05, back up on port 5433)
- Committed memory reorganization: commit 606d053
- import_seed_investors.py: 2,240 rows upserted (all existing, refreshed)
- sync_laptop_to_raspibig.sh: master_romania_companies (10,064,564) + seed_investors (2,308) → raspibig
- Created `workers` tentacle in Octogent + wired 3 patterns in auto_tentacle.ps1

### Key files
- D:\MEMORY\DATA\DB\import_seed_investors.py
- D:\MEMORY\DATA\DB\sync_laptop_to_raspibig.sh
- D:\MEMORY\.octogent\tentacles\workers\CONTEXT.md
- D:\MEMORY\CODE\INFRA\OCTOGENT\auto_tentacle.ps1

### Pending
- Steps 22-36 EMAIL PERSONAL pipeline (Postgres kill interrupted)
- experti_contabili CECCAR — 17K accountants, scraping needed
- Lead score formula refinement
- Postgres auto-start on boot (currently manual)

### Next steps
- Run pipeline resume batch (see CLAUDE.md)
- Deploy workers catalog to interjob.ro/workers/

## Session 2026-04-19 23:14
## Raspi data consolidation + inventory (2026-04-19)\n\n**Done:**\n- Imported buzau_enriched (45,563 rows) into romania.raspi_import via 30-col FORCE_NULL pad\n- Imported 20 sqlite DBs (44 tables, 261K rows) into interjob_master.raspi_import_sqlite\n- Fixed mem CLI slowness on raspi: 2m20s to 2.7s. Changes: MEM_ROOT=/opt/ACTIVE + added ARCHIVE/BACKUP/BACKUPS/backups/ARCHIVE_HOME_BACKUP/ARCHIVED_2026-01-06/.cache/cache to EXCLUDED_DIRS in ~/bin/mem/mem_core.py\n- Generated full raspi inventory at D:/MEMORY/ARCHIVE/raspi_inventory_2026_04_19/ (disk, PG DBs, services, cron, data files, SUMMARY.md)\n\n**Critical raspi-unique data (NOT mirrored):**\n- PG csv_raw: 3018 tables, 18.9M rows\n- PG master_db: 360 tables, 12.0M rows (raw+contacts+agencies schemas)\n- PG eures: 194K rows\n- PG romania (raspi variant, 142K, differs from laptop 208M)\n- /opt/DATA/EURES/*.csv (~1.2G country contacts)\n- /opt/DATA/csv_archive/*.csv (~2.5G SEAP/eurostat)\n- /opt/ACTIVE/ (550M live services — check git)\n- /opt/SCRAPERS/ (3.5G — check git)\n\n**Safe duplicates:**\n- /opt/BACKUPS/raspibig/ (55G) = raspibig mirror\n- /home/tudor/Documents/ (118G) = extracted to D:/MEMORY/ARCHIVE/raspi_backup_extract/\n- /home/tudor/SCRAPERS_BACKUP = /opt/SCRAPERS\n\n**Unresolved:**\n- nhs_jobs: 75K CSV loaded only 1339 rows (quoting issue, skipped)\n- 118G BACKUP_OLD + 78G Documents + 30G ARCHIVE not yet nuked (pending user approval)\n\n**Pending options offered (not executed):**\n1. pg_dump csv_raw/master_db/eures/romania -> D:/MEMORY/ARCHIVE/\n2. tar /opt/DATA/EURES + /opt/DATA/csv_archive -> D:/MEMORY/ARCHIVE/\n3. Check git status of /opt/ACTIVE + /opt/SCRAPERS\n\n**Key files:**\n- D:/MEMORY/ARCHIVE/raspi_inventory_2026_04_19/SUMMARY.md (read first)\n- D:/MEMORY/ARCHIVE/raspi_backup_extract/buzau_fix.sh, sqlite_to_pg.py\n- raspi ~/bin/mem/mem_core.py (patched), ~/.bashrc (MEM_ROOT changed)
