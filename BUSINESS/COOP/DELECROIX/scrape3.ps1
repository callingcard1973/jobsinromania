# Scrape dealer sites - encoding safe
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$urls = @(
    @{url='https://www.agritech.com.ro/recoltare-si-ambalare/masini-de-recoltat-legume/masina-autopropulsata-pentru-recoltat-morcovi-cu-descarcare-in-remorca/'; name='agritech-morcovi'},
    @{url='https://www.agritech.com.ro/recoltare-si-ambalare/masini-de-recoltat-legume/rosii-masini-de-recoltat-legume/banda-colectoare-cu-statie-de-sortare/'; name='agritech-banda'},
    @{url='https://www.agritech.com.ro/category/recoltare-si-ambalare/sortare-si-conditionare-recoltare-si-ambalare/'; name='agritech-sortare'},
    @{url='https://www.greengarden.ro'; name='greengarden'},
    @{url='https://www.marcoser.ro'; name='marcoser'},
    @{url='https://www.eqinto.eu'; name='eqinto'},
    @{url='https://www.agrialianta.com'; name='agrialianta'}
)

foreach ($item in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $item.url -TimeoutSec 15 -UseBasicParsing
        $content = $r.Content
        Write-Output "=== $($item.name) ==="
        Write-Output "URL: $($item.url) | Status: $($r.StatusCode) | Length: $($content.Length)"
        
        # Clean HTML
        $clean = $content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&euro;', 'EUR '
        $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 10 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|[{}]|//)' }
        
        # Price lines
        $priceLines = $lines | Where-Object { $_ -match 'lei|RON|EUR|euro|pret|price|cost' }
        if ($priceLines) {
            Write-Output "--- PRICES ---"
            $priceLines | ForEach-Object { $_.Trim() } | Select-Object -First 10
        }
        
        # Brand lines
        $brandLines = $lines | Where-Object { $_ -match 'marca|brand|fabrica|produc|import|distrib|Asa-Lift|Dewulf|Grimme|Miedema|Volmer|Delecroix|Standen|Wijnenga|Ferrari|Torno|Baselier' }
        if ($brandLines) {
            Write-Output "--- BRANDS ---"
            $brandLines | ForEach-Object { $_.Trim() } | Select-Object -First 10
        }
        
        # Meaningful content
        Write-Output "--- CONTENT ---"
        $lines | Select-Object -First 25 | ForEach-Object { $_.Trim() }
        Write-Output "---END---`n"
    } catch {
        Write-Output "ERROR: $($item.name) - $($_.Exception.Message)`n---END---`n"
    }
}
