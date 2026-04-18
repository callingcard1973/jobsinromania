"""Add /nanoclaw command to bot_commands_system.py"""
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_system.py"
lines = open(f).readlines()

insert_at = None
for i, line in enumerate(lines):
    if "INFRA_COMMANDS" in line or "# Command registry" in line:
        insert_at = i
        break

if not insert_at:
    for i, line in enumerate(lines):
        if "cmd_watchdog" in line and "INFRA" in line:
            insert_at = i
            break

if not insert_at:
    insert_at = len(lines)

new = [
    '\nasync def cmd_nanoclaw(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """NanoClaw operations agent status."""\n',
    '    r = _run("python3 /opt/ACTIVE/INFRA/GOVERNOR/nanoclaw.py --status 2>&1", timeout=15)\n',
    '    await update.message.reply_text(_reply(f"NANOCLAW:\\n{r}"), parse_mode="HTML")\n',
    '\n',
]

lines = lines[:insert_at] + new + lines[insert_at:]
open(f, "w").writelines(lines)

# Add to INFRA_COMMANDS in bot_commands_infra.py
inf = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_infra.py"
content = open(inf).read()
if '"nanoclaw"' not in content:
    content = content.replace(
        '"workers": cmd_workers,',
        '"workers": cmd_workers, "nanoclaw": cmd_nanoclaw,')
    open(inf, "w").write(content)

print(f"Added /nanoclaw. System file: {len(lines)} lines")
