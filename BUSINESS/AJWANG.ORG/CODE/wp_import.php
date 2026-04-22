<?php
/**
 * Import African country profiles into WordPress CPT 'africa_country'.
 * Run via: wp eval-file CODE/wp_import.php --path=/home/loaiidil/ajwang.org
 */

$json_path = __DIR__ . '/../DATA/countries.json';
if (!file_exists($json_path)) {
    echo "ERROR: countries.json not found at $json_path\n";
    exit(1);
}

$profiles = json_decode(file_get_contents($json_path), true);
if (!$profiles) {
    echo "ERROR: Failed to parse countries.json\n";
    exit(1);
}

$created = 0;
$updated = 0;

foreach ($profiles as $p) {
    $slug = strtolower($p['iso2']);
    $title = $p['name'];

    $existing = get_posts([
        'post_type'      => 'africa_country',
        'name'           => $slug,
        'posts_per_page' => 1,
        'post_status'    => 'any',
    ]);

    $post_data = [
        'post_title'   => $title,
        'post_name'    => $slug,
        'post_type'    => 'africa_country',
        'post_status'  => 'draft',
        'post_content' => '',
    ];

    if ($existing) {
        $post_data['ID'] = $existing[0]->ID;
        $post_id = wp_update_post($post_data);
        $updated++;
    } else {
        $post_id = wp_insert_post($post_data);
        $created++;
    }

    if (is_wp_error($post_id)) {
        echo "ERROR inserting {$title}: " . $post_id->get_error_message() . "\n";
        continue;
    }

    $scalar_fields = [
        'iso2', 'iso3', 'region', 'capital', 'currency', 'language',
        'gdp_usd', 'gdp_per_capita', 'gdp_growth_pct', 'population',
        'ease_of_business', 'exports_usd', 'imports_usd',
        'inflation_pct', 'unemployment_pct',
        'cpi_score', 'cpi_rank',
        'gdp_display', 'population_display',
        'visa_free_count', 'voa_count', 'evisa_count', 'visa_required_count', 'schengen_access',
        'treaty_count',
    ];

    foreach ($scalar_fields as $field) {
        $val = $p[$field] ?? null;
        if ($val !== null) {
            update_post_meta($post_id, "_ajwang_{$field}", $val);
        }
    }

    // Treaties stored as JSON array
    if (!empty($p['treaties'])) {
        update_post_meta($post_id, '_ajwang_treaties', json_encode($p['treaties']));
    }

    echo ($existing ? "Updated" : "Created") . ": {$title}\n";
}

echo "\nDone. Created: {$created}, Updated: {$updated}\n";
