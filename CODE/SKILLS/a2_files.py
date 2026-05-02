#!/usr/bin/env python3
"""
A2 Hosting File Manager
Manage files on A2 Hosting via SSH/SFTP.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

def load_config():
    """Load configuration from ~/.a2hosting.env"""
    config = {}
    config_file = Path.home() / ".a2hosting.env"

    if not config_file.exists():
        print(f"Error: Configuration file not found: {config_file}")
        sys.exit(1)

    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip().strip('"\'')

    return config

def ssh_cmd(config, command):
    """Run SSH command and return output"""
    host = config.get('A2_HOST')
    user = config.get('A2_SSH_USER')
    port = config.get('A2_SSH_PORT', '7822')
    key = config.get('A2_SSH_KEY', '~/.ssh/id_rsa')

    key = os.path.expanduser(key)
    ssh_opts = f"-p {port}"
    if os.path.exists(key):
        ssh_opts += f" -i {key}"

    full_cmd = f"ssh {ssh_opts} {user}@{host} '{command}'"

    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def scp_download(config, remote_path, local_path):
    """Download file via SCP"""
    host = config.get('A2_HOST')
    user = config.get('A2_SSH_USER')
    port = config.get('A2_SSH_PORT', '7822')
    key = config.get('A2_SSH_KEY', '~/.ssh/id_rsa')

    key = os.path.expanduser(key)
    scp_opts = f"-P {port}"
    if os.path.exists(key):
        scp_opts += f" -i {key}"

    # Handle home directory paths
    if not remote_path.startswith('/'):
        remote_path = f"~/{remote_path}"

    cmd = f"scp {scp_opts} {user}@{host}:{remote_path} {local_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stderr

def scp_upload(config, local_path, remote_path):
    """Upload file via SCP"""
    host = config.get('A2_HOST')
    user = config.get('A2_SSH_USER')
    port = config.get('A2_SSH_PORT', '7822')
    key = config.get('A2_SSH_KEY', '~/.ssh/id_rsa')

    key = os.path.expanduser(key)
    scp_opts = f"-P {port}"
    if os.path.exists(key):
        scp_opts += f" -i {key}"

    if not remote_path.startswith('/'):
        remote_path = f"~/{remote_path}"

    cmd = f"scp {scp_opts} {local_path} {user}@{host}:{remote_path}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stderr

def cmd_ls(config, args):
    """List directory contents"""
    path = args.path or '~'
    stdout, stderr, code = ssh_cmd(config, f"ls -lah {path}")

    if code != 0:
        print(f"Error: {stderr}")
        sys.exit(1)

    print(f"Contents of {path}:")
    print(stdout)

def cmd_download(config, args):
    """Download file from server"""
    if not args.path:
        print("Error: Remote path required")
        sys.exit(1)

    local = args.extra[0] if args.extra else './'

    print(f"Downloading {args.path} to {local}...")
    success, error = scp_download(config, args.path, local)

    if success:
        print("Download complete!")
    else:
        print(f"Error: {error}")
        sys.exit(1)

def cmd_upload(config, args):
    """Upload file to server"""
    if not args.path:
        print("Error: Local path required")
        sys.exit(1)

    if not args.extra:
        print("Error: Remote path required")
        sys.exit(1)

    remote = args.extra[0]

    if not os.path.exists(args.path):
        print(f"Error: Local file not found: {args.path}")
        sys.exit(1)

    print(f"Uploading {args.path} to {remote}...")
    success, error = scp_upload(config, args.path, remote)

    if success:
        print("Upload complete!")
    else:
        print(f"Error: {error}")
        sys.exit(1)

def cmd_backup(config, args):
    """Create backup of directory"""
    path = args.path or 'public_html'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{path.replace('/', '_')}_{timestamp}.tar.gz"

    print(f"Creating backup of {path}...")

    # Create tarball on remote server
    stdout, stderr, code = ssh_cmd(config, f"tar -czf ~/{backup_name} {path}")

    if code != 0:
        print(f"Error creating backup: {stderr}")
        sys.exit(1)

    # Download backup
    print(f"Downloading {backup_name}...")
    success, error = scp_download(config, f"~/{backup_name}", './')

    if not success:
        print(f"Error downloading: {error}")
        sys.exit(1)

    # Optionally remove remote backup
    ssh_cmd(config, f"rm ~/{backup_name}")

    print(f"Backup saved: ./{backup_name}")

def cmd_delete(config, args):
    """Delete file or directory"""
    if not args.path:
        print("Error: Path required")
        sys.exit(1)

    # Confirm dangerous operation
    confirm = input(f"Delete {args.path}? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Cancelled.")
        return

    stdout, stderr, code = ssh_cmd(config, f"rm -rf {args.path}")

    if code != 0:
        print(f"Error: {stderr}")
        sys.exit(1)

    print(f"Deleted: {args.path}")

def cmd_mkdir(config, args):
    """Create directory"""
    if not args.path:
        print("Error: Path required")
        sys.exit(1)

    stdout, stderr, code = ssh_cmd(config, f"mkdir -p {args.path}")

    if code != 0:
        print(f"Error: {stderr}")
        sys.exit(1)

    print(f"Created directory: {args.path}")

def cmd_cat(config, args):
    """View file contents"""
    if not args.path:
        print("Error: Path required")
        sys.exit(1)

    stdout, stderr, code = ssh_cmd(config, f"cat {args.path}")

    if code != 0:
        print(f"Error: {stderr}")
        sys.exit(1)

    print(stdout)

def cmd_find(config, args):
    """Find files by pattern"""
    path = args.path or '~'
    pattern = args.extra[0] if args.extra else '*'

    stdout, stderr, code = ssh_cmd(config, f"find {path} -name '{pattern}' -type f 2>/dev/null | head -50")

    if stdout:
        print("Found files:")
        print(stdout)
    else:
        print("No files found.")

def cmd_disk(config, args):
    """Show disk usage"""
    path = args.path or '~'
    stdout, stderr, code = ssh_cmd(config, f"du -sh {path}/*")

    if code != 0:
        print(f"Error: {stderr}")
        sys.exit(1)

    print(f"Disk usage in {path}:")
    print(stdout)

def main():
    parser = argparse.ArgumentParser(description='A2 Hosting File Manager')
    parser.add_argument('action', help='Action: ls, download, upload, backup, delete, mkdir, cat, find, disk')
    parser.add_argument('path', nargs='?', help='File or directory path')
    parser.add_argument('extra', nargs='*', help='Additional arguments')

    args = parser.parse_args()
    config = load_config()

    commands = {
        'ls': cmd_ls,
        'download': cmd_download,
        'upload': cmd_upload,
        'backup': cmd_backup,
        'delete': cmd_delete,
        'mkdir': cmd_mkdir,
        'cat': cmd_cat,
        'find': cmd_find,
        'disk': cmd_disk,
    }

    if args.action in commands:
        commands[args.action](config, args)
    else:
        print(f"Unknown action: {args.action}")
        print("Available: ls, download, upload, backup, delete, mkdir, cat, find, disk")
        sys.exit(1)

if __name__ == '__main__':
    main()
