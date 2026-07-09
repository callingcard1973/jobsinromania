param([string]$RaspiHost="192.168.100.20",[string]$User="tudor",[string]$Pw="RASPI_PW_REDACTED")
$ts=Get-Date -Format "yyyyMMdd_HHmmss"
$outDir=Join-Path $PSScriptRoot "DATA\RASPI"; if(!(Test-Path $outDir)){New-Item -ItemType Directory -Path $outDir|Out-Null}
$outFile=Join-Path $outDir "raspi_task1_archive_$ts.txt"
$remote=@'
echo "=== BEFORE: csv dir listing ==="
ls -la /opt/ACTIVE/ANOFM_DATA/csv/ | grep -i manual || echo "(no manual files found in main listing)"
echo "=== full listing ==="
ls -la /opt/ACTIVE/ANOFM_DATA/csv/
echo "=== mkdir archive ==="
mkdir -p /opt/ACTIVE/ANOFM_DATA/csv/_archive/ && echo "archive dir ok"
echo "=== MOVE manual files ==="
shopt -s nullglob
moved=0
for f in /opt/ACTIVE/ANOFM_DATA/csv/anofm_raw_manual_*.csv; do
  mv -v "$f" /opt/ACTIVE/ANOFM_DATA/csv/_archive/ && moved=$((moved+1))
done
echo "moved_count=$moved"
echo "=== AFTER: main dir manual check ==="
ls -la /opt/ACTIVE/ANOFM_DATA/csv/ | grep -i manual || echo "(no manual files remain in main dir)"
echo "=== AFTER: archive dir listing ==="
ls -la /opt/ACTIVE/ANOFM_DATA/csv/_archive/
echo "=== DONE TASK1 ==="
'@
$remoteLf=$remote -replace "`r`n","`n"
$b64=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($remoteLf))
$plinkArgs=@("-batch","-pw",$Pw,"$User@$RaspiHost","echo $b64 | base64 --decode | bash")
$res= try { & plink @plinkArgs 2>&1 } catch { "EROARE plink: $_" }
("TASK1 ARCHIVE REPORT $ts`n"+($res -join "`n"))|Out-File -FilePath $outFile -Encoding UTF8
Write-Host "Raport: $outFile"
