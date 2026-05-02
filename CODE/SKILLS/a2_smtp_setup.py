#!/usr/bin/env python3
"""
A2 Hosting SMTP Sender Setup

Automates setup of email sending domains via A2 Hosting SMTP:
- Creates email accounts (office@domain.eu)
- Adds DNS records (SPF, DMARC) for deliverability
- Resets passwords and saves credentials
- Generates campaign sender configs

Commands:
    setup <domain>              Full setup: create email + DNS records
    bulk <domain1> <domain2>... Setup multiple domains at once
    reset-password <domain>     Reset password for existing account
    reset-bulk <d1> <d2>...     Reset passwords for multiple domains
    status <domain>             Check email and DNS status
    list                        List all domains with email accounts
    add-to-env <domain>         Add credentials to /opt/ACTIVE/EMAIL/CAMPAIGNS/.env
    add-all-to-env              Add all stored credentials to .env
    generate-config <domain>    Generate sender config for campaigns
    generate-all-configs        Generate configs for all stored credentials

Examples:
    # Full setup for new domain
    python3 a2_smtp_setup.py setup horecaworkers.eu

    # Setup multiple domains
    python3 a2_smtp_setup.py bulk horecaworkers.eu meatworkers.eu farmworkers.eu

    # Reset password and save (for existing accounts)
    python3 a2_smtp_setup.py reset-bulk horecaworkers.eu meatworkers.eu

    # Add all to .env after reset
    python3 a2_smtp_setup.py add-all-to-env

    # Generate campaign configs
    python3 a2_smtp_setup.py generate-all-configs

A2 Hosting SMTP Settings:
    Server: nl1-cl8-ats1.a2hosting.com
    Port: 465 (SSL) or 587 (TLS)
    Auth: Email account credentials
    Limit: ~500/hour per account (use 500/day to be safe)
"""

import os
import sys
import json
import secrets
import string
import subprocess
import urllib.parse
import urllib.request
import ssl
from pathlib import Path

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/.a2hosting.env'))
load_dotenv('/opt/.env')

# A2 Hosting API settings
A2_HOST = os.getenv('A2_HOST', 'nl1-cl8-ats1.a2hosting.com')
A2_USER = os.getenv('A2_SSH_USER', 'loaiidil')
A2_TOKEN = os.getenv('A2_CPANEL_TOKEN')
A2_SMTP_SERVER = A2_HOST
A2_SMTP_PORT_SSL = 465
A2_SMTP_PORT_TLS = 587

if not A2_TOKEN:
    print("ERROR: A2_CPANEL_TOKEN not set. Check ~/.a2hosting.env or /opt/.env")
    sys.exit(1)

# Paths
ENV_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
CREDENTIALS_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json")


def api_call(module, func, params=None):
    """Make cPanel API call."""
    params = params or {}
    params_str = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())

    url = f"https://{A2_HOST}:2083/execute/{module}/{func}"
    if params_str:
        url += f"?{params_str}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"cpanel {A2_USER}:{A2_TOKEN}")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"errors": [str(e)]}


def api_call_v2(module, func, params=None):
    """Make cPanel API v2 call (for DNS)."""
    params = params or {}
    params["cpanel_jsonapi_user"] = A2_USER
    params["cpanel_jsonapi_apiversion"] = "2"
    params["cpanel_jsonapi_module"] = module
    params["cpanel_jsonapi_func"] = func

    params_str = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
    url = f"https://{A2_HOST}:2083/json-api/cpanel?{params_str}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"cpanel {A2_USER}:{A2_TOKEN}")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"cpanelresult": {"error": str(e)}}


def generate_password(length=16):
    """Generate secure password."""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(chars) for _ in range(length))


def create_email_account(domain, username="office"):
    """Create email account on A2 Hosting."""
    email = f"{username}@{domain}"
    password = generate_password()

    print(f"Creating email account: {email}")

    result = api_call("Email", "add_pop", {
        "email": username,
        "domain": domain,
        "password": password,
        "quota": 1024  # 1GB quota
    })

    if result.get("errors"):
        # Check if already exists
        if "already exists" in str(result.get("errors", [])).lower():
            print(f"  Account already exists: {email}")
            return {"email": email, "exists": True, "password": None}
        print(f"  Error: {result.get('errors')}")
        return None

    print(f"  Created successfully")
    return {"email": email, "password": password, "exists": False}


def reset_email_password(domain, username="office"):
    """Reset password for existing email account."""
    email = f"{username}@{domain}"
    password = generate_password()

    print(f"Resetting password for: {email}")

    result = api_call("Email", "passwd_pop", {
        "email": username,
        "domain": domain,
        "password": password,
    })

    if result.get("errors"):
        print(f"  Error: {result.get('errors')}")
        return None

    if result.get("status") == 1:
        print(f"  Password reset successfully")
        return {"email": email, "password": password}

    print(f"  Failed: {result}")
    return None


