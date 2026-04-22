<?php
/**
 * alert_matcher.php — Match new MADR land listings against confirmed price alerts.
 * Reads alerts from WordPress MySQL, listings from Supabase REST API, sends via Brevo.
 * Triggered by cPanel cron or web with ?key=agromatch2026
 */

// Auth guard: allow CLI or web with correct key
$is_cli = (php_sapi_name() === 'cli');
if (!$is_cli) {
    $key = $_GET['key'] ?? '';
    if ($key !== 'agromatch2026') {
        http_response_code(403);
        exit;
    }
}

header('Content-Type: text/plain; charset=utf-8');

$docroot = '/home/loaiidil/agroevolution.com';
chdir($docroot);
require_once $docroot . '/wp-load.php';

global $wpdb;

$date_str = date('Y-m-d H:i:s');
echo "Alert Matcher — {$date_str}\n";

// --- Constants ---
define('SUPABASE_URL', 'https://jaurgtjadyiannbalhhb.supabase.co');
define('SUPABASE_KEY', 'sb_secret_6M9Pf8i46lvXMjSN3wvBYA_Zr2qiO7R');
define('BREVO_KEY', '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');
define('COOLDOWN_DAYS', 7);
define('MAX_LISTINGS_PER_EMAIL', 5);

// --- 1. Fetch confirmed alerts ---
$alerts = $wpdb->get_results(
    "SELECT * FROM {$wpdb->prefix}agro_price_alerts
     WHERE confirmed = 1
       AND (last_notified_at IS NULL OR last_notified_at < NOW() - INTERVAL " . COOLDOWN_DAYS . " DAY)",
    ARRAY_A
);
$alert_count = count($alerts);
echo "Alerte active: {$alert_count}\n";

// --- 2. Fetch new listings from Supabase (last 48h) ---
$since = date('Y-m-d\TH:i:s', strtotime('-48 hours'));
$sb_url = SUPABASE_URL . '/rest/v1/land_listings'
    . '?scraped_at=gte.' . urlencode($since)
    . '&select=judet,localitate,suprafata_ha,pret_ron,categorie'
    . '&limit=500';

$ch = curl_init($sb_url);
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
        'apikey: ' . SUPABASE_KEY,
        'Authorization: Bearer ' . SUPABASE_KEY,
        'Accept: application/json',
    ],
    CURLOPT_TIMEOUT => 15,
]);
$sb_response = curl_exec($ch);
$sb_error    = curl_error($ch);
curl_close($ch);

if ($sb_error) {
    echo "EROARE Supabase: {$sb_error}\n";
    exit(1);
}

$listings = json_decode($sb_response, true);
if (!is_array($listings)) {
    echo "EROARE Supabase: raspuns invalid\n";
    exit(1);
}

$listing_count = count($listings);
echo "Listings noi (48h): {$listing_count}\n";

if ($alert_count === 0 || $listing_count === 0) {
    echo "Emailuri trimise: 0\nDone.\n";
    exit(0);
}

// --- 3. Match alerts against listings ---
$emails_sent = 0;

foreach ($alerts as $alert) {
    $matched = [];

    foreach ($listings as $listing) {
        // Judet filter
        if (!empty($alert['judet']) && $alert['judet'] !== $listing['judet']) {
            continue;
        }
        // Categorie filter
        if (!empty($alert['categorie']) && $alert['categorie'] !== $listing['categorie']) {
            continue;
        }
        // Suprafata min filter
        if (!empty($alert['suprafata_min']) && $listing['suprafata_ha'] < (float)$alert['suprafata_min']) {
            continue;
        }
        // Pret/ha filter
        if (!empty($alert['pret_max_ha']) && $listing['suprafata_ha'] > 0) {
            $pret_ha = (float)$listing['pret_ron'] / (float)$listing['suprafata_ha'];
            if ($pret_ha > (float)$alert['pret_max_ha']) {
                continue;
            }
        }
        $matched[] = $listing;
    }

    if (empty($matched)) {
        continue;
    }

    // Cap at 5 listings
    $to_send = array_slice($matched, 0, MAX_LISTINGS_PER_EMAIL);
    $n       = count($matched);

    // Build email
    $subject = "🌾 {$n} teren" . ($n > 1 ? 'uri' : '') . " noi la prețul tău — AgroEvolution";
    $html    = build_email_html($to_send, $n);

    $sent = send_brevo_email($alert['email'], $subject, $html);
    if ($sent) {
        $wpdb->query(
            $wpdb->prepare(
                "UPDATE {$wpdb->prefix}agro_price_alerts SET last_notified_at = NOW() WHERE id = %d",
                $alert['id']
            )
        );
        $emails_sent++;
    }
}

