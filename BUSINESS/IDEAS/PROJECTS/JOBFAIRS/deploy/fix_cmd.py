"""Fix cmd_responses in bot_commands_infra.py"""
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_infra.py"
lines = open(f).readlines()
new = []
skip = False
for line in lines:
    if "async def cmd_responses" in line:
        skip = True
        continue
    if skip:
        if line.startswith("# Command") or line.startswith("INFRA_COMMANDS"):
            skip = False
        else:
            continue
    new.append(line)

insert_at = None
for i, line in enumerate(new):
    if line.startswith("# Command registry"):
        insert_at = i
        break

func = [
    'async def cmd_responses(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Campaign responses."""\n',
    '    count = _run(\'psql -d interjob_master -t -c "SELECT category, COUNT(*) FROM campaign_responses GROUP BY category"\', timeout=10)\n',
    '    recent = _run(\'psql -d interjob_master -t -c "SELECT sender_email, category FROM campaign_responses ORDER BY created_at DESC LIMIT 10"\', timeout=10)\n',
    '    msg = "RESPONSES:" + chr(10) + count.strip() + chr(10)*2 + "Last 10:" + chr(10) + (recent.strip() or "None")\n',
    '    await update.message.reply_text(_reply(msg), parse_mode="HTML")\n',
    '\n',
    '\n',
]
if insert_at:
    new = new[:insert_at] + func + new[insert_at:]

open(f, "w").writelines(new)
print("DONE")
