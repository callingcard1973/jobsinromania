#!/usr/bin/env python3
"""
A2 Hosting MySQL Operations
Provides database management via SSH tunnel or direct connection.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

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

def run_mysql_ssh(config, command, database=None):
    """Run MySQL command via SSH"""
    host = config.get('A2_HOST')
    user = config.get('A2_SSH_USER')
    port = config.get('A2_SSH_PORT', '7822')
    key = config.get('A2_SSH_KEY', '~/.ssh/id_rsa')

    mysql_user = config.get('A2_MYSQL_USER', user)
    mysql_pass = config.get('A2_MYSQL_PASS')

    if not mysql_pass:
        print("Error: A2_MYSQL_PASS required in config")
        sys.exit(1)

    # Build MySQL command
    mysql_cmd = f"mysql -u{mysql_user} -p'{mysql_pass}'"
    if database:
        mysql_cmd += f" {database}"

    if command:
        mysql_cmd += f" -e \"{command}\""

    # Build SSH command
    key = os.path.expanduser(key)
    ssh_opts = f"-p {port}"
    if os.path.exists(key):
        ssh_opts += f" -i {key}"

    full_cmd = f"ssh {ssh_opts} {user}@{host} '{mysql_cmd}'"

    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)

    return result.stdout

def cmd_list(config, args):
    """List all databases"""
    output = run_mysql_ssh(config, "SHOW DATABASES;")
    print("Databases:")
    for line in output.strip().split('\n')[1:]:  # Skip header
        if line and not line.startswith('+'):
            print(f"  - {line.strip('| ')}")

def cmd_tables(config, args):
    """List tables in database"""
    if not args.database:
        print("Error: Database name required")
        sys.exit(1)

    output = run_mysql_ssh(config, "SHOW TABLES;", args.database)
    print(f"Tables in {args.database}:")
    for line in output.strip().split('\n')[1:]:
        if line and not line.startswith('+'):
            print(f"  - {line.strip('| ')}")

def cmd_query(config, args):
    """Run SQL query"""
    if not args.database:
        print("Error: Database name required")
        sys.exit(1)
    if not args.extra:
        print("Error: SQL query required")
        sys.exit(1)

    query = ' '.join(args.extra)
    output = run_mysql_ssh(config, query, args.database)
    print(output)

def cmd_export(config, args):
    """Export database to SQL"""
    if not args.database:
        print("Error: Database name required")
        sys.exit(1)

    host = config.get('A2_HOST')
    user = config.get('A2_SSH_USER')
    port = config.get('A2_SSH_PORT', '7822')
    key = config.get('A2_SSH_KEY', '~/.ssh/id_rsa')

    mysql_user = config.get('A2_MYSQL_USER', user)
    mysql_pass = config.get('A2_MYSQL_PASS')

    # Build mysqldump command
    dump_cmd = f"mysqldump -u{mysql_user} -p'{mysql_pass}' {args.database}"

    key = os.path.expanduser(key)
    ssh_opts = f"-p {port}"
    if os.path.exists(key):
        ssh_opts += f" -i {key}"

    full_cmd = f"ssh {ssh_opts} {user}@{host} '{dump_cmd}'"

    # Stream output to stdout
    subprocess.run(full_cmd, shell=True)

def cmd_import(config, args):
    """Import SQL file to database"""
    if not args.database:
        print("Error: Database name required")
        sys.exit(1)

    print("Reading SQL from stdin...")
    print("Usage: cat backup.sql | a2_mysql.py import dbname")

    host = config.get('A2_HOST')
    user = config.get('A2_SSH_USER')
    port = config.get('A2_SSH_PORT', '7822')
    key = config.get('A2_SSH_KEY', '~/.ssh/id_rsa')

    mysql_user = config.get('A2_MYSQL_USER', user)
    mysql_pass = config.get('A2_MYSQL_PASS')

    mysql_cmd = f"mysql -u{mysql_user} -p'{mysql_pass}' {args.database}"

    key = os.path.expanduser(key)
    ssh_opts = f"-p {port}"
    if os.path.exists(key):
        ssh_opts += f" -i {key}"

    full_cmd = f"ssh {ssh_opts} {user}@{host} '{mysql_cmd}'"

    # Read from stdin and pipe to remote MySQL
    subprocess.run(full_cmd, shell=True, stdin=sys.stdin)

def cmd_size(config, args):
    """Show database sizes"""
    query = """
    SELECT
        table_schema AS 'Database',
        ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
    FROM information_schema.tables
    GROUP BY table_schema
    ORDER BY SUM(data_length + index_length) DESC;
    """
    output = run_mysql_ssh(config, query)
    print(output)

def main():
    parser = argparse.ArgumentParser(description='A2 Hosting MySQL Operations')
    parser.add_argument('action', help='Action: list, tables, query, export, import, size')
    parser.add_argument('database', nargs='?', help='Database name')
    parser.add_argument('extra', nargs='*', help='SQL query or additional args')

    args = parser.parse_args()
    config = load_config()

    commands = {
        'list': cmd_list,
        'tables': cmd_tables,
        'query': cmd_query,
        'export': cmd_export,
        'import': cmd_import,
        'size': cmd_size,
    }

    if args.action in commands:
        commands[args.action](config, args)
    else:
        print(f"Unknown action: {args.action}")
        print("Available: list, tables, query, export, import, size")
        sys.exit(1)

if __name__ == '__main__':
    main()
