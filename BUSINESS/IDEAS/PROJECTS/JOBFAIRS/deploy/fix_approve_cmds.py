"""Add /approve and /skip handlers + /process command to bot."""
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_infra.py"
lines = open(f).readlines()

insert_at = None
for i, line in enumerate(lines):
    if line.startswith("# Command registry"):
        insert_at = i
        break

new = [
    'async def cmd_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Approve email action. Usage: /approve_eXXX"""\n',
    '    text = update.message.text.strip()\n',
    '    eid = text.replace("/approve_", "")\n',
    '    r = _run(f"cd /opt/ACTIVE/INFRA/SKILLS && python3 email_executor.py {eid} approve", timeout=30)\n',
    '    await update.message.reply_text(r or "Done")\n',
    '\n',
    'async def cmd_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Skip email. Usage: /skip_eXXX"""\n',
    '    text = update.message.text.strip()\n',
    '    eid = text.replace("/skip_", "")\n',
    '    r = _run(f"cd /opt/ACTIVE/INFRA/SKILLS && python3 email_executor.py {eid} skip", timeout=10)\n',
    '    await update.message.reply_text(r or "Skipped")\n',
    '\n',
    'async def cmd_process(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Process new emails now with Ollama."""\n',
    '    await update.message.reply_text("Processing emails with Ollama...")\n',
    '    r = _run("python3 /opt/ACTIVE/INFRA/SKILLS/email_processor.py 2>&1", timeout=120)\n',
    '    await update.message.reply_text(_reply(f"PROCESSED:\\n{r or \'No new emails\'}"), parse_mode="HTML")\n',
    '\n',
    'async def cmd_queue(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Show pending email queue."""\n',
    '    import json as j\n',
    '    try:\n',
    '        q = j.loads(open("/opt/ACTIVE/INFRA/GOVERNOR/email_queue.json").read())\n',
    '        pending = [f"{v[\'email\'][\'sender\']}: {v[\'proposal\'].get(\'category\',\'?\')}"\n',
    '                   for v in q.values() if v.get("status") == "pending"]\n',
    '        msg = f"QUEUE ({len(pending)} pending):\\n" + "\\n".join(pending[:15]) if pending else "Queue empty"\n',
    '    except Exception:\n',
    '        msg = "No queue file"\n',
    '    await update.message.reply_text(_reply(msg), parse_mode="HTML")\n',
    '\n',
    '\n',
]

if insert_at:
    lines = lines[:insert_at] + new + lines[insert_at:]

content = "".join(lines)
for cmd in ["process", "queue"]:
    if f'"{cmd}"' not in content:
        content = content.replace(
            '"workers": cmd_workers,',
            f'"workers": cmd_workers, "{cmd}": cmd_{cmd},')

open(f, "w").write(content)
print("Added /approve, /skip, /process, /queue commands")