def add_dns_record(domain, record_type, name, value):
    """Add DNS record via cPanel API."""
    params = {
        "domain": domain,
        "type": record_type,
        "name": name,
    }

    if record_type == "TXT":
        params["txtdata"] = value
    elif record_type == "CNAME":
        params["cname"] = value

    result = api_call_v2("ZoneEdit", "add_zone_record", params)

    cpresult = result.get("cpanelresult", {})
    if cpresult.get("error"):
        return False, cpresult.get("error")

    data = cpresult.get("data", [{}])[0]
    if data.get("result", {}).get("status") == 1:
        return True, "Added"

    # Check for already exists
    if "already exists" in str(data).lower() or "duplicate" in str(data).lower():
        return True, "Already exists"

    return False, str(data)


def setup_dns_for_email(domain):
    """Set up SPF, DKIM, DMARC for email deliverability."""
    print(f"\nSetting up DNS records for {domain}...")

    # SPF record - allows A2 Hosting to send
    spf_value = "v=spf1 +a +mx +ip4:68.66.216.0/24 +ip4:68.66.217.0/24 include:_spf.a2hosting.com ~all"
    print(f"  Adding SPF record...")
    ok, msg = add_dns_record(domain, "TXT", f"{domain}.", spf_value)
    print(f"    {'OK' if ok else 'FAILED'}: {msg}")

    # DMARC record
    dmarc_value = "v=DMARC1; p=quarantine; rua=mailto:dmarc@interjob.ro"
    print(f"  Adding DMARC record...")
    ok, msg = add_dns_record(domain, "TXT", f"_dmarc.{domain}.", dmarc_value)
    print(f"    {'OK' if ok else 'FAILED'}: {msg}")

    # Note: DKIM requires cPanel to generate keys
    print(f"  Note: DKIM must be enabled via cPanel Email Deliverability")

    return True


def check_domain_status(domain):
    """Check email and DNS status for domain."""
    print(f"\n=== Status: {domain} ===\n")

    # Check email accounts
    result = api_call("Email", "list_pops")
    accounts = [d["email"] for d in result.get("data", []) if domain in d.get("email", "")]

    print(f"Email accounts: {accounts if accounts else 'None'}")

    # Check DNS (via external lookup)
    print(f"\nDNS Records:")
    try:
        import subprocess
        # SPF
        spf = subprocess.run(["host", "-t", "TXT", domain], capture_output=True, text=True, timeout=5)
        if "spf" in spf.stdout.lower():
            print(f"  SPF: OK")
        else:
            print(f"  SPF: MISSING")

        # DMARC
        dmarc = subprocess.run(["host", "-t", "TXT", f"_dmarc.{domain}"], capture_output=True, text=True, timeout=5)
        if "dmarc" in dmarc.stdout.lower():
            print(f"  DMARC: OK")
        else:
            print(f"  DMARC: MISSING")
    except:
        print(f"  Could not check DNS")

    return accounts


def save_credentials(domain, email, password):
    """Save credentials to JSON file."""
    creds = {}
    if CREDENTIALS_FILE.exists():
        creds = json.loads(CREDENTIALS_FILE.read_text())

    creds[domain] = {
        "email": email,
        "password": password,
        "smtp_server": A2_SMTP_SERVER,
        "smtp_port": A2_SMTP_PORT_SSL,
        "created": str(__import__("datetime").datetime.now())
    }

    CREDENTIALS_FILE.write_text(json.dumps(creds, indent=2))
    CREDENTIALS_FILE.chmod(0o600)
    print(f"  Credentials saved to {CREDENTIALS_FILE}")


def add_to_env(domain):
    """Add A2 SMTP credentials to .env file."""
    if not CREDENTIALS_FILE.exists():
        print(f"No credentials file found. Run setup first.")
        return False

    creds = json.loads(CREDENTIALS_FILE.read_text())
    if domain not in creds:
        print(f"No credentials for {domain}. Run setup first.")
        return False

    c = creds[domain]

    # Generate env variable name
    var_name = domain.replace(".", "_").replace("-", "_").upper()

    env_lines = [
        f"\n# A2 SMTP - {domain}",
        f"A2_{var_name}_EMAIL={c['email']}",
        f"A2_{var_name}_PASSWORD={c['password']}",
        f"A2_{var_name}_SERVER={c['smtp_server']}",
        f"A2_{var_name}_PORT={c['smtp_port']}",
    ]

    # Append to .env
    with open(ENV_FILE, "a") as f:
        f.write("\n".join(env_lines) + "\n")

    print(f"Added to {ENV_FILE}:")
    for line in env_lines[1:]:
        print(f"  {line.split('=')[0]}=***")

    return True