echo "Emailuri trimise: {$emails_sent}\nDone.\n";
exit(0);

// --- Helper: build HTML email ---
function build_email_html(array $listings, int $total): string
{
    $rows = '';
    foreach ($listings as $l) {
        $pret_ha = ($l['suprafata_ha'] > 0)
            ? number_format((float)$l['pret_ron'] / (float)$l['suprafata_ha'], 0, ',', '.')
            : 'N/A';
        $sup = number_format((float)$l['suprafata_ha'], 2, ',', '.');
        $pret_ron = number_format((float)$l['pret_ron'], 0, ',', '.');
        $judet = htmlspecialchars($l['judet'] ?? '');
        $loc   = htmlspecialchars($l['localitate'] ?? '');
        $cat   = htmlspecialchars($l['categorie'] ?? '');
        $rows .= "<tr>
            <td style='padding:8px;border-bottom:1px solid #eee'>{$judet}</td>
            <td style='padding:8px;border-bottom:1px solid #eee'>{$loc}</td>
            <td style='padding:8px;border-bottom:1px solid #eee'>{$sup} ha</td>
            <td style='padding:8px;border-bottom:1px solid #eee'>{$pret_ha} RON/ha</td>
            <td style='padding:8px;border-bottom:1px solid #eee'>{$cat}</td>
        </tr>\n";
    }

    $extra = ($total > MAX_LISTINGS_PER_EMAIL)
        ? "<p style='color:#666;font-size:13px'>+ " . ($total - MAX_LISTINGS_PER_EMAIL) . " alte anunțuri disponibile pe hartă.</p>"
        : '';

    return "<!DOCTYPE html><html><body style='font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto'>
<h2 style='color:#2e7d32'>🌾 Terenuri agricole noi care corespund alertei tale</h2>
<p>Am găsit <strong>{$total} anunț" . ($total > 1 ? 'uri noi' : ' nou') . "</strong> care corespund criteriilor tale de preț pe AgroEvolution.</p>
<table style='width:100%;border-collapse:collapse;margin:16px 0'>
<thead>
  <tr style='background:#f5f5f5'>
    <th style='padding:10px;text-align:left'>Județ</th>
    <th style='padding:10px;text-align:left'>Localitate</th>
    <th style='padding:10px;text-align:left'>Suprafață</th>
    <th style='padding:10px;text-align:left'>Preț/ha</th>
    <th style='padding:10px;text-align:left'>Tip</th>
  </tr>
</thead>
<tbody>{$rows}</tbody>
</table>
{$extra}
<p style='margin-top:24px'>
  <a href='https://agroevolution.com/harta.php'
     style='background:#2e7d32;color:#fff;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:bold'>
    Vezi toate anunțurile pe hartă
  </a>
</p>
<p style='margin-top:32px;font-size:12px;color:#999'>
  Primești acest email deoarece ai setat o alertă de preț pe AgroEvolution.com.<br>
  Pentru a dezactiva alertele, contactează-ne la contact@agroevolution.com.
</p>
</body></html>";
}

// --- Helper: send via Brevo ---
function send_brevo_email(string $to_email, string $subject, string $html): bool
{
    $payload = json_encode([
        'sender'     => ['name' => 'AgroEvolution', 'email' => 'contact@agroevolution.com'],
        'to'         => [['email' => $to_email]],
        'subject'    => $subject,
        'htmlContent'=> $html,
    ]);

    $ch = curl_init('https://api.brevo.com/v3/smtp/email');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $payload,
        CURLOPT_HTTPHEADER     => [
            'api-key: ' . BREVO_KEY,
            'Content-Type: application/json',
            'Accept: application/json',
        ],
        CURLOPT_TIMEOUT => 15,
    ]);
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    return ($http_code >= 200 && $http_code < 300);
}
