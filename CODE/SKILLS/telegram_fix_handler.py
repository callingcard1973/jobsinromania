#!/usr/bin/env python3
"""
Telegram Fix Handler - Reply "fix it" to alerts to auto-fix issues

Integrates with alerting.py to add actionable fixes to alerts.

Usage:
    # As standalone bot (adds fix commands to existing bot)
    python3 telegram_fix_handler.py --serve

    # Send alert with fix button
    python3 telegram_fix_handler.py --alert "Disk full on /opt" --fix-cmd "cleanup"

    # List available fixes
    python3 telegram_fix_handler.py --list-fixes
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import subprocess
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Load env
from dotenv import load_dotenv
load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_GROUPS_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '547047851')
ADMIN_USER_ID = 547047851

# Fix commands mapping - what to run for each issue type
FIX_COMMANDS = {
    # Disk issues
    'disk_full': {
        'name': 'Clean disk space',
        'cmd': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/disk_cleanup.py --auto',
        'description': 'Remove old logs, temp files, and caches'
    },
    'disk_warning': {
        'name': 'Check disk usage',
        'cmd': 'du -sh /opt/ACTIVE/INFRA/LOGS/* /tmp/* 2>/dev/null | sort -h | tail -10',
        'description': 'Show largest directories'
    },

    # Service issues
    'service_down': {
        'name': 'Restart services',
        'cmd': 'sudo systemctl restart telegram-bot bounce-webhook dashboard 2>/dev/null; echo "Services restarted"',
        'description': 'Restart critical services'
    },
    'nodered_down': {
        'name': 'Restart Node-RED',
        'cmd': 'sudo systemctl restart nodered; sleep 5; curl -s http://localhost:1880 && echo "Node-RED OK"',
        'description': 'Restart Node-RED'
    },
    'dashboard_down': {
        'name': 'Restart dashboard',
        'cmd': 'pkill -f unified_dashboard; /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/unified_dashboard.py --serve 8085 &',
        'description': 'Restart web dashboard'
    },

    # Brevo/Email issues
    'bounce_high': {
        'name': 'Run bounce cleanup',
        'cmd': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/campaign_operations.py --bounce-cleanup',
        'description': 'Clean bounced emails from campaigns'
    },
    'warmup_paused': {
        'name': 'Check warmup status',
        'cmd': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/brevo_warmup.py status',
        'description': 'Show current warmup status'
    },
    'campaign_low': {
        'name': 'Feed campaigns',
        'cmd': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/scraper_to_campaigns.py',
        'description': 'Auto-feed low campaigns from scraper data'
    },

    # Scraper issues
    'scraper_failed': {
        'name': 'Check scraper logs',
        'cmd': 'tail -50 /opt/ACTIVE/INFRA/LOGS/scrapers/*.log 2>/dev/null | grep -E "ERROR|FAIL" | tail -20',
        'description': 'Show recent scraper errors'
    },
    'scraper_stale': {
        'name': 'Run scraper',
        'cmd': 'echo "Use: ssh raspibig python3 /opt/ACTIVE/SCRAPERS/EUROPE/<scraper>.py"',
        'description': 'Instructions to run scraper'
    },

    # Database issues
    'db_connection': {
        'name': 'Check PostgreSQL',
        'cmd': 'pg_isready && PGPASSWORD=scraper123 psql -h localhost -U tudor -d email_sender -c "SELECT 1"',
        'description': 'Test database connection'
    },

    # General
    'autofix': {
        'name': 'Run autofix',
        'cmd': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/autofix.py --fix',
        'description': 'Run all auto-fixes'
    },
    'health_check': {
        'name': 'Health check',
        'cmd': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/health_monitor.py --days 1',
        'description': 'Quick health check'
    },
    'sync_raspibig': {
        'name': 'Sync from raspibig',
        'cmd': 'rsync -avz raspibig:/opt/ACTIVE/OPENDATA/DATA/ /opt/ACTIVE/OPENDATA/DATA/ --dry-run | head -20',
        'description': 'Preview sync from raspibig'
    }
}

# Keywords to fix type mapping
KEYWORD_FIX_MAP = {
    'disk': 'disk_full',
    'space': 'disk_full',
    'storage': 'disk_full',
    'service': 'service_down',
    'nodered': 'nodered_down',
    'node-red': 'nodered_down',
    'dashboard': 'dashboard_down',
    'bounce': 'bounce_high',
    'warmup': 'warmup_paused',
    'paused': 'warmup_paused',
    'campaign': 'campaign_low',
    'contacts': 'campaign_low',
    'scraper': 'scraper_failed',
    'database': 'db_connection',
    'postgres': 'db_connection',
    'db': 'db_connection',
    'health': 'health_check',
    'sync': 'sync_raspibig',
}


def detect_fix_type(message: str) -> Optional[str]:
    """Detect what fix to apply based on alert message."""
    msg_lower = message.lower()

    for keyword, fix_type in KEYWORD_FIX_MAP.items():
        if keyword in msg_lower:
            return fix_type

    return 'autofix'  # Default to general autofix


def run_fix(fix_type: str) -> Dict:
    """Run a fix command and return result."""
    if fix_type not in FIX_COMMANDS:
        return {'success': False, 'output': f'Unknown fix type: {fix_type}'}

    fix = FIX_COMMANDS[fix_type]
    try:
        result = subprocess.run(
            fix['cmd'],
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )

        output = result.stdout or result.stderr or 'No output'
        # Truncate long output
        if len(output) > 1000:
            output = output[:1000] + '\n... (truncated)'

        return {
            'success': result.returncode == 0,
            'output': output,
            'fix_name': fix['name']
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'output': 'Command timed out (120s)'}
    except Exception as e:
        return {'success': False, 'output': f'Error: {e}'}


def send_alert_with_fix(title: str, message: str, fix_type: str = None, level: str = 'warning'):
    """Send Telegram alert with inline fix button."""
    if not fix_type:
        fix_type = detect_fix_type(f"{title} {message}")

    fix_info = FIX_COMMANDS.get(fix_type, FIX_COMMANDS['autofix'])

    emoji = {'info': 'i', 'warning': '⚠️', 'error': '🔴', 'critical': '🚨'}.get(level, '⚠️')

    text = f"{emoji} *{title}*\n\n{message}\n\n"
    text += f"Reply `/fix {fix_type}` to: {fix_info['name']}"

    # Send with inline keyboard
    keyboard = {
        'inline_keyboard': [[
            {'text': f'🔧 {fix_info["name"]}', 'callback_data': f'fix:{fix_type}'}
        ]]
    }

    try:
        resp = requests.post(
            f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage',
            json={
                'chat_id': TELEGRAM_CHAT_ID,
                'text': text,
                'parse_mode': 'Markdown',
                'reply_markup': keyboard
            },
            timeout=10
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Failed to send alert: {e}")
        return False


def handle_fix_command(fix_type: str) -> str:
    """Handle /fix command and return response."""
    result = run_fix(fix_type)

    if result['success']:
        return f"✅ *{result['fix_name']}*\n\n```\n{result['output']}\n```"
    else:
        return f"❌ *Fix failed*\n\n```\n{result['output']}\n```"


def list_fixes() -> str:
    """List all available fixes."""
    lines = ["*Available Fixes*\n"]
    for fix_id, fix in FIX_COMMANDS.items():
        lines.append(f"`/fix {fix_id}` - {fix['name']}")
        lines.append(f"  _{fix['description']}_\n")
    return '\n'.join(lines)


# ===== Async Bot Handler (for integration with existing bot) =====

async def handle_fix_callback(update, context):
    """Handle inline button callback for fix commands."""
    query = update.callback_query
    data = query.data

    if not data.startswith('fix:'):
        return

    # Check if user is admin
    if query.from_user.id != ADMIN_USER_ID:
        await query.answer("Only admin can run fixes", show_alert=True)
        return

    fix_type = data.split(':')[1]
    await query.answer(f"Running {FIX_COMMANDS.get(fix_type, {}).get('name', fix_type)}...")

    # Run fix
    result = run_fix(fix_type)

    # Edit message with result
    emoji = "✅" if result['success'] else "❌"
    output = result['output'][:500] if len(result['output']) > 500 else result['output']

    try:
        await query.edit_message_text(
            f"{emoji} *{result.get('fix_name', 'Fix')}*\n\n"
            f"```\n{output}\n```",
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.message.reply_text(f"Fix result: {output[:1000]}")


async def handle_fix_text_command(update, context):
    """Handle /fix text command."""
    message = update.message
    user = message.from_user

    # Check if admin
    if user.id != ADMIN_USER_ID:
        await message.reply_text("Only admin can run fixes")
        return

    # Get fix type from command args
    args = context.args if context.args else []

    if not args:
        await message.reply_text(list_fixes(), parse_mode='Markdown')
        return

    fix_type = args[0]

    if fix_type not in FIX_COMMANDS:
        await message.reply_text(
            f"Unknown fix: {fix_type}\n\n" + list_fixes(),
            parse_mode='Markdown'
        )
        return

    await message.reply_text(f"Running {FIX_COMMANDS[fix_type]['name']}...")

    result = run_fix(fix_type)
    response = handle_fix_command(fix_type)

    await message.reply_text(response, parse_mode='Markdown')


async def handle_fix_it_reply(update, context):
    """Handle 'fix it' replies to alerts."""
    message = update.message

    if not message.reply_to_message:
        return

    # Check if replying with "fix it" or "fix"
    text = (message.text or '').lower().strip()
    if text not in ['fix it', 'fix', 'fixit', 'fix this']:
        return

    # Check admin
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply_text("Only admin can run fixes")
        return

    # Get original alert message
    original = message.reply_to_message.text or ''

    # Detect fix type from original message
    fix_type = detect_fix_type(original)

    await message.reply_text(f"Detected issue: {fix_type}\nRunning fix...")

    result = run_fix(fix_type)
    response = handle_fix_command(fix_type)

    await message.reply_text(response, parse_mode='Markdown')


# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Telegram Fix Handler')
    parser.add_argument('--serve', action='store_true', help='Run as bot (integrate with existing)')
    parser.add_argument('--alert', type=str, help='Send alert with fix button')
    parser.add_argument('--fix-cmd', type=str, help='Fix type for alert')
    parser.add_argument('--fix', type=str, help='Run a fix directly')
    parser.add_argument('--list-fixes', action='store_true', help='List available fixes')
    parser.add_argument('--test', action='store_true', help='Send test alert')
    args = parser.parse_args()

    if args.list_fixes:
        for fix_id, fix in FIX_COMMANDS.items():
            print(f"{fix_id:20} - {fix['name']}")
            print(f"                       {fix['description']}")
        return

    if args.fix:
        result = run_fix(args.fix)
        print(f"{'OK' if result['success'] else 'FAIL'}: {result.get('fix_name', args.fix)}")
        print(result['output'])
        return

    if args.alert:
        success = send_alert_with_fix(
            args.alert.split(':')[0] if ':' in args.alert else 'Alert',
            args.alert,
            args.fix_cmd
        )
        print(f"Alert sent: {success}")
        return

    if args.test:
        success = send_alert_with_fix(
            'Test Alert',
            'This is a test alert with fix button.\n\nReply "fix it" or tap button to test.',
            'health_check'
        )
        print(f"Test alert sent: {success}")
        return

    if args.serve:
        print("Starting fix handler bot...")
        print("This should be integrated with existing telegram bot")
        print("Add these handlers to telegram_bot_raspi.py:")
        print("  - CallbackQueryHandler(handle_fix_callback)")
        print("  - CommandHandler('fix', handle_fix_text_command)")
        print("  - MessageHandler(filters.REPLY, handle_fix_it_reply)")
        return

    parser.print_help()


if __name__ == '__main__':
    main()
