<?php
header('Content-Type: application/json');

// Capture real request method before WordPress overwrites it
$real_method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

// Load WordPress
chdir('/home/loaiidil/agroevolution.com');
$_SERVER['HTTP_HOST']      = 'agroevolution.com';
$_SERVER['REQUEST_URI']    = '/';
$_SERVER['REQUEST_METHOD'] = 'GET';
$_SERVER['SERVER_NAME']    = 'agroevolution.com';
require_once('wp-load.php');

global $wpdb;
$table = $wpdb->prefix . 'agro_price_alerts';

// Only accept POST
if ($real_method !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
    exit;
}

// Parse JSON body
$body = json_decode(file_get_contents('php://input'), true);
if (!is_array($body)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Invalid JSON']);
    exit;
}

// Validate required fields
$email       = isset($body['email']) ? trim($body['email']) : '';
$pret_max_ha = isset($body['pret_max_ha']) ? $body['pret_max_ha'] : null;

if (empty($email) || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Email invalid sau lipsă']);
    exit;
}

if ($pret_max_ha === null || !is_numeric($pret_max_ha)) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'pret_max_ha este obligatoriu și trebuie să fie numeric']);
    exit;
}

$pret_max_ha   = floatval($pret_max_ha);
$judet         = isset($body['judet'])         ? sanitize_text_field($body['judet'])         : null;
$categorie     = isset($body['categorie'])     ? sanitize_text_field($body['categorie'])     : null;
$suprafata_min = isset($body['suprafata_min']) ? floatval($body['suprafata_min'])             : null;

// Generate 64-char hex confirmation token
$token = bin2hex(random_bytes(32));

// Insert into DB
$inserted = $wpdb->insert(
    $table,
    [
        'email'          => $email,
        'judet'          => $judet,
        'categorie'      => $categorie,
        'suprafata_min'  => $suprafata_min,
        'pret_max_ha'    => $pret_max_ha,
        'confirmed'      => 0,
        'confirm_token'  => $token,
        'created_at'     => current_time('mysql'),
    ],
    ['%s','%s','%s','%f','%f','%d','%s','%s']
);

if (!$inserted) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Eroare la salvare']);
    exit;
}

// Send confirmation email via Brevo
$confirm_url = 'https://agroevolution.com/confirm_alert.php?token=' . $token;

$judet_text     = $judet     ? "<li>Județ: <strong>{$judet}</strong></li>"         : '';
$categorie_text = $categorie ? "<li>Categorie: <strong>{$categorie}</strong></li>" : '';
$suprafata_text = $suprafata_min ? "<li>Suprafață minimă: <strong>{$suprafata_min} ha</strong></li>" : '';

$html_content = "
<!DOCTYPE html>
<html lang='ro'>
<head><meta charset='UTF-8'></head>
<body style='font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;color:#333'>
  <h2 style='color:#2d6a2d'>🌾 Alertă de preț teren — AgroEvolution</h2>
  <p>Ai solicitat o alertă pentru terenuri agricole cu prețul de <strong>maxim {$pret_max_ha} RON/ha</strong>.</p>
  <p>Detalii alertă:</p>
  <ul>
    {$judet_text}
    {$categorie_text}
    {$suprafata_text}
    <li>Preț maxim/ha: <strong>{$pret_max_ha} RON</strong></li>
  </ul>
  <p>Click pe butonul de mai jos pentru a activa alerta:</p>
  <p style='text-align:center;margin:30px 0'>
    <a href='{$confirm_url}'
       style='background:#2d6a2d;color:white;padding:14px 28px;text-decoration:none;border-radius:6px;font-size:16px;display:inline-block'>
      ✓ Activează Alerta
    </a>
  </p>
  <p style='font-size:12px;color:#888'>Dacă nu ai solicitat această alertă, ignoră acest email.<br>
  AgroEvolution &mdash; <a href='https://agroevolution.com'>agroevolution.com</a></p>
</body>
</html>
";

$brevo_payload = json_encode([
    'sender'      => ['name' => 'AgroEvolution', 'email' => 'office@agroevolution.com'],
    'to'          => [['email' => $email]],
    'subject'     => 'Confirmă alerta de preț teren — AgroEvolution',
    'htmlContent' => $html_content,
]);

$ch = curl_init('https://api.brevo.com/v3/smtp/email');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => $brevo_payload,
    CURLOPT_HTTPHEADER     => [
        'accept: application/json',
        'api-key: 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',
        'content-type: application/json',
    ],
    CURLOPT_TIMEOUT => 15,
]);

$brevo_response = curl_exec($ch);
$brevo_status   = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($brevo_status !== 201) {
    // Email failed but record is saved — log silently
    error_log("subscribe_alert.php: Brevo error {$brevo_status} for {$email}");
}

echo json_encode(['ok' => true, 'message' => 'Verifică emailul pentru confirmare']);
