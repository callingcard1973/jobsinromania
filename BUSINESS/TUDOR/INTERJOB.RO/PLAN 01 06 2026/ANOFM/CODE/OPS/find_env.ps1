param([string]$H="192.168.100.21",[string]$User="tudor",[string]$Pw="RASPI_PW_REDACTED")
$ts=Get-Date -Format "yyyyMMdd_HHmmss"
$o=Join-Path $PSScriptRoot "DATA\RASPI"; if(!(Test-Path $o)){New-Item -ItemType Directory -Path $o|Out-Null}
$f=Join-Path $o "raspi_findenv_$ts.txt"
$remote=@'
echo "=== files containing GMAIL_USER under /opt/ACTIVE ==="
grep -rl "GMAIL_USER" /opt/ACTIVE 2>/dev/null | grep -E "\.env|\.sh" | head -20
echo "=== all .env files mentioning GMAIL (any var) ==="
for ff in $(find /opt/ACTIVE -name ".env" 2>/dev/null); do
  if grep -qi "GMAIL" "$ff" 2>/dev/null; then echo "--- $ff ---"; grep -iE "GMAIL_USER|GMAIL_APP_PASSWORD|GMAIL_PASS|SMTP_USER|SMTP_PASS" "$ff" 2>/dev/null | sed "s/=.*/=<redacted>/"; fi
done
echo "=== /opt/ACTIVE/ANOFM/.env exists? ==="
if [ -f /opt/ACTIVE/ANOFM/.env ]; then echo YES; grep -iE "GMAIL_USER|GMAIL_APP_PASSWORD" /opt/ACTIVE/ANOFM/.env | sed "s/=.*/=<redacted>/"; else echo NO; fi
echo "=== /opt/ACTIVE/EMAIL/CAMPAIGNS/.env exists? ==="
if [ -f /opt/ACTIVE/EMAIL/CAMPAIGNS/.env ]; then echo YES; grep -iE "GMAIL_USER|GMAIL_APP_PASSWORD" /opt/ACTIVE/EMAIL/CAMPAIGNS/.env | sed "s/=.*/=<redacted>/"; else echo NO; fi
echo "=== /opt/ACTIVE/.env GMAIL vars ==="
if [ -f /opt/ACTIVE/.env ]; then grep -iE "GMAIL_USER|GMAIL_APP_PASSWORD|GMAIL" /opt/ACTIVE/.env | sed "s/=.*/=<redacted>/"; else echo "NO /opt/ACTIVE/.env"; fi
echo "=== all .env files with GMAIL_APP_PASSWORD specifically (paths only) ==="
grep -rl "GMAIL_APP_PASSWORD" /opt/ACTIVE 2>/dev/null | grep "\.env" | head
echo "=== DONE ==="
'@
$lf=$remote -replace "`r`n","`n"; $b=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($lf))
$a=@("-batch","-pw",$Pw,"$User@$H","echo $b | base64 --decode | bash")
$r= try { & plink @a 2>&1 } catch { "ERR $_" }
("host=$H`n"+($r -join "`n"))|Out-File $f -Encoding UTF8; Write-Host $f
