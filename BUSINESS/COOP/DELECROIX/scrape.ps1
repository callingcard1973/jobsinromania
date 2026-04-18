$urls = @(
    'https://www.agritech.com.ro/recoltare-si-ambalare/masini-de-recoltat-legume/masina-autopropulsata-pentru-recoltat-morcovi-cu-descarcare-in-remorca/',
    'https://www.agritech.com.ro/recoltare-si-ambalare/masini-de-recoltat-legume/rosii-masini-de-recoltat-legume/banda-colectoare-cu-statie-de-sortare/',
    'https://www.agritech.com.ro/recoltare-si-ambalare/masini-de-recoltat-legume/masina-de-dislocat-morcovi/',
    'https://www.agritech.com.ro/recoltare-si-ambalare/masini-de-recoltat-legume/ceapa-masini-de-recoltat-legume/masini-de-dislocat-ceapa/',
    'https://www.agritech.com.ro/recoltare-si-ambalare/masini-de-recoltat-legume/rosii-masini-de-recoltat-legume/masini-autopropulsate-de-recoltat-rosii/'
)
foreach ($url in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $url -TimeoutSec 15 -UseBasicParsing
        $content = $r.Content
        $startIdx = $content.IndexOf('entry-content')
        if ($startIdx -lt 0) { $startIdx = 0 }
        $chunk = $content.Substring($startIdx, [Math]::Min(12000, $content.Length - $startIdx))
        $clean = $chunk -replace '<[^>]+>', "`n" -replace '&nbsp;', ' ' -replace '&amp;', '&' -replace '&#8220;', '"' -replace '&#8221;', '"' -replace '&#8211;', '-'
        $lines = $clean.Split("`n") | Where-Object { $_.Trim().Length -gt 5 } | Select-Object -First 35
        Write-Output "=== $url ==="
        $lines -join "`n"
        Write-Output "`n---`n"
    } catch {
        Write-Output "ERROR: $url - $($_.Exception.Message)"
    }
}
