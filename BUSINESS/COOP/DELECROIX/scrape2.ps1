# Scrape article content from agritech and other dealers
$urls = @(
    @{url='https://www.agritech.com.ro/recoltare-si-ambalare/masini-de-recoltat-legume/masina-autopropulsata-pentru-recoltat-morcovi-cu-descarcare-in-remorca/'; name='agritech-morcovi'},
    @{url='https://www.agritech.com.ro/recoltare-si-ambalare/masini-de-recoltat-legume/rosii-masini-de-recoltat-legume/banda-colectoare-cu-statie-de-sortare/'; name='agritech-banda-sortare'},
    @{url='https://www.agritech.com.ro/category/recoltare-si-ambalare/sortare-si-conditionare-recoltare-si-ambalare/'; name='agritech-sortare'},
    @{url='https://www.greengarden.ro'; name='greengarden-home'},
    @{url='https://www.marcoser.ro'; name='marcoser-home'},
    @{url='https://www.eqinto.eu'; name='eqinto-home'},
    @{url='https://www.agrialianta.com'; name='agrialianta-home'}
)

foreach ($item in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $item.url -TimeoutSec 15 -UseBasicParsing
        $content = $r.Content
        # Try to find article/post content
        $patterns = @('class="entry-content"', 'class="post-content"', 'class="article"', 'class="product"', 'class="item"', '<article', 'class="content"')
        
        Write-Output "=== $($item.name) ==="
        Write-Output "URL: $($item.url)"
        Write-Output "Status: $($r.StatusCode)"
        Write-Output "Content length: $($content.Length)"
        
        # Extract all text content, looking for meaningful paragraphs
        $clean = $content -replace '<script[^>]*>.*?</script>', '' -replace '<style[^>]*>.*?</style>', '' -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&lt;', '<' -replace '&gt;', '>' -replace '&#8220;', '"' -replace '&#8221;', '"' -replace '&#8211;', '-' -replace '&#8217;', "'" -replace '&#8364;', 'EUR' -replace '&euro;', 'EUR' -replace 'lei', ' RON '
        $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 10 } | Where-Object { $_.Trim() -notmatch '^(function|var |if\(|jQuery|window\.|document|{|}|\/\/)' }
        
        # Look for price-related content
        $priceLines = $lines | Where-Object { $_ -match 'lei|RON|EUR|euro|pret|price|cost|€' }
        if ($priceLines) {
            Write-Output "--- PRICES FOUND ---"
            $priceLines | ForEach-Object { $_.Trim() }
        }
        
        # Look for brand-related content
        $brandLines = $lines | Where-Object { $_ -match 'marca|brand|fabrica|produc|import|distribui|Asa-Lift|Dewulf|Grimme|Miedema|Volmer|Delecroix|Standen|Wijnenga|Ferrari' }
        if ($brandLines) {
            Write-Output "--- BRANDS FOUND ---"
            $brandLines | ForEach-Object { $_.Trim() }
        }
        
        # Show first meaningful content lines
        Write-Output "--- CONTENT SAMPLE ---"
        $lines | Select-Object -First 20 | ForEach-Object { $_.Trim() }
        Write-Output "`n---END---`n"
    } catch {
        Write-Output "ERROR: $($item.name) - $($_.Exception.Message)`n"
    }
}
