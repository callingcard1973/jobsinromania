<?php
/**
 * Install and activate Yoast SEO, then auto-generate meta descriptions.
 * Run once via browser, then delete this file.
 */
define('WP_USE_THEMES', false);
require_once(__DIR__ . '/wp-load.php');
require_once(ABSPATH . 'wp-admin/includes/plugin.php');
require_once(ABSPATH . 'wp-admin/includes/file.php');
require_once(ABSPATH . 'wp-admin/includes/misc.php');
require_once(ABSPATH . 'wp-admin/includes/class-wp-upgrader.php');

header('Content-Type: text/plain; charset=utf-8');
echo "=== CIFN.EU Yoast SEO Install ===\n\n";

// Step 1: Install Yoast SEO
$plugin_slug = 'wordpress-seo';
$plugin_file = 'wordpress-seo/wp-seo.php';

if (file_exists(WP_PLUGIN_DIR . '/' . $plugin_file)) {
    echo "Yoast SEO already installed.\n";
} else {
    echo "Step 1: Downloading Yoast SEO...\n";
    $api_url = "https://api.wordpress.org/plugins/info/1.2/?action=plugin_information&request[slug]=$plugin_slug";
    $response = wp_remote_get($api_url);
    if (is_wp_error($response)) {
        echo "ERROR: Could not fetch plugin info: " . $response->get_error_message() . "\n";
        exit;
    }
    $plugin_info = json_decode(wp_remote_retrieve_body($response));
    if (!$plugin_info || !isset($plugin_info->download_link)) {
        echo "ERROR: Could not find download link.\n";
        exit;
    }

    echo "  Download URL: {$plugin_info->download_link}\n";

    // Use WP upgrader to install
    $skin = new WP_Ajax_Upgrader_Skin();
    $upgrader = new Plugin_Upgrader($skin);
    $result = $upgrader->install($plugin_info->download_link);

    if (is_wp_error($result)) {
        echo "ERROR: " . $result->get_error_message() . "\n";
        exit;
    }
    if ($result === false) {
        $errors = $skin->get_errors();
        if (is_wp_error($errors)) {
            echo "ERROR: " . $errors->get_error_message() . "\n";
        } else {
            echo "ERROR: Installation failed (unknown reason).\n";
        }
        exit;
    }
    echo "  Yoast SEO installed successfully.\n";
}

// Step 2: Activate
if (is_plugin_active($plugin_file)) {
    echo "Yoast SEO already active.\n";
} else {
    $result = activate_plugin($plugin_file);
    if (is_wp_error($result)) {
        echo "ERROR activating: " . $result->get_error_message() . "\n";
        exit;
    }
    echo "Step 2: Yoast SEO ACTIVATED.\n";
}

// Step 3: Generate meta descriptions for all posts that don't have one
echo "\nStep 3: Generating meta descriptions...\n";
$posts = get_posts([
    'post_type' => ['post', 'page'],
    'post_status' => 'publish',
    'numberposts' => -1,
]);

$updated = 0;
foreach ($posts as $post) {
    $existing = get_post_meta($post->ID, '_yoast_wpseo_metadesc', true);
    if (!empty($existing)) {
        echo "  SKIP ID {$post->ID}: already has meta desc\n";
        continue;
    }

    // Generate from content: strip tags, take first ~150 chars
    $content = wp_strip_all_tags($post->post_content);
    $content = preg_replace('/\s+/', ' ', $content);
    $content = trim($content);

    if (strlen($content) > 155) {
        // Cut at word boundary
        $desc = substr($content, 0, 155);
        $desc = substr($desc, 0, strrpos($desc, ' '));
        $desc .= '...';
    } else {
        $desc = $content;
    }

    if (!empty($desc)) {
        update_post_meta($post->ID, '_yoast_wpseo_metadesc', $desc);
        echo "  SET ID {$post->ID} ({$post->post_name}): " . substr($desc, 0, 80) . "...\n";
        $updated++;
    }
}

// Step 4: Set Yoast defaults
echo "\nStep 4: Configuring Yoast SEO defaults...\n";
$wpseo = get_option('wpseo', []);
$wpseo['keyword_analysis_active'] = true;
$wpseo['content_analysis_active'] = true;
$wpseo['enable_xml_sitemap'] = true;
update_option('wpseo', $wpseo);

$wpseo_titles = get_option('wpseo_titles', []);
$wpseo_titles['title-post'] = '%%title%% - %%sitename%%';
$wpseo_titles['metadesc-post'] = '%%excerpt%%';
$wpseo_titles['title-page'] = '%%title%% - %%sitename%%';
update_option('wpseo_titles', $wpseo_titles);

echo "  Defaults configured.\n";

echo "\n=== DONE ===\n";
echo "Yoast SEO: INSTALLED + ACTIVE\n";
echo "Meta descriptions: $updated posts updated\n";
echo "Total posts/pages: " . count($posts) . "\n";
echo "\nDELETE THIS FILE NOW.\n";
