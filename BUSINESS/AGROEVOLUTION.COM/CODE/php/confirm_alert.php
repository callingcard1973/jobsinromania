<?php
// Load WordPress
chdir('/home/loaiidil/agroevolution.com');
$_SERVER['HTTP_HOST']      = 'agroevolution.com';
$_SERVER['REQUEST_URI']    = '/';
$_SERVER['REQUEST_METHOD'] = 'GET';
$_SERVER['SERVER_NAME']    = 'agroevolution.com';
require_once('wp-load.php');

global $wpdb;
$table = $wpdb->prefix . 'agro_price_alerts';

$token = isset($_GET['token']) ? sanitize_text_field($_GET['token']) : '';

$success  = false;
$message  = '';
$sub_text = '';

if (!empty($token) && strlen($token) === 64 && ctype_xdigit($token)) {
    $row = $wpdb->get_row(
        $wpdb->prepare(
            "SELECT id FROM {$table} WHERE confirm_token = %s AND confirmed = 0 LIMIT 1",
            $token
        )
    );

    if ($row) {
        $updated = $wpdb->update(
            $table,
            ['confirmed' => 1],
            ['id' => $row->id],
            ['%d'],
            ['%d']
        );

        if ($updated !== false) {
            $success  = true;
            $message  = '✓ Alertă activată!';
            $sub_text = 'Te vom notifica când apare teren la prețul specificat.';
        } else {
            $message  = 'Eroare la activare. Încearcă din nou.';
            $sub_text = 'Dacă problema persistă, contactează-ne la office@agroevolution.com.';
        }
    } else {
        $message  = 'Token invalid sau alertă deja confirmată.';
        $sub_text = 'Dacă crezi că este o eroare, înscrie-te din nou pe agroevolution.com.';
    }
} else {
    $message  = 'Token lipsă sau invalid.';
    $sub_text = 'Accesează linkul primit pe email pentru a confirma alerta.';
}

$color     = $success ? '#2d6a2d' : '#c0392b';
$bg_icon   = $success ? '#e8f5e9' : '#fdecea';
$icon      = $success ? '✓' : '✗';
$btn_label = $success ? 'Înapoi la AgroEvolution' : 'Înscrie-te din nou';
$btn_url   = 'https://agroevolution.com';
?>
<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Alertă teren — AgroEvolution</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f4f6f0; display: flex;
           align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
    .card { background: white; border-radius: 10px; padding: 48px 40px;
            max-width: 480px; width: 100%; text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,.08); }
    .icon { width: 72px; height: 72px; border-radius: 50%;
            background: <?= $bg_icon ?>; display: inline-flex;
            align-items: center; justify-content: center;
            font-size: 36px; margin-bottom: 24px; }
    h1 { color: <?= $color ?>; font-size: 24px; margin: 0 0 12px; }
    p  { color: #555; font-size: 15px; line-height: 1.5; margin: 0 0 28px; }
    a.btn { background: <?= $color ?>; color: white; padding: 12px 28px;
            text-decoration: none; border-radius: 6px; font-size: 15px;
            display: inline-block; }
    a.btn:hover { opacity: .88; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon"><?= $icon ?></div>
    <h1><?= htmlspecialchars($message) ?></h1>
    <p><?= htmlspecialchars($sub_text) ?></p>
    <a class="btn" href="<?= $btn_url ?>"><?= $btn_label ?></a>
  </div>
</body>
</html>
