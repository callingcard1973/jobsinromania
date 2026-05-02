#!/usr/bin/env python3
"""
WordPress Claude API - Multi-site deployment tool
Manage files on WordPress sites with Claude API plugin installed

Usage:
    python3 wp_claude_api.py --site oipa.ro --ping
    python3 wp_claude_api.py --site oipa.ro --list [path]
    python3 wp_claude_api.py --site oipa.ro --deploy /path/to/build --target new/
    python3 wp_claude_api.py --site oipa.ro --upload local.html remote.html
    python3 wp_claude_api.py --site oipa.ro --delete path/file.html
    python3 wp_claude_api.py --status  # Check all sites
    python3 wp_claude_api.py --install-plugin SITE  # Show install instructions
"""

import os
import sys
import json
import base64
import argparse
import subprocess
import random
from pathlib import Path

# Sites with Claude API plugin (21 WordPress sites)
# Removed: ajwang.org (deprecated), cifn.info (disabled), cifn.eu (static site)
SITES = {
    # External hosting (LiteSpeed)
    "oipa.ro": {"url": "https://oipa.ro/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "external"},
    "hambarulromanesc.ro": {"url": "https://hambarulromanesc.ro/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "external"},
    # A2 Hosting - Original sites
    "cumparlegume.com": {"url": "https://cumparlegume.com/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "seicarescu.com": {"url": "https://seicarescu.com/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "mivromania.com": {"url": "https://mivromania.com/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "haritina.com": {"url": "https://haritina.com/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "baneasa39.com": {"url": "https://baneasa39.com/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "agroevolution.com": {"url": "https://agroevolution.com/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    # A2 Hosting - Job portal multisite + others
    "aluminumrecyclehub.com": {"url": "https://aluminumrecyclehub.com/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "buildjobs.eu": {"url": "https://buildjobs.eu/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "careworkers.eu": {"url": "https://careworkers.eu/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "electricjobs.eu": {"url": "https://electricjobs.eu/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "expatsinromania.org": {"url": "https://expatsinromania.org/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "factoryjobs.eu": {"url": "https://factoryjobs.eu/index.php", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "farmworkers.eu": {"url": "https://farmworkers.eu/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "horecaworkers.eu": {"url": "https://horecaworkers.eu/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "interjob.ro": {"url": "https://interjob.ro/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "meatworkers.eu": {"url": "https://meatworkers.eu/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "mechanicjobs.eu": {"url": "https://mechanicjobs.eu/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "mivromania.info": {"url": "https://mivromania.info/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
    "nepalezi.com": {"url": "https://nepalezi.com/", "key": "oipa-claude-2026-xK9mP2vL", "hosting": "a2"},
}

PLUGIN_URL = "https://files.catbox.moe/sqmfum.zip"


class WPClaudeAPI:
    def __init__(self, site_name):
        if site_name not in SITES:
            raise ValueError(f"Unknown site: {site_name}. Available: {', '.join(SITES.keys())}")

        self.site = SITES[site_name]
        self.name = site_name
        self.url = self.site["url"]
        self.key = self.site["key"]

    def api_call(self, action, params=None, data=None):
        """Make API call to Claude API plugin using curl (avoids proxy issues)"""
        # Add cache buster to avoid LiteSpeed cache
        cache_buster = random.randint(10000, 99999)
        url = f"{self.url}?claude_api={action}&_cb={cache_buster}"
        if params:
            url += "&" + "&".join(f"{k}={v}" for k, v in params.items())

        try:
            if data:
                # POST request
                cmd = ["curl", "-s", "-X", "POST", "-H", f"X-Claude-Key: {self.key}"]
                for k, v in data.items():
                    cmd.extend(["-d", f"{k}={v}"])
                cmd.append(url)
            else:
                # GET request
                cmd = ["curl", "-s", "-H", f"X-Claude-Key: {self.key}", url]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.stdout:
                return json.loads(result.stdout)
            return {"error": "Empty response"}
        except json.JSONDecodeError:
            return {"error": "Not JSON - plugin probably not installed"}
        except subprocess.TimeoutExpired:
            return {"error": "Request timeout"}
        except Exception as e:
            return {"error": str(e)}

    def ping(self):
        """Test API connection"""
        result = self.api_call("ping")
        return result.get("status") == "ok", result

    def list_files(self, path=""):
        """List files in directory"""
        result = self.api_call("list", {"path": path})
        return result

    def upload_file(self, local_path, remote_path):
        """Upload a single file"""
        with open(local_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()

        result = self.api_call("upload", data={
            "path": remote_path,
            "content": content
        })
        return result

    def delete_file(self, remote_path):
        """Delete a file"""
        return self.api_call("delete", {"path": remote_path})

    def mkdir(self, remote_path):
        """Create directory"""
        return self.api_call("mkdir", {"path": remote_path})

    def read_file(self, remote_path):
        """Read file contents"""
        result = self.api_call("read", {"path": remote_path})
        if "content" in result:
            result["content"] = base64.b64decode(result["content"]).decode()
        return result

    def deploy_directory(self, local_dir, target_path=""):
        """Deploy entire directory"""
        local_path = Path(local_dir)
        if not local_path.exists():
            print(f"Error: {local_dir} not found")
            return False

        files = list(local_path.rglob("*"))
        total = len([f for f in files if f.is_file()])
        uploaded = 0

        print(f"Deploying {total} files to {self.url}{target_path}")

        for file_path in files:
            if file_path.is_file():
                relative = file_path.relative_to(local_path)
                remote = target_path + str(relative)

                # Create parent dirs
                parent = str(relative.parent)
                if parent != ".":
                    self.mkdir(target_path + parent)

                # Upload file
                result = self.upload_file(file_path, remote)
                uploaded += 1
                status = "OK" if result.get("status") == "ok" else "FAIL"
                print(f"[{uploaded}/{total}] {status} {remote}")

        print(f"\nDeployed {uploaded} files to {self.url}{target_path}")
        return True


def check_all_sites():
    """Check status of all sites"""
    print("Checking all WordPress sites with Claude API...\n")
    print(f"{'Site':<25} {'Status':<10} {'Hosting'}")
    print("-" * 50)

    for name, config in SITES.items():
        try:
            api = WPClaudeAPI(name)
            ok, result = api.ping()
            status = "OK" if ok else "NO PLUGIN"
        except Exception as e:
            status = "ERROR"

        print(f"{name:<25} {status:<10} {config['hosting']}")


def show_install_instructions(site=None):
    """Show plugin installation instructions"""
    print(f"""
=== CLAUDE API PLUGIN INSTALLATION ===

Plugin ZIP: {PLUGIN_URL}

Steps:
1. Go to WP Admin → Plugins → Add New → Upload Plugin
2. Upload: {PLUGIN_URL}
3. Activate the plugin

The plugin adds these endpoints:
  ?claude_api=ping     - Test connection
  ?claude_api=list     - List directory
  ?claude_api=upload   - Upload file (POST)
  ?claude_api=mkdir    - Create directory
  ?claude_api=delete   - Delete file
  ?claude_api=read     - Read file

API Key: oipa-claude-2026-xK9mP2vL
Header: X-Claude-Key
""")

    if site:
        print(f"Install on: https://{site}/wp-admin/plugin-install.php")
    else:
        print("Sites needing installation:")
        for name in SITES:
            try:
                api = WPClaudeAPI(name)
                ok, _ = api.ping()
                if not ok:
                    print(f"  - {name}")
            except:
                print(f"  - {name}")


def main():
    parser = argparse.ArgumentParser(description="WordPress Claude API Tool")
    parser.add_argument("--site", "-s", help="Target site (e.g., oipa.ro)")
    parser.add_argument("--ping", action="store_true", help="Test API connection")
    parser.add_argument("--list", nargs="?", const="", metavar="PATH", help="List files")
    parser.add_argument("--deploy", metavar="DIR", help="Deploy directory")
    parser.add_argument("--target", default="", help="Target path for deploy (e.g., new/)")
    parser.add_argument("--upload", nargs=2, metavar=("LOCAL", "REMOTE"), help="Upload file")
    parser.add_argument("--delete", metavar="PATH", help="Delete file")
    parser.add_argument("--read", metavar="PATH", help="Read file")
    parser.add_argument("--status", action="store_true", help="Check all sites")
    parser.add_argument("--install-plugin", nargs="?", const="", metavar="SITE", help="Show install instructions")

    args = parser.parse_args()

    if args.status:
        check_all_sites()
        return

    if args.install_plugin is not None:
        show_install_instructions(args.install_plugin if args.install_plugin else None)
        return

    if not args.site:
        parser.print_help()
        print("\nAvailable sites:", ", ".join(SITES.keys()))
        return

    api = WPClaudeAPI(args.site)

    if args.ping:
        ok, result = api.ping()
        print(json.dumps(result, indent=2))
        print(f"\nStatus: {'Connected' if ok else 'Failed'}")

    elif args.list is not None:
        result = api.list_files(args.list)
        if "files" in result:
            for f in result["files"]:
                if f not in [".", ".."]:
                    print(f)
        else:
            print(json.dumps(result, indent=2))

    elif args.deploy:
        api.deploy_directory(args.deploy, args.target)

    elif args.upload:
        result = api.upload_file(args.upload[0], args.upload[1])
        print(json.dumps(result, indent=2))

    elif args.delete:
        result = api.delete_file(args.delete)
        print(json.dumps(result, indent=2))

    elif args.read:
        result = api.read_file(args.read)
        if "content" in result:
            print(result["content"])
        else:
            print(json.dumps(result, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
