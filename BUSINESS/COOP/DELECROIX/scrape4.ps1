[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Results = @()

# 1. Agritech - get harvesting machines page 2
Write-Output "===== AGRITECH PAGE 2 ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.agritech.com.ro/category/recoltare-si-ambalare/masini-de-recoltat-legume/page/2/' -TimeoutSec 15 -UseBasicParsing
    $clean = $r.Content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&euro;', 'EUR '
    $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 15 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|[{}]|//|\.)' }
    $lines | Where-Object { $_ -match 'recolt|remorc|banda|sortar|legum|pret|lei|RON|EUR|marca|brand|produc|fabric|import' } | Select-Object -First 30 | ForEach-Object { $_.Trim() }
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== AGRITECH SORTARE ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.agritech.com.ro/category/recoltare-si-ambalare/sortare-si-conditionare-recoltare-si-ambalare/' -TimeoutSec 15 -UseBasicParsing
    $clean = $r.Content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&euro;', 'EUR '
    $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 15 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|[{}]|//|\.)' }
    $lines | Where-Object { $_ -match 'recolt|remorc|banda|sortar|legum|pret|lei|RON|EUR|marca|brand|produc|fabric|import|benz|convey' } | Select-Object -First 30 | ForEach-Object { $_.Trim() }
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== GREENGARDEN ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.greengarden.ro' -TimeoutSec 15 -UseBasicParsing
    Write-Output "Status: $($r.StatusCode) Title: "
    $titleMatch = [regex]::Match($r.Content, '<title>(.*?)</title>')
    Write-Output $titleMatch.Groups[1].Value
    # Get all links
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'recolt|harvest|legum|band|sort|convey|remorc' } | Select-Object -First 20
    Write-Output "--- All product/menu links ---"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'categor|product|magazin|utilaj|echip|shop' } | Select-Object -First 30
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== MARCOSER ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.marcoser.ro' -TimeoutSec 15 -UseBasicParsing
    Write-Output "Status: $($r.StatusCode)"
    $titleMatch = [regex]::Match($r.Content, '<title>(.*?)</title>')
    Write-Output "Title: $($titleMatch.Groups[1].Value)"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'recolt|harvest|legum|band|sort|convey|remorc|utilaj|product|categor' } | Select-Object -First 20
    Write-Output "--- All links ---"
    $r.Links | ForEach-Object { $_.href } | Select-Object -First 40
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== EQINTO ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.eqinto.eu' -TimeoutSec 15 -UseBasicParsing
    Write-Output "Status: $($r.StatusCode)"
    $titleMatch = [regex]::Match($r.Content, '<title>(.*?)</title>')
    Write-Output "Title: $($titleMatch.Groups[1].Value)"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'recolt|harvest|legum|band|sort|convey|remorc|utilaj|product|categor' } | Select-Object -First 20
    Write-Output "--- All links ---"
    $r.Links | ForEach-Object { $_.href } | Select-Object -First 40
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== AGRIALIANTA ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.agrialianta.com' -TimeoutSec 15 -UseBasicParsing
    Write-Output "Status: $($r.StatusCode)"
    $titleMatch = [regex]::Match($r.Content, '<title>(.*?)</title>')
    Write-Output "Title: $($titleMatch.Groups[1].Value)"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'recolt|harvest|legum|band|sort|convey|remorc|utilaj|product|categor' } | Select-Object -First 20
    Write-Output "--- All links ---"
    $r.Links | ForEach-Object { $_.href } | Select-Object -First 40
} catch { Write-Output "ERROR: $($_.Exception.Message)" }
