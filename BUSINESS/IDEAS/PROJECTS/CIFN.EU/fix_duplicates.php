<?php
/**
 * CIFN.EU Fix Script - Delete duplicate posts + stagger dates
 * Run once via browser, then delete this file.
 */

// Load WordPress
define('WP_USE_THEMES', false);
require_once(__DIR__ . '/wp-load.php');

header('Content-Type: text/plain; charset=utf-8');

echo "=== CIFN.EU Duplicate Post Cleanup ===\n\n";

// Duplicate post IDs (the -2 and -3 slug variants) to delete
// Originals are the earliest IDs with clean slugs
$duplicates_to_delete = [
    // -2 variants (second import)
    26,  // cum-functioneaza-achizitiile-publice-din-fonduri-europene-2
    40,  // ce-programe-operationale-sunt-disponibile-in-romania-2
    44,  // top-10-judete-cu-cele-mai-multe-achizitii-publice-in-2026-2
    34,  // finantari-pentru-imm-uri-si-antreprenori-in-2026-2
    32,  // energie-regenerabila-si-eficienta-energetica-fonduri-disponibile-2
    65,  // fonduri-pentru-agricultura-pescuit-si-dezvoltare-rurala-2
    77,  // fonduri-pentru-educatie-si-formare-profesionala-2
    85,  // fonduri-pentru-infrastructura-de-transport-si-utilitati-2
    87,  // fonduri-pentru-inovare-si-cercetare-dezvoltare-2
    93,  // fonduri-pentru-sanatate-si-servicii-sociale-2
    91,  // 5-033-de-proiecte-europene-cu-proceduri-de-achizitie-active-2
    67,  // 13-570-de-anunturi-de-achizitii-publice-disponibile-...-2
    100, // tranzitia-verde-si-economia-circulara-fonduri-ue-2
    69,  // fonduri-europene-in-bucuresti-1-030-de-proiecte-2
    // -3 variants (third import)
    63,  // cum-functioneaza-achizitiile-publice-din-fonduri-europene-3
    89,  // ce-programe-operationale-sunt-disponibile-in-romania-3
    97,  // top-10-judete-cu-cele-mai-multe-achizitii-publice-in-2026-3
    83,  // finantari-pentru-imm-uri-si-antreprenori-in-2026-3
    79,  // energie-regenerabila-si-eficienta-energetica-fonduri-disponibile-3
];

// Step 1: Delete duplicates
echo "STEP 1: Deleting " . count($duplicates_to_delete) . " duplicate posts...\n";
$deleted = 0;
foreach ($duplicates_to_delete as $post_id) {
    $post = get_post($post_id);
    if ($post) {
        $result = wp_delete_post($post_id, true); // true = force delete (skip trash)
        if ($result) {
            echo "  DELETED: ID $post_id - {$post->post_name}\n";
            $deleted++;
        } else {
            echo "  FAILED: ID $post_id\n";
        }
    } else {
        echo "  SKIP: ID $post_id (not found)\n";
    }
}
echo "Deleted $deleted duplicate posts.\n\n";

// Step 2: Stagger dates for remaining posts (spread over 30 days)
echo "STEP 2: Staggering publication dates...\n";
$remaining = get_posts([
    'post_type' => 'post',
    'post_status' => 'publish',
    'numberposts' => -1,
    'orderby' => 'ID',
    'order' => 'ASC',
]);

$total = count($remaining);
echo "Found $total remaining posts to stagger.\n";

// Spread posts from March 5 to April 3 (29 days)
$start_date = strtotime('2026-03-05');
$end_date = strtotime('2026-04-03');
$interval = ($end_date - $start_date) / max($total - 1, 1);

foreach ($remaining as $i => $post) {
    $new_timestamp = $start_date + ($i * $interval);
    // Add random hours (8-18) for natural feel
    $hour = rand(8, 18);
    $minute = rand(0, 59);
    $new_date = date('Y-m-d', $new_timestamp) . " " . sprintf('%02d:%02d:00', $hour, $minute);
    $new_date_gmt = get_gmt_from_date($new_date);

    wp_update_post([
        'ID' => $post->ID,
        'post_date' => $new_date,
        'post_date_gmt' => $new_date_gmt,
    ]);
    echo "  ID {$post->ID}: {$post->post_name} => $new_date\n";
}

echo "\n=== DONE ===\n";
echo "Deleted: $deleted duplicates\n";
echo "Staggered: $total posts across 30 days\n";
echo "\nNEXT STEPS:\n";
echo "1. Install Yoast SEO or Rank Math plugin\n";
echo "2. Resubmit sitemap in Google Search Console\n";
echo "3. DELETE THIS FILE (fix_duplicates.php)\n";
