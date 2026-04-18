[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# EQINTO - vegetable processing equipment and agriculture section
Write-Output "===== EQINTO - UTILAJE PROCESARE LEGUME FRUCTE ====="
try {
    $r = Invoke-WebRequest -Uri 'http://www.eqinto.eu/product-category/utilaje-procesare-legume-fructe/' -TimeoutSec 15 -UseBasicParsing
    $clean = $r.Content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&#8211;', '-' -replace '&#8217;', "'" -replace '&euro;', 'EUR ' -replace '&#8220;', '"' -replace '&#8221;', '"'
    $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 10 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|[{}]|//|\.)' }
    $lines | Where-Object { $_ -match 'recolt|band|sort|legum|convey|harvest|remorc|pret|lei|RON|EUR|price|marca|brand|produc|benz|loader|calibr|spal|ambal' } | Select-Object -First 30 | ForEach-Object { $_.Trim() }
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== EQINTO - CULTURA MARE ====="
try {
    $r = Invoke-WebRequest -Uri 'http://www.eqinto.eu/product-category/cultura-mare/' -TimeoutSec 15 -UseBasicParsing
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'legum|recolt|band|sort|harvest|remorc' } | Select-Object -First 20
    Write-Output "--- All subcategories ---"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'product-category' } | Select-Object -First 40
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== AGRIALIANTA - AGRICULTURA ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.agrialianta.com/agricultura/' -TimeoutSec 15 -UseBasicParsing
    Write-Output "Status: $($r.StatusCode)"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'recolt|harvest|legum|band|sort|convey|remorc|utilaj|product' } | Select-Object -First 20
    Write-Output "--- All links ---"
    $r.Links | ForEach-Object { $_.href } | Select-Object -First 40
    $clean = $r.Content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&#8211;', '-'
    $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 15 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|[{}]|//|\.)' }
    $lines | Where-Object { $_ -match 'recolt|band|sort|legum|convey|harvest|remorc|pret|lei|RON|EUR|price|marca|brand|produc|fabric|import|distrib' } | Select-Object -First 20 | ForEach-Object { $_.Trim() }
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== GREENGARDEN - CATALOG ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.greengarden.ro/produse/' -TimeoutSec 15 -UseBasicParsing
    Write-Output "Status: $($r.StatusCode)"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'recolt|harvest|legum|band|sort|convey|remorc|utilaj|masin' } | Select-Object -First 20
    Write-Output "--- All category links ---"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'categor|produs|utilaj' } | Select-Object -First 40
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== MARCOSER - PRODUSE ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.marcoser.ro/produse/' -TimeoutSec 15 -UseBasicParsing
    Write-Output "Status: $($r.StatusCode)"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'recolt|harvest|legum|band|sort|convey|remorc|utilaj|masin' } | Select-Object -First 20
    Write-Output "--- All category links ---"
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'produs' } | Select-Object -First 50
} catch { Write-Output "ERROR: $($_.Exception.Message)" }
