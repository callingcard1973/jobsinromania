# Sync ISCIR lead tables laptop(master) -> raspibig. Small tables only (~5K rows);
# companies_master (2.9M) is refreshed manually on monthly scrape, not here.
# Schedule: Windows Task Scheduler "SyncIscirDB" daily 03:45 (after DeltaSync 03:30).
$ErrorActionPreference = "Stop"
$bin   = "C:\Users\apami\pg18\bin"
$env:PGPASSWORD = "tudor"
$dump  = "$bin\pg_dump.exe"
$psql  = "$bin\psql.exe"
$tmp   = "$env:TEMP\iscir_sync.sql"

# iscir_* tables on laptop
$tables = & $psql -h localhost -p 5433 -U tudor -d romania -Atc `
  "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'iscir_%';"

if (-not $tables) { Write-Host "no iscir_ tables found"; exit 1 }
$tArgs = $tables -split "`n" | Where-Object { $_ } | ForEach-Object { "-t"; $_ }

# dump (clean: drop+recreate) from laptop
& $dump -h localhost -p 5433 -U tudor -d romania --clean --if-exists $tArgs -f $tmp
# restore to raspibig
& $psql -h 192.168.100.21 -p 5432 -U tudor -d romania -q -f $tmp
Remove-Item $tmp -Force

$n = ($tables -split "`n" | Where-Object { $_ }).Count
Write-Host "synced $n iscir_ tables laptop -> raspibig $(Get-Date -Format s)"