def generate_sender_config(domain, sender_name=None):
    """Generate sender config for campaign system."""
    if not CREDENTIALS_FILE.exists():
        print(f"No credentials file found. Run setup first.")
        return None

    creds = json.loads(CREDENTIALS_FILE.read_text())
    if domain not in creds:
        print(f"No credentials for {domain}. Run setup first.")
        return None

    c = creds[domain]
    var_name = domain.replace(".", "_").replace("-", "_").lower()

    # Default sender name from domain
    if not sender_name:
        sender_name = domain.split(".")[0].replace("workers", " Workers").replace("jobs", " Jobs").title()

    config = f'''
# A2 SMTP Sender: {domain}
"a2_{var_name}": {{
    "type": "smtp",
    "email": "{c['email']}",
    "password": os.getenv("A2_{domain.replace(".", "_").replace("-", "_").upper()}_PASSWORD"),
    "smtp_server": "{A2_SMTP_SERVER}",
    "smtp_port": {A2_SMTP_PORT_SSL},
    "use_ssl": True,
    "sender_name": "{sender_name}",
    "daily_limit": 500,  # A2 limit ~500/hour, be conservative
    "warmup_days": 0,    # No warmup needed for A2
}},
'''
    print(config)
    return config


def list_all_domains():
    """List all domains with email capability."""
    result = api_call("Email", "list_pops")

    domains = {}
    for acc in result.get("data", []):
        email = acc.get("email", "")
        if "@" in email:
            domain = email.split("@")[1]
            if domain not in domains:
                domains[domain] = []
            domains[domain].append(email)

    print("\n=== Domains with Email Accounts ===\n")
    for domain, emails in sorted(domains.items()):
        print(f"{domain}:")
        for email in emails:
            print(f"  - {email}")

    return domains


def setup_domain(domain, email_user="office"):
    """Full setup: create email + DNS records."""
    print(f"\n{'='*50}")
    print(f"Setting up {domain} for A2 SMTP sending")
    print(f"{'='*50}")

    # 1. Create email account
    result = create_email_account(domain, email_user)
    if not result:
        return False

    # 2. Save credentials if new account
    if not result.get("exists") and result.get("password"):
        save_credentials(domain, result["email"], result["password"])

    # 3. Set up DNS
    setup_dns_for_email(domain)

    print(f"\n{'='*50}")
    print(f"Setup complete for {domain}")
    print(f"{'='*50}")

    if result.get("password"):
        print(f"\nCredentials:")
        print(f"  Email: {result['email']}")
        print(f"  Password: {result['password']}")
        print(f"  SMTP Server: {A2_SMTP_SERVER}")
        print(f"  SMTP Port: {A2_SMTP_PORT_SSL} (SSL)")

    print(f"\nNext steps:")
    print(f"  1. Wait 1-24h for DNS propagation")
    print(f"  2. Enable DKIM in cPanel > Email Deliverability")
    print(f"  3. Run: python3 a2_smtp_setup.py add-to-env {domain}")
    print(f"  4. Add sender config to campaign system")

    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "setup" and len(sys.argv) >= 3:
        domain = sys.argv[2]
        email_user = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--email" else "office"
        setup_domain(domain, email_user)

    elif cmd == "bulk" and len(sys.argv) >= 3:
        domains = sys.argv[2:]
        for domain in domains:
            setup_domain(domain)
            print("\n")

    elif cmd == "reset-password" and len(sys.argv) >= 3:
        domain = sys.argv[2]
        email_user = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--email" else "office"
        result = reset_email_password(domain, email_user)
        if result:
            save_credentials(domain, result["email"], result["password"])
            print(f"\nCredentials saved. Run: python3 a2_smtp_setup.py add-to-env {domain}")

    elif cmd == "reset-bulk" and len(sys.argv) >= 3:
        domains = sys.argv[2:]
        for domain in domains:
            result = reset_email_password(domain)
            if result:
                save_credentials(domain, result["email"], result["password"])
            print()

    elif cmd == "status" and len(sys.argv) >= 3:
        check_domain_status(sys.argv[2])

    elif cmd == "list":
        list_all_domains()

    elif cmd == "add-to-env" and len(sys.argv) >= 3:
        add_to_env(sys.argv[2])

    elif cmd == "add-all-to-env":
        if CREDENTIALS_FILE.exists():
            creds = json.loads(CREDENTIALS_FILE.read_text())
            for domain in creds:
                add_to_env(domain)
        else:
            print("No credentials file found")

    elif cmd == "generate-config" and len(sys.argv) >= 3:
        sender_name = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--name" else None
        generate_sender_config(sys.argv[2], sender_name)

    elif cmd == "generate-all-configs":
        if CREDENTIALS_FILE.exists():
            creds = json.loads(CREDENTIALS_FILE.read_text())
            print("# A2 SMTP Senders - Add to /opt/ACTIVE/EMAIL/CAMPAIGNS/config.py AVAILABLE_SENDERS\n")
            for domain in creds:
                generate_sender_config(domain)
        else:
            print("No credentials file found")

    elif cmd == "help":
        print(__doc__)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
