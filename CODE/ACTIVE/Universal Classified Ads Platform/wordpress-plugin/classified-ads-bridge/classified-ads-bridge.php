<?php
/**
 * Plugin Name: Classified Ads Bridge
 * Plugin URI: https://github.com/classified-ads-bridge
 * Description: Facebook login + classified ads posting via FastAPI backend. Users register with Facebook, post ads, pay via Stripe, and ads appear as WP posts after moderation.
 * Version: 1.0.0
 * Author: Classified Ads Platform
 * Requires at least: 5.0
 * Requires PHP: 7.4
 */

defined('ABSPATH') || exit;

define('CAB_VERSION', '1.0.0');
define('CAB_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('CAB_PLUGIN_URL', plugin_dir_url(__FILE__));

// --- Settings page ---
add_action('admin_menu', function () {
    add_options_page('Classified Ads', 'Classified Ads', 'manage_options', 'classified-ads-bridge', 'cab_settings_page');
});

add_action('admin_init', function () {
    register_setting('cab_settings', 'cab_api_url', ['type' => 'string', 'sanitize_callback' => 'esc_url_raw']);
    register_setting('cab_settings', 'cab_fb_app_id', ['type' => 'string', 'sanitize_callback' => 'sanitize_text_field']);
    register_setting('cab_settings', 'cab_fb_app_secret', ['type' => 'string', 'sanitize_callback' => 'sanitize_text_field']);
    register_setting('cab_settings', 'cab_price_cents', ['type' => 'integer', 'sanitize_callback' => 'absint']);
    register_setting('cab_settings', 'cab_currency', ['type' => 'string', 'sanitize_callback' => 'sanitize_text_field']);
    register_setting('cab_settings', 'cab_stripe_pk', ['type' => 'string', 'sanitize_callback' => 'sanitize_text_field']);
});

function cab_settings_page() {
    ?>
    <div class="wrap">
        <h1>Classified Ads Bridge</h1>
        <form method="post" action="options.php">
            <?php settings_fields('cab_settings'); ?>
            <table class="form-table">
                <tr><th>FastAPI Backend URL</th><td><input type="url" name="cab_api_url" value="<?php echo esc_attr(get_option('cab_api_url', '')); ?>" class="regular-text" placeholder="https://api.example.com"></td></tr>
                <tr><th>Facebook App ID</th><td><input type="text" name="cab_fb_app_id" value="<?php echo esc_attr(get_option('cab_fb_app_id', '')); ?>" class="regular-text"></td></tr>
                <tr><th>Facebook App Secret</th><td><input type="password" name="cab_fb_app_secret" value="<?php echo esc_attr(get_option('cab_fb_app_secret', '')); ?>" class="regular-text"></td></tr>
                <tr><th>Stripe Publishable Key</th><td><input type="text" name="cab_stripe_pk" value="<?php echo esc_attr(get_option('cab_stripe_pk', '')); ?>" class="regular-text"></td></tr>
                <tr><th>Price (cents)</th><td><input type="number" name="cab_price_cents" value="<?php echo esc_attr(get_option('cab_price_cents', 500)); ?>"></td></tr>
                <tr><th>Currency</th><td><input type="text" name="cab_currency" value="<?php echo esc_attr(get_option('cab_currency', 'usd')); ?>"></td></tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}

// --- Facebook SDK + Login ---
add_action('wp_enqueue_scripts', function () {
    $fb_app_id = get_option('cab_fb_app_id', '');
    if ($fb_app_id) {
        wp_enqueue_script('cab-fb-sdk', "https://connect.facebook.net/en_US/sdk.js", [], null, true);
    }
    wp_enqueue_script('cab-app', CAB_PLUGIN_URL . 'js/app.js', [], CAB_VERSION, true);
    wp_localize_script('cab-app', 'cabConfig', [
        'apiUrl' => rtrim(get_option('cab_api_url', ''), '/'),
        'fbAppId' => $fb_app_id,
        'stripePk' => get_option('cab_stripe_pk', ''),
        'priceCents' => (int) get_option('cab_price_cents', 500),
        'currency' => get_option('cab_currency', 'usd'),
        'ajaxUrl' => admin_url('admin-ajax.php'),
        'homeUrl' => home_url(),
    ]);
});

// --- AJAX: Facebook login → create WP user + FastAPI account ---
add_action('wp_ajax_nopriv_cab_fb_login', 'cab_ajax_fb_login');
add_action('wp_ajax_cab_fb_login', 'cab_ajax_fb_login');

function cab_ajax_fb_login() {
    $access_token = sanitize_text_field($_POST['access_token'] ?? '');
    if (!$access_token) wp_send_json_error('No access token');

    $fb_app_id = get_option('cab_fb_app_id', '');
    $fb_app_secret = get_option('cab_fb_app_secret', '');
    if (!$fb_app_id || !$fb_app_secret) wp_send_json_error('FB not configured');

    // Verify token with FB
    $verify_url = "https://graph.facebook.com/me?fields=id,name,email&access_token=" . urlencode($access_token);
    $response = wp_remote_get($verify_url, ['timeout' => 10]);
    if (is_wp_error($response)) wp_send_json_error('FB verify failed');
    $fb_user = json_decode(wp_remote_retrieve_body($response), true);
    if (empty($fb_user['id'])) wp_send_json_error('Invalid FB token');

    $fb_id = $fb_user['id'];
    $email = $fb_user['email'] ?? "fb_{$fb_id}@facebook.com";
    $name = $fb_user['name'] ?? 'Facebook User';

    // Create or get WP user
    $existing = get_user_by('email', $email);
    if (!$existing) {
        $user_id = wp_create_user($email, wp_generate_password(), $email);
        wp_update_user(['ID' => $user_id, 'display_name' => $name, 'nickname' => $name]);
        update_user_meta($user_id, '_cab_fb_id', $fb_id);
    } else {
        $user_id = $existing->ID;
    }

    // Log into WP
    wp_set_current_user($user_id);
    wp_set_auth_cookie($user_id, true);

    // Also register/login on FastAPI backend
    $api_url = rtrim(get_option('cab_api_url', ''), '/');
    if ($api_url) {
        // Try register then login
        wp_remote_post("$api_url/api/auth/register", [
            'timeout' => 10,
            'headers' => ['Content-Type' => 'application/json'],
            'body' => json_encode(['name' => $name, 'email' => $email, 'password' => 'fb_' . $fb_id . '_auth']),
        ]);
        $login_resp = wp_remote_post("$api_url/api/auth/login", [
            'timeout' => 10,
            'body' => ['username' => $email, 'password' => 'fb_' . $fb_id . '_auth'],
        ]);
        $api_token = null;
        if (!is_wp_error($login_resp)) {
            $body = json_decode(wp_remote_retrieve_body($login_resp), true);
            $api_token = $body['access_token'] ?? null;
        }
    }

    wp_send_json_success([
        'user_id' => $user_id,
        'name' => $name,
        'email' => $email,
        'api_token' => $api_token ?? '',
    ]);
}

// --- AJAX: WP native register/login → FastAPI account ---
add_action('wp_ajax_nopriv_cab_native_register', 'cab_ajax_native_register');
add_action('wp_ajax_cab_native_register', 'cab_ajax_native_register');

function cab_ajax_native_register() {
    $name = sanitize_text_field($_POST['name'] ?? '');
    $email = sanitize_email($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';
    if (!$name || !$email || !$password) wp_send_json_error('All fields required');

    if (get_user_by('email', $email)) wp_send_json_error('Email already registered');

    $user_id = wp_create_user($email, $password, $email);
    if (is_wp_error($user_id)) wp_send_json_error($user_id->get_error_message());
    wp_update_user(['ID' => $user_id, 'display_name' => $name, 'nickname' => $name]);
    wp_set_current_user($user_id);
    wp_set_auth_cookie($user_id, true);

    // Also register on FastAPI backend
    $api_url = rtrim(get_option('cab_api_url', ''), '/');
    $api_token = '';
    if ($api_url) {
        wp_remote_post("$api_url/api/auth/register", [
            'timeout' => 10,
            'headers' => ['Content-Type' => 'application/json'],
            'body' => json_encode(['name' => $name, 'email' => $email, 'password' => $password]),
        ]);
        $login_resp = wp_remote_post("$api_url/api/auth/login", [
            'timeout' => 10,
            'body' => ['username' => $email, 'password' => $password],
        ]);
        if (!is_wp_error($login_resp)) {
            $body = json_decode(wp_remote_retrieve_body($login_resp), true);
            $api_token = $body['access_token'] ?? '';
        }
    }

    wp_send_json_success(['user_id' => $user_id, 'name' => $name, 'email' => $email, 'api_token' => $api_token]);
}

add_action('wp_ajax_nopriv_cab_native_login', 'cab_ajax_native_login');
add_action('wp_ajax_cab_native_login', 'cab_ajax_native_login');

function cab_ajax_native_login() {
    $email = sanitize_email($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';
    if (!$email || !$password) wp_send_json_error('Email and password required');

    $user = wp_authenticate($email, $password);
    if (is_wp_error($user)) wp_send_json_error('Invalid credentials');
    wp_set_current_user($user->ID);
    wp_set_auth_cookie($user->ID, true);

    // Login on FastAPI backend
    $api_url = rtrim(get_option('cab_api_url', ''), '/');
    $api_token = '';
    if ($api_url) {
        $login_resp = wp_remote_post("$api_url/api/auth/login", [
            'timeout' => 10,
            'body' => ['username' => $email, 'password' => $password],
        ]);
        if (!is_wp_error($login_resp)) {
            $body = json_decode(wp_remote_retrieve_body($login_resp), true);
            $api_token = $body['access_token'] ?? '';
        }
    }

    wp_send_json_success(['user_id' => $user->ID, 'name' => $user->display_name, 'email' => $email, 'api_token' => $api_token]);
}

// --- Shortcode: [classified_ads_form] ---
add_shortcode('classified_ads_form', 'cab_render_post_form');

function cab_render_post_form() {
    if (!is_user_logged_in()) {
        $fb_app_id = get_option('cab_fb_app_id', '');
        $html = '<div class="cab-auth" style="max-width:420px;margin:20px auto">';
        $html .= '<h3>Post your ad</h3>';
        if ($fb_app_id) {
            $html .= '<button id="cab-fb-login-btn" class="button button-primary" style="font-size:16px;padding:10px 24px;width:100%;margin-bottom:12px"><span style="margin-right:8px">📘</span> Login with Facebook</button>';
            $html .= '<hr style="margin:16px 0"><p style="text-align:center;color:#888">or</p>';
        }
        $html .= '<div id="cab-native-auth">';
        $html .= '<div id="cab-login-form">';
        $html .= '<p><label><strong>Email</strong></label><br><input type="email" id="cab-email" required class="regular-text" style="width:100%"></p>';
        $html .= '<p><label><strong>Password</strong></label><br><input type="password" id="cab-password" required class="regular-text" style="width:100%"></p>';
        $html .= '<button id="cab-login-btn" class="button button-primary" style="width:100%">Login</button>';
        $html .= '<p style="text-align:center;margin-top:8px"><a href="#" id="cab-show-register">Create account</a></p>';
        $html .= '</div>';
        $html .= '<div id="cab-register-form" style="display:none">';
        $html .= '<p><label><strong>Name</strong></label><br><input type="text" id="cab-reg-name" required class="regular-text" style="width:100%"></p>';
        $html .= '<p><label><strong>Email</strong></label><br><input type="email" id="cab-reg-email" required class="regular-text" style="width:100%"></p>';
        $html .= '<p><label><strong>Password</strong></label><br><input type="password" id="cab-reg-password" required minlength="6" class="regular-text" style="width:100%"></p>';
        $html .= '<button id="cab-register-btn" class="button button-primary" style="width:100%">Create Account & Login</button>';
        $html .= '<p style="text-align:center;margin-top:8px"><a href="#" id="cab-show-login">Already have account? Login</a></p>';
        $html .= '</div>';
        $html .= '</div>';
        $html .= '<div id="cab-auth-error" class="notice notice-error" style="display:none;margin-top:8px"></div>';
        $html .= '</div>';
        return $html;
    }

    ob_start();
    ?>
    <div class="cab-form-wrap">
        <h3>Post Your Ad</h3>
        <form id="cab-ad-form">
            <p><label><strong>Title *</strong></label><br><input type="text" id="cab-title" required maxlength="200" class="regular-text" style="width:100%"></p>
            <p><label><strong>Description *</strong></label><br><textarea id="cab-description" required minlength="10" rows="5" style="width:100%"></textarea></p>
            <p><label><strong>Category *</strong></label><br><select id="cab-category" required style="width:100%">
                <option value="">Select...</option>
            </select></p>
            <p><label><strong>Location *</strong></label><br><input type="text" id="cab-location" required maxlength="200" class="regular-text" style="width:100%"></p>
            <p><label><strong>Price</strong></label><br><input type="number" id="cab-price" step="0.01" min="0" class="regular-text"></p>
            <p><label><strong>Contact Info</strong></label><br><input type="text" id="cab-contact" maxlength="500" class="regular-text" style="width:100%"></p>
            <p><label><strong>Images</strong></label><br><input type="file" id="cab-images" multiple accept="image/*"></p>
            <div id="cab-error" class="notice notice-error" style="display:none"></div>
            <p><button type="submit" class="button button-primary button-hero">Post Ad</button></p>
        </form>
    </div>
    <?php
    return ob_get_clean();
}

// --- Shortcode: [my_classified_ads] ---
add_shortcode('my_classified_ads', 'cab_render_my_ads');

function cab_render_my_ads() {
    if (!is_user_logged_in()) return '<p>Please <a href="' . wp_login_url() . '">login</a> to view your ads.</p>';
    return '<div id="cab-my-ads"><p>Loading your ads...</p></div>';
}

// --- Activate ---
register_activation_hook(__FILE__, function () {
    // Create "Classifieds" WP category if not exists
    if (!get_term_by('name', 'Classifieds', 'category')) {
        wp_insert_term('Classifieds', 'category');
    }
});
