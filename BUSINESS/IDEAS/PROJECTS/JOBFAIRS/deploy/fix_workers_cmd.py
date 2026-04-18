"""Add /workers command to bot_commands_infra.py"""
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_infra.py"
lines = open(f).readlines()

# Find INFRA_COMMANDS dict
insert_at = None
for i, line in enumerate(lines):
    if line.startswith("# Command registry"):
        insert_at = i
        break

func = [
    'async def cmd_workers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Recent worker applications."""\n',
    '    r1 = _run(\'sqlite3 /opt/ACTIVE/OPENDATA/DATA/master_applicants.db "SELECT COUNT(*) FROM applicants"\', timeout=5)\n',
    '    r2 = _run(\'sqlite3 /opt/ACTIVE/OPENDATA/DATA/master_applicants.db "SELECT email, source, created_at FROM applicants ORDER BY created_at DESC LIMIT 10"\', timeout=5)\n',
    '    r3 = _run(\'psql -d interjob_master -t -c "SELECT sender_email, inbox, LEFT(subject,30) FROM campaign_responses WHERE category=\'\'WORKER_APPLICATION\'\' ORDER BY created_at DESC LIMIT 10"\', timeout=5)\n',
    '    msg = "WORKERS:\\nTotal: " + r1.strip() + "\\n\\nLatest DB:\\n" + (r2.strip() or "None") + "\\n\\nNew apps:\\n" + (r3.strip() or "None")\n',
    '    await update.message.reply_text(_reply(msg), parse_mode="HTML")\n',
    '\n',
    '\n',
]

if insert_at:
    lines = lines[:insert_at] + func + lines[insert_at:]

content = "".join(lines)
if '"workers"' not in content:
    content = content.replace(
        '"responses": cmd_responses,',
        '"responses": cmd_responses, "workers": cmd_workers,')

open(f, "w").write(content)
print("Added /workers command")
