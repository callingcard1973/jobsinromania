"""Add /approve_ and /skip_ message handler to unified controller."""
f = "/opt/ACTIVE/INFRA/SKILLS/telegram_unified_controller.py"
content = open(f).read()

# Find the handle_message function and add approve/skip routing before LLM
old = 'async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:'
new = '''async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Handle /approve_eXXX and /skip_eXXX commands (dynamic IDs)
    if update.message and update.message.text:
        text = update.message.text.strip()
        if text.startswith("/approve_e"):
            eid = text.replace("/approve_", "")
            import subprocess
            r = subprocess.run(["python3", "/opt/ACTIVE/INFRA/SKILLS/email_executor.py", eid, "approve"],
                capture_output=True, text=True, timeout=30, cwd="/opt/ACTIVE/INFRA/SKILLS")
            await update.message.reply_text(r.stdout.strip() or "Done")
            return
        if text.startswith("/skip_e"):
            eid = text.replace("/skip_", "")
            import subprocess
            r = subprocess.run(["python3", "/opt/ACTIVE/INFRA/SKILLS/email_executor.py", eid, "skip"],
                capture_output=True, text=True, timeout=10, cwd="/opt/ACTIVE/INFRA/SKILLS")
            await update.message.reply_text(r.stdout.strip() or "Skipped")
            return
    # Original handle_message continues below'''

# Only add if not already there
if '/approve_e' not in content:
    content = content.replace(old, new)
    open(f, 'w').write(content)
    print("Added /approve_ and /skip_ to message handler")
else:
    print("Already has /approve_ handler")
