#!/usr/bin/env python3
"""
A2 Hosting WordPress Installer
Usage: a2_wordpress_install.py <domain> [--title "Site Title"] [--email admin@domain.com]

Example:
    a2_wordpress_install.py buildjobs.eu --title "BuildJobs EU" --email office@buildjobs.eu
"""

import os
import sys
import json
import random
import string
import hashlib
import argparse
import subprocess
import tempfile
import requests
from pathlib import Path

# Load credentials
def load_env():
    env_file = Path.home() / '.a2hosting.env'
    env = {}
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                key, val = line.split('=', 1)
                env[key.strip()] = val.strip().strip('"\'')
    return env

ENV = load_env()
A2_HOST = ENV.get('A2_HOST', 'nl1-cl8-ats1.a2hosting.com')
A2_USER = ENV.get('A2_SSH_USER', 'loaiidil')
A2_TOKEN = ENV.get('A2_CPANEL_TOKEN', '')
A2_PORT = ENV.get('A2_CPANEL_PORT', '2083')

CPANEL_URL = f"https://{A2_HOST}:{A2_PORT}"
HEADERS = {"Authorization": f"cpanel {A2_USER}:{A2_TOKEN}"}


def random_string(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def cpanel_api(endpoint, params=None):
    """Call cPanel UAPI"""
    url = f"{CPANEL_URL}/execute/{endpoint}"
    try:
        r = requests.get(url, headers=HEADERS, params=params, verify=False, timeout=30)
        return r.json()
    except Exception as e:
        return {"status": 0, "errors": [str(e)]}


def upload_file(local_path, remote_dir, remote_name=None):
    """Upload file via cPanel API"""
    if remote_name is None:
        remote_name = os.path.basename(local_path)

    url = f"{CPANEL_URL}/execute/Fileman/upload_files"
    files = {'file-1': (remote_name, open(local_path, 'rb'))}
    data = {'dir': f'/home/{A2_USER}/{remote_dir}', 'overwrite': '1'}

    try:
        r = requests.post(url, headers=HEADERS, files=files, data=data, verify=False, timeout=120)
        return r.json().get('status') == 1
    except Exception as e:
        print(f"Upload error: {e}")
        return False


def create_database(db_suffix):
    """Create MySQL database"""
    db_name = f"{A2_USER}_{db_suffix}"
    result = cpanel_api("Mysql/create_database", {"name": db_name})
    if result.get('status') == 1:
        print(f"✓ Database created: {db_name}")
        return db_name
    elif "already exists" in str(result.get('errors', [])):
        print(f"✓ Database exists: {db_name}")
        return db_name
    else:
        print(f"✗ Database error: {result.get('errors')}")
        return None


def create_db_user(user_suffix, password):
    """Create MySQL user"""
    user_name = f"{A2_USER}_{user_suffix}"
    result = cpanel_api("Mysql/create_user", {"name": user_name, "password": password})
    if result.get('status') == 1:
        print(f"✓ DB user created: {user_name}")
        return user_name
    elif "already exists" in str(result.get('errors', [])):
        print(f"✓ DB user exists: {user_name}")
        return user_name
    else:
        print(f"✗ DB user error: {result.get('errors')}")
        return None


def grant_privileges(user, database):
    """Grant ALL PRIVILEGES on database to user"""
    result = cpanel_api("Mysql/set_privileges_on_database", {
        "user": user,
        "database": database,
        "privileges": "ALL PRIVILEGES"
    })
    if result.get('status') == 1:
        print(f"✓ Privileges granted")
        return True
    else:
        print(f"✗ Privileges error: {result.get('errors')}")
        return False


def generate_wp_config(db_name, db_user, db_pass):
    """Generate wp-config.php content"""
    salts = '\n'.join([
        f"define( '{key}', '{random_string(64)}' );"
        for key in ['AUTH_KEY', 'SECURE_AUTH_KEY', 'LOGGED_IN_KEY', 'NONCE_KEY',
                    'AUTH_SALT', 'SECURE_AUTH_SALT', 'LOGGED_IN_SALT', 'NONCE_SALT']
    ])

    return f"""<?php
define( 'DB_NAME', '{db_name}' );
define( 'DB_USER', '{db_user}' );
define( 'DB_PASSWORD', '{db_pass}' );
define( 'DB_HOST', 'localhost' );
define( 'DB_CHARSET', 'utf8mb4' );
define( 'DB_COLLATE', '' );

{salts}

$table_prefix = 'wp_';
define( 'WP_DEBUG', false );

if ( ! defined( 'ABSPATH' ) ) {{
    define( 'ABSPATH', __DIR__ . '/' );
}}
require_once ABSPATH . 'wp-settings.php';
"""


def generate_setup_php():
    """Generate PHP script to extract WordPress"""
    return """<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);

$base = dirname(__FILE__);
chdir($base);

// Extract
$output = shell_exec('unzip -o wordpress.zip 2>&1');
echo "Extract: " . substr($output, 0, 200) . "...\\n";

// Move files
shell_exec('cp -r wordpress/* . 2>&1');
echo "Copied files\\n";

// Cleanup
shell_exec('rm -rf wordpress wordpress.zip wp_setup.php 2>&1');
echo "Cleaned up\\n";

// Verify
if (file_exists('wp-config-sample.php')) {
    echo "SUCCESS: WordPress installed!\\n";
} else {
    echo "ERROR: wp-config-sample.php not found\\n";
}
?>"""


def install_wordpress(domain, title, admin_email, admin_user='admin'):
    """Main installation function"""
    print(f"\n=== Installing WordPress on {domain} ===\n")

    # Generate credentials
    db_suffix = domain.replace('.', '').replace('-', '')[:8]
    db_pass = f"Wp{random_string(10)}!"
    admin_pass = f"Admin{random_string(10)}!"

    # 1. Create database
    db_name = create_database(db_suffix)
    if not db_name:
        return False

    # 2. Create DB user
    db_user = create_db_user(db_suffix[:7], db_pass)
    if not db_user:
        return False

    # 3. Grant privileges
    if not grant_privileges(db_user, db_name):
        return False

    # 4. Download WordPress locally
    print("↓ Downloading WordPress...")
    wp_dir = tempfile.mkdtemp()
    wp_zip = os.path.join(wp_dir, 'wordpress.zip')
    subprocess.run(['curl', '-sLo', wp_zip, 'https://wordpress.org/latest.tar.gz'], check=True)
    subprocess.run(['tar', '-xzf', wp_zip, '-C', wp_dir], check=True)

    # Repack as zip for easier extraction
    subprocess.run(['bash', '-c', f'cd {wp_dir} && zip -rq wordpress.zip wordpress/'], check=True)
    wp_zip = os.path.join(wp_dir, 'wordpress.zip')

    if not os.path.exists(wp_zip):
        # Fallback - download zip directly
        subprocess.run(['curl', '-sLo', wp_zip, 'https://wordpress.org/latest.zip'], check=True)

    print(f"✓ WordPress downloaded ({os.path.getsize(wp_zip) // 1024 // 1024}MB)")

    # 5. Upload WordPress zip
    print("↑ Uploading WordPress...")
    if not upload_file(wp_zip, domain, 'wordpress.zip'):
        print("✗ Failed to upload WordPress")
        return False
    print("✓ WordPress uploaded")

    # 6. Upload setup script
    setup_php = os.path.join(wp_dir, 'wp_setup.php')
    with open(setup_php, 'w') as f:
        f.write(generate_setup_php())

    if not upload_file(setup_php, domain, 'wp_setup.php'):
        print("✗ Failed to upload setup script")
        return False

    # 7. Execute setup script
    print("⚙ Extracting WordPress...")
    try:
        r = requests.get(f"https://{domain}/wp_setup.php", timeout=60, verify=False)
        if 'SUCCESS' in r.text:
            print("✓ WordPress extracted")
        else:
            print(f"✗ Extract failed: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"✗ Setup error: {e}")
        return False

    # 8. Upload wp-config.php
    wp_config = os.path.join(wp_dir, 'wp-config.php')
    with open(wp_config, 'w') as f:
        f.write(generate_wp_config(db_name, db_user, db_pass))

    if not upload_file(wp_config, domain, 'wp-config.php'):
        print("✗ Failed to upload wp-config.php")
        return False
    print("✓ wp-config.php uploaded")

    # 9. Run WordPress installation
    print("⚙ Running WordPress setup...")
    try:
        # Step 1 - language
        requests.post(f"https://{domain}/wp-admin/install.php?step=1",
                     data={"language": ""}, timeout=30, verify=False)

        # Step 2 - site info
        r = requests.post(f"https://{domain}/wp-admin/install.php?step=2", data={
            "weblog_title": title,
            "user_name": admin_user,
            "admin_password": admin_pass,
            "admin_password2": admin_pass,
            "admin_email": admin_email,
            "blog_public": "1"
        }, timeout=30, verify=False)

        # Verify
        r = requests.get(f"https://{domain}/", timeout=10, verify=False)
        if title.lower() in r.text.lower() or 'wordpress' in r.text.lower():
            print("✓ WordPress installed successfully!")
        else:
            print("⚠ Installation may need manual completion")
    except Exception as e:
        print(f"⚠ Setup warning: {e}")

    # Cleanup temp files
    subprocess.run(['rm', '-rf', wp_dir])

    # Print credentials
    print(f"""
=== WordPress Installed ===

Site URL:  https://{domain}/
Admin URL: https://{domain}/wp-admin/

Admin User:     {admin_user}
Admin Password: {admin_pass}
Admin Email:    {admin_email}

Database:       {db_name}
DB User:        {db_user}
DB Password:    {db_pass}

Save these credentials securely!
""")

    return True


def main():
    parser = argparse.ArgumentParser(description='Install WordPress on A2 Hosting')
    parser.add_argument('domain', help='Domain name (e.g., example.com)')
    parser.add_argument('--title', default=None, help='Site title')
    parser.add_argument('--email', default=None, help='Admin email')
    parser.add_argument('--user', default='admin', help='Admin username')

    args = parser.parse_args()

    title = args.title or args.domain.replace('.', ' ').title()
    email = args.email or f"admin@{args.domain}"

    # Suppress SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    success = install_wordpress(args.domain, title, email, args.user)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
