<?php
/**
 * create_tables.php — One-time runner: creates agro_leads + agro_price_alerts tables.
 * Self-deletes after successful run. Deploy to agroevolution.com docroot, visit once.
 */

$key = $_GET['key'] ?? '';
if ($key !== 'agro2026create') {
    http_response_code(403);
    exit;
}

define('ABSPATH_GUARD', true);

$docroot = '/home/loaiidil/agroevolution.com';
chdir($docroot);
require_once $docroot . '/wp-load.php';

global $wpdb;
$charset = $wpdb->get_charset_collate();
$prefix  = $wpdb->prefix;

$results = [];

// --- agro_leads ---
$sql_leads = "CREATE TABLE IF NOT EXISTS {$prefix}agro_leads (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    telefon VARCHAR(50) DEFAULT NULL,
    judet VARCHAR(50) DEFAULT NULL,
    categorie VARCHAR(50) DEFAULT NULL,
    suprafata_min DECIMAL(10,2) DEFAULT NULL,
    pret_max_ha DECIMAL(10,2) DEFAULT NULL,
    mesaj TEXT DEFAULT NULL,
    sursa VARCHAR(50) DEFAULT 'harta',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_judet (judet),
    INDEX idx_sursa (sursa)
) ENGINE=InnoDB {$charset};";

$r1 = $wpdb->query($sql_leads);
$results['agro_leads'] = ($r1 !== false) ? 'OK' : $wpdb->last_error;

// --- agro_price_alerts ---
$sql_alerts = "CREATE TABLE IF NOT EXISTS {$prefix}agro_price_alerts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    judet VARCHAR(50) DEFAULT NULL,
    categorie VARCHAR(50) DEFAULT NULL,
    suprafata_min DECIMAL(10,2) DEFAULT NULL,
    pret_max_ha DECIMAL(10,2) NOT NULL,
    confirmed TINYINT(1) DEFAULT 0,
    confirm_token VARCHAR(64) DEFAULT NULL,
    last_notified_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_confirmed (confirmed),
    INDEX idx_token (confirm_token)
) ENGINE=InnoDB {$charset};";

$r2 = $wpdb->query($sql_alerts);
$results['agro_price_alerts'] = ($r2 !== false) ? 'OK' : $wpdb->last_error;

// Verify tables exist
$tables = $wpdb->get_col("SHOW TABLES LIKE '{$prefix}agro%'");
$results['tables_found'] = $tables;

$all_ok = ($r1 !== false && $r2 !== false);

// Self-delete
if ($all_ok) {
    @unlink(__FILE__);
    $results['self_deleted'] = true;
}

header('Content-Type: application/json');
echo json_encode(['ok' => $all_ok, 'results' => $results], JSON_PRETTY_PRINT);
