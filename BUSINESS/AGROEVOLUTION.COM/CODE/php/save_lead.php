<?php
/**
 * save_lead.php — Permanent POST endpoint for capturing buyer leads.
 * Accepts JSON body, validates, sanitizes, inserts into wp_agro_leads.
 * Deploy to: /home/loaiidil/agroevolution.com/save_lead.php
 */

header('Access-Control-Allow-Origin: https://agroevolution.com');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

// Handle preflight
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

$docroot = '/home/loaiidil/agroevolution.com';
chdir($docroot);
require_once $docroot . '/wp-load.php';

global $wpdb;

// Parse JSON body
$raw  = file_get_contents('php://input');
$data = json_decode($raw, true);
if (!is_array($data)) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid JSON body']);
    exit;
}

// Validate required fields
$email = isset($data['email']) ? trim($data['email']) : '';
if (!$email || !is_email($email)) {
    http_response_code(422);
    echo json_encode(['error' => 'Valid email is required']);
    exit;
}

$allowed_sursa = ['harta', 'cumparferme', 'alert'];
$sursa = isset($data['sursa']) ? sanitize_text_field($data['sursa']) : 'harta';
if (!in_array($sursa, $allowed_sursa, true)) {
    http_response_code(422);
    echo json_encode(['error' => 'sursa must be one of: harta, cumparferme, alert']);
    exit;
}

// Sanitize inputs
$telefon      = isset($data['telefon'])      ? sanitize_text_field($data['telefon'])      : null;
$judet        = isset($data['judet'])        ? sanitize_text_field($data['judet'])        : null;
$categorie    = isset($data['categorie'])    ? sanitize_text_field($data['categorie'])    : null;
$mesaj        = isset($data['mesaj'])        ? sanitize_textarea_field($data['mesaj'])    : null;

$suprafata_min = null;
if (isset($data['suprafata_min']) && is_numeric($data['suprafata_min'])) {
    $suprafata_min = (float) $data['suprafata_min'];
}

$pret_max_ha = null;
if (isset($data['pret_max_ha']) && is_numeric($data['pret_max_ha'])) {
    $pret_max_ha = (float) $data['pret_max_ha'];
}

// Insert
$inserted = $wpdb->insert(
    $wpdb->prefix . 'agro_leads',
    [
        'email'         => sanitize_email($email),
        'telefon'       => $telefon,
        'judet'         => $judet,
        'categorie'     => $categorie,
        'suprafata_min' => $suprafata_min,
        'pret_max_ha'   => $pret_max_ha,
        'mesaj'         => $mesaj,
        'sursa'         => $sursa,
    ],
    ['%s', '%s', '%s', '%s', '%f', '%f', '%s', '%s']
);

if ($inserted === false) {
    http_response_code(500);
    echo json_encode(['error' => 'Database insert failed: ' . $wpdb->last_error]);
    exit;
}

echo json_encode(['ok' => true, 'id' => $wpdb->insert_id]);
