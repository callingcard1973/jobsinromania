#!/usr/bin/env python3
"""
EEATINGH Skill Deployment Script

This script deploys the EEATINGH platform skill to raspibig and sets up
the necessary environment, dependencies, and automation.

Usage:
python deploy_eeatingh_skill.py [--install-deps] [--setup-cron] [--test]
"""

import subprocess
import os
import json
import argparse
from pathlib import Path

def run_command(cmd, description=""):
    """Run a shell command and return result."""
    try:
        if description:
            print(f"🔧 {description}")

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✅ Success: {description}")
            return True, result.stdout
        else:
            print(f"❌ Failed: {description}")
            print(f"Error: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"❌ Exception in {description}: {e}")
        return False, str(e)

def deploy_to_raspibig():
    """Deploy skill files to raspibig."""
    print("🚀 Deploying EEATINGH skill to raspibig...")

    # Create skill directory
    cmd = 'ssh tudor@192.168.100.21 "mkdir -p /opt/ACTIVE/INFRA/SKILLS/EEATINGH"'
    success, _ = run_command(cmd, "Creating skill directory on raspibig")

    if not success:
        return False

    # Copy main skill file
    cmd = 'scp "D:/MEMORY/eeatingh_platform_skill.py" tudor@192.168.100.21:/opt/ACTIVE/INFRA/SKILLS/EEATINGH/'
    success, _ = run_command(cmd, "Copying main skill file")

    if not success:
        return False

    # Copy configuration file
    cmd = 'scp "D:/MEMORY/eeatingh_config.json" tudor@192.168.100.21:/opt/ACTIVE/INFRA/SKILLS/EEATINGH/'
    success, _ = run_command(cmd, "Copying configuration file")

    if not success:
        return False

    # Make skill executable
    cmd = 'ssh tudor@192.168.100.21 "chmod +x /opt/ACTIVE/INFRA/SKILLS/EEATINGH/eeatingh_platform_skill.py"'
    success, _ = run_command(cmd, "Making skill executable")

    return success

def install_dependencies():
    """Install required Python dependencies on raspibig."""
    print("📦 Installing dependencies...")

    dependencies = [
        "requests",
        "beautifulsoup4",
        "pandas",
        "lxml"
    ]

    for dep in dependencies:
        cmd = f'ssh tudor@192.168.100.21 "python3 -m pip install {dep}"'
        success, _ = run_command(cmd, f"Installing {dep}")

        if not success:
            print(f"⚠️  Failed to install {dep}, continuing...")

    return True

def create_wrapper_scripts():
    """Create wrapper scripts for easy skill execution."""
    print("📝 Creating wrapper scripts...")

    # Create main wrapper script
    wrapper_content = '''#!/bin/bash
# EEATINGH Platform Skill Wrapper
# Usage: eeatingh <command> [options]

SKILL_DIR="/opt/ACTIVE/INFRA/SKILLS/EEATINGH"
SKILL_SCRIPT="$SKILL_DIR/eeatingh_platform_skill.py"

cd "$SKILL_DIR"

case "$1" in
    "login")
        python3 "$SKILL_SCRIPT" --action=login
        ;;
    "dashboard")
        python3 "$SKILL_SCRIPT" --action=dashboard
        ;;
    "export-products")
        python3 "$SKILL_SCRIPT" --action=export_products --file="${2:-products.csv}"
        ;;
    "import-products")
        if [ -z "$2" ]; then
            echo "Usage: eeatingh import-products <csv_file>"
            exit 1
        fi
        python3 "$SKILL_SCRIPT" --action=import_products --file="$2"
        ;;
    "campaign")
        city="${2:-all}"
        python3 "$SKILL_SCRIPT" --action=generate_campaign --city="$city"
        ;;
    "analytics")
        days="${2:-7}"
        python3 "$SKILL_SCRIPT" --action=analytics --days="$days"
        ;;
    "publish")
        python3 "$SKILL_SCRIPT" --action=publish_store
        ;;
    "status")
        python3 "$SKILL_SCRIPT" --action=store_status
        ;;
    "test")
        python3 "$SKILL_SCRIPT" --action=test
        ;;
    *)
        echo "EEATINGH Platform Skill"
        echo "Usage: eeatingh <command> [options]"
        echo ""
        echo "Commands:"
        echo "  login                    - Test platform login"
        echo "  dashboard                - Get dashboard stats"
        echo "  export-products [file]   - Export products to CSV"
        echo "  import-products <file>   - Import products from CSV"
        echo "  campaign [city]          - Generate restaurant campaign"
        echo "  analytics [days]         - Performance analytics"
        echo "  publish                  - Publish store"
        echo "  status                   - Check store status"
        echo "  test                     - Run all tests"
        echo ""
        echo "Examples:"
        echo "  eeatingh dashboard"
        echo "  eeatingh campaign Medias"
        echo "  eeatingh export-products my_products.csv"
        ;;
esac
'''

    # Write wrapper to temporary file then copy
    with open("eeatingh_wrapper.sh", "w") as f:
        f.write(wrapper_content)

    # Copy to raspibig
    cmd = 'scp "eeatingh_wrapper.sh" tudor@192.168.100.21:/opt/ACTIVE/INFRA/SKILLS/EEATINGH/'
    success, _ = run_command(cmd, "Copying wrapper script")

    if success:
        # Make executable and create symlink
        cmd = 'ssh tudor@192.168.100.21 "chmod +x /opt/ACTIVE/INFRA/SKILLS/EEATINGH/eeatingh_wrapper.sh && ln -sf /opt/ACTIVE/INFRA/SKILLS/EEATINGH/eeatingh_wrapper.sh /usr/local/bin/eeatingh"'
        success, _ = run_command(cmd, "Making wrapper executable and creating symlink")

    # Clean up temporary file
    os.remove("eeatingh_wrapper.sh")

    return success

def setup_automation():
    """Setup cron jobs and automation for EEATINGH monitoring."""
    print("⏰ Setting up automation...")

    # Create cron job for daily analytics
    cron_content = '''# EEATINGH Platform Automation
# Daily analytics report at 8 AM
0 8 * * * /usr/local/bin/eeatingh analytics 1 >> /var/log/eeatingh_daily.log 2>&1

# Weekly analytics report every Monday at 9 AM
0 9 * * 1 /usr/local/bin/eeatingh analytics 7 >> /var/log/eeatingh_weekly.log 2>&1

# Daily dashboard check at 6 AM
0 6 * * * /usr/local/bin/eeatingh dashboard >> /var/log/eeatingh_status.log 2>&1
'''

    # Write cron content to file
    with open("eeatingh_cron.txt", "w") as f:
        f.write(cron_content)

    # Copy and install cron job
    cmd = 'scp "eeatingh_cron.txt" tudor@192.168.100.21:/tmp/'
    success, _ = run_command(cmd, "Copying cron configuration")

    if success:
        cmd = 'ssh tudor@192.168.100.21 "crontab -l > /tmp/current_cron 2>/dev/null; cat /tmp/eeatingh_cron.txt >> /tmp/current_cron; crontab /tmp/current_cron; rm /tmp/eeatingh_cron.txt /tmp/current_cron"'
        success, _ = run_command(cmd, "Installing cron jobs")

    # Clean up
    os.remove("eeatingh_cron.txt")

    return success

def test_deployment():
    """Test the deployed skill."""
    print("🧪 Testing deployment...")

    # Test skill execution
    cmd = 'ssh tudor@192.168.100.21 "eeatingh test"'
    success, output = run_command(cmd, "Running skill test")

    if success:
        print(f"📊 Test output:\n{output}")

    return success

def create_documentation():
    """Create documentation file on raspibig."""
    doc_content = """# EEATINGH Platform Skill Documentation

## Installation Location
- Main skill: `/opt/ACTIVE/INFRA/SKILLS/EEATINGH/eeatingh_platform_skill.py`
- Configuration: `/opt/ACTIVE/INFRA/SKILLS/EEATINGH/eeatingh_config.json`
- Wrapper: `/usr/local/bin/eeatingh`

## Quick Commands

### Platform Management
```bash
eeatingh login          # Test platform connection
eeatingh dashboard      # Get current stats
eeatingh status         # Check store status
eeatingh publish        # Publish store to go live
```

### Product Management
```bash
eeatingh export-products                    # Export all products
eeatingh export-products my_products.csv    # Export to specific file
eeatingh import-products products.csv       # Import from CSV
```

### Campaign Management
```bash
eeatingh campaign              # Generate campaign for all cities
eeatingh campaign Medias       # Generate campaign for Medias
eeatingh campaign Buzau        # Generate campaign for Buzau
```

### Analytics
```bash
eeatingh analytics         # 7-day performance report
eeatingh analytics 30      # 30-day performance report
eeatingh analytics 1       # Daily report
```

## Configuration
Edit `/opt/ACTIVE/INFRA/SKILLS/EEATINGH/eeatingh_config.json` for:
- Login credentials
- Store settings
- Campaign parameters
- API endpoints
- Webhook configuration

## Automation
Cron jobs are set for:
- Daily analytics: 8:00 AM
- Weekly reports: Monday 9:00 AM
- Status checks: 6:00 AM daily

## Logs
- Daily logs: `/var/log/eeatingh_daily.log`
- Weekly logs: `/var/log/eeatingh_weekly.log`
- Status logs: `/var/log/eeatingh_status.log`

## Troubleshooting

### Login Issues
1. Check credentials in config.json
2. Verify platform accessibility: `curl https://eeatingh.ro`
3. Test manual login at https://eeatingh.ro/admin

### Import/Export Issues
1. Verify CSV format matches template
2. Check file permissions
3. Ensure store is published

### Campaign Issues
1. Verify restaurant database exists
2. Check email/phone data availability
3. Validate SMTP settings for email campaigns

## Support
- Configuration: `/opt/ACTIVE/INFRA/SKILLS/EEATINGH/eeatingh_config.json`
- Logs: `/var/log/eeatingh_*.log`
- Manual execution: `python3 /opt/ACTIVE/INFRA/SKILLS/EEATINGH/eeatingh_platform_skill.py`

Created: 2026-04-04
Version: 1.0
"""

    # Write documentation
    with open("eeatingh_documentation.md", "w") as f:
        f.write(doc_content)

    # Copy to raspibig
    cmd = 'scp "eeatingh_documentation.md" tudor@192.168.100.21:/opt/ACTIVE/INFRA/SKILLS/EEATINGH/'
    success, _ = run_command(cmd, "Creating documentation")

    # Clean up
    os.remove("eeatingh_documentation.md")

    return success

def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy EEATINGH Platform Skill")
    parser.add_argument("--install-deps", action="store_true", help="Install Python dependencies")
    parser.add_argument("--setup-cron", action="store_true", help="Setup cron automation")
    parser.add_argument("--test", action="store_true", help="Test deployment")
    parser.add_argument("--all", action="store_true", help="Full deployment with all options")

    args = parser.parse_args()

    print("🍽️ EEATINGH Platform Skill Deployment")
    print("=" * 50)

    # Deploy core files
    if not deploy_to_raspibig():
        print("❌ Core deployment failed")
        return False

    # Install dependencies if requested
    if args.install_deps or args.all:
        install_dependencies()

    # Create wrapper scripts
    if not create_wrapper_scripts():
        print("❌ Wrapper script creation failed")
        return False

    # Setup automation if requested
    if args.setup_cron or args.all:
        setup_automation()

    # Create documentation
    create_documentation()

    # Test if requested
    if args.test or args.all:
        test_deployment()

    print("\n✅ EEATINGH Platform Skill Deployment Complete!")
    print("\nQuick Start:")
    print("ssh tudor@192.168.100.21")
    print("eeatingh login")
    print("eeatingh dashboard")
    print("eeatingh campaign Medias")

    return True

if __name__ == "__main__":
    main()