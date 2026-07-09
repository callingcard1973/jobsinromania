param([string]$H="192.168.100.21",[string]$User="tudor",[string]$Pw="RASPI_PW_REDACTED")
$ts=Get-Date -Format "yyyyMMdd_HHmmss"
$o=Join-Path $PSScriptRoot "DATA\RASPI"; if(!(Test-Path $o)){New-Item -ItemType Directory -Path $o|Out-Null}
$f=Join-Path $o "raspi_bigemail_$ts.txt"
$remote=@'
set +e
echo "=== ENV grep GMAIL_MANPOWER ==="
sudo grep -hE "GMAIL_MANPOWER_DRISTOR" /opt/ACTIVE/EMAIL/CAMPAIGNS/.env 2>/dev/null
echo "=== ENV all GMAIL user/pass lines ==="
sudo grep -hiE "(GMAIL|SMTP).*(USER|PASS|MAIL|FROM)" /opt/ACTIVE/EMAIL/CAMPAIGNS/.env 2>/dev/null | grep -ivE "BREVO" | head -40
echo "=== reply_handler_silozuri usage ==="
sudo grep -nE "GMAIL_MANPOWER_DRISTOR|getenv|os.environ" /opt/ACTIVE/SILOZURI/CAMPAIGN/CODE/reply_handler_silozuri.py 2>/dev/null | head -20
'@
$lf=$remote -replace "`r`n","`n"; $b=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($lf))
$a=@("-batch","-pw",$Pw,"$User@$H","echo $b | base64 --decode | bash")
$r= try { & plink @a 2>&1 } catch { "ERR $_" }
("host=$H`n"+($r -join "`n"))|Out-File $f -Encoding UTF8; Write-Host $f
