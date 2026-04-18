[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Output "===== EQINTO - LEGUMICULTURA ====="
try {
    $r = Invoke-WebRequest -Uri 'http://www.eqinto.eu/product-category/legumicultura/' -TimeoutSec 15 -UseBasicParsing
    $clean = $r.Content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&#8211;', '-' -replace '&#8217;', "'" -replace '&euro;', 'EUR '
    $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 10 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|[{}]|//|\.)' -and $_.Trim() -notmatch 'width|margin|padding|display|position|border|color|font|background|float' }
    $lines | Where-Object { $_ -match 'recolt|band|sort|legum|convey|harvest|remorc|pret|lei|RON|EUR|price|marca|brand|produc|fabric|import|distrib|calibr|spal|ambal|PIORO|solar|sere|rotosap|seman|plantat|motocult' } | Select-Object -First 40 | ForEach-Object { $_.Trim() }
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== EQINTO - LEGUMICULTURA LINKS ====="
try {
    $r = Invoke-WebRequest -Uri 'http://www.eqinto.eu/product-category/legumicultura/' -TimeoutSec 15 -UseBasicParsing
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'legumicultura' } | Select-Object -First 30
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== EQINTO - UTILAJE RECOLTAT LIVEZI ====="
try {
    $r = Invoke-WebRequest -Uri 'http://www.eqinto.eu/product-category/vii-si-livezi/utilaje-de-recoltat/' -TimeoutSec 15 -UseBasicParsing
    $clean = $r.Content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&#8211;', '-'
    $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 10 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|[{}]|//|\.)' -and $_.Trim() -notmatch 'width|margin|padding|display|position|border|color|font|background|float' }
    $lines | Select-Object -First 40 | ForEach-Object { $_.Trim() }
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== AGRIALIANTA - ALL PRODUCTS ====="
try {
    $r = Invoke-WebRequest -Uri 'https://www.agrialianta.com/agricultura/produse/' -TimeoutSec 15 -UseBasicParsing
    $r.Links | ForEach-Object { $_.href } | Where-Object { $_ -match 'produs|product|recolt|harvest|legum|band|sort|remorc|utilaj' } | Select-Object -First 50
    $clean = $r.Content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&#8211;', '-'
    $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 10 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|[{}]|//|\.)' -and $_.Trim() -notmatch 'width|margin|padding|display|position|border|color|font|background|float' }
    $lines | Where-Object { $_ -match 'recolt|band|sort|legum|convey|harvest|remorc|pret|lei|RON|EUR|price|marca|brand|produc|fabric|import|distrib|tractor|Kubota|Sampo|Kverneland|Amazone|Lemken' } | Select-Object -First 30 | ForEach-Object { $_.Trim() }
} catch { Write-Output "ERROR: $($_.Exception.Message)" }

Write-Output "`n===== EQINTO - REMORCI AGRICOLE ====="
try {
    $r = Invoke-WebRequest -Uri 'http://www.eqinto.eu/product-category/cultura-mare/remorci-agricole/remorci-multifunctionale/' -TimeoutSec 15 -UseBasicParsing
    $clean = $r.Content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&#8211;', '-'
    $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 10 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|[{}]|//|\.)' -and $_.Trim() -notmatch 'width|margin|padding|display|position|border|color|font|background|float' }
    $lines | Where-Object { $_ -match 'remorc|pret|lei|RON|EUR|price|ton|capacit|marca|brand|produc|descarc|bascul' } | Select-Object -First 30 | ForEach-Object { $_.Trim() }
    Write-Output "--- PRODUCT NAMES ---"
    $lines | Where-Object { $_.Trim().Length -gt 15 } | Select-Object -First 30 | ForEach-Object { $_.Trim() }
} catch { Write-Output "ERROR: $($_.Exception.Message)" }
