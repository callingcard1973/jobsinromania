import re

f = '/opt/ACTIVE/INFRA/SKILLS/bot_commands_infra.py'
content = open(f).read()

# Remove broken cmd_responses if exists
content = re.sub(r'async def cmd_responses\(.*?\n\n', '', content, flags=re.DOTALL)

old = '# Command registry for easy import\nINFRA_COMMANDS = {'
new = '''async def cmd_responses(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Campaign responses from all inboxes."""
    sql1 = "SELECT category, COUNT(*) FROM campaign_responses GROUP BY category ORDER BY count DESC"
    sql2 = "SELECT category, sender_email, LEFT(subject,40) FROM campaign_responses ORDER BY created_at DESC LIMIT 10"
    count = _run('psql -d interjob_master -t -c "' + sql1 + '"', timeout=10)
    recent = _run('psql -d interjob_master -t -c "' + sql2 + '"', timeout=10)
    text = f"RESPONSES:\\n{count.strip()}\\n\\nLast 10:\\n{recent.strip() or 'None yet'}"
    await update.message.reply_text(_reply(text), parse_mode="HTML")


# Command registry for easy import
INFRA_COMMANDS = {'''

content = content.replace(old, new)

# Make sure responses is in the dict
if '"responses"' not in content:
    content = content.replace(
        '"watchdog": cmd_watchdog,',
        '"watchdog": cmd_watchdog, "responses": cmd_responses,')

open(f, 'w').write(content)
print('Fixed')
