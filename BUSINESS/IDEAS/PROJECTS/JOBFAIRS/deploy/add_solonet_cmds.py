"""Add /solonet commands to bot + wire into controller message handler."""

# 1. Add /solonet command to bot_commands_campaign.py
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_campaign.py"
lines = open(f).readlines()
if "cmd_solonet" not in "".join(lines):
    lines.append('\nasync def cmd_solonet(update, ctx):\n')
    lines.append('    """Solonet order status."""\n')
    lines.append('    r = _run("python3 /opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py status", timeout=15)\n')
    lines.append('    await update.message.reply_text(_reply(r), parse_mode="HTML")\n')
    lines.append('\n')
    open(f, "w").writelines(lines)
    print("Added /solonet to campaign commands")

# 2. Add to INFRA_COMMANDS registry
f2 = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_infra.py"
content = open(f2).read()
if '"solonet"' not in content:
    content = content.replace(
        '"workers": cmd_workers,',
        '"workers": cmd_workers, "solonet": cmd_solonet,')
    open(f2, "w").write(content)
    print("Added solonet to registry")

# 3. Wire /send_solonet_ and /skip_solonet_ into controller message handler
f3 = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_handlers.py"
content = open(f3).read()
if "send_solonet" not in content:
    old = "    # Original handle_message continues below"
    new = """        if text.startswith("/send_solonet_"):
            oid = text.replace("/send_solonet_", "")
            import subprocess
            r = subprocess.run(["python3", "/opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py", "send", oid],
                capture_output=True, text=True, timeout=30, cwd="/opt/ACTIVE/INFRA/SKILLS")
            await update.message.reply_text(r.stdout.strip() or "Sent")
            return
        if text.startswith("/skip_solonet_"):
            oid = text.replace("/skip_solonet_", "")
            import subprocess
            r = subprocess.run(["python3", "/opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py", "skip", oid],
                capture_output=True, text=True, timeout=10, cwd="/opt/ACTIVE/INFRA/SKILLS")
            await update.message.reply_text(r.stdout.strip() or "Skipped")
            return
        if text.startswith("/solonet_placed_"):
            parts = text.replace("/solonet_placed_", "").split()
            oid = parts[0]
            workers = parts[1] if len(parts) > 1 else "0"
            revenue = parts[2] if len(parts) > 2 else "0"
            import subprocess
            r = subprocess.run(["python3", "/opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py", "placed", oid, workers, revenue],
                capture_output=True, text=True, timeout=10, cwd="/opt/ACTIVE/INFRA/SKILLS")
            await update.message.reply_text(r.stdout.strip() or "Marked")
            return
        if text.startswith("/solonet_responded_"):
            oid = text.replace("/solonet_responded_", "")
            import subprocess, psycopg2
            conn = psycopg2.connect(host="/var/run/postgresql", dbname="interjob_master", user="tudor", password="scraper123")
            cur = conn.cursor()
            cur.execute("UPDATE solonet_orders SET status='responded', responded_at=NOW() WHERE id=%s", (oid,))
            conn.commit()
            cur.close()
            conn.close()
            await update.message.reply_text(f"Order #{oid} marked as responded")
            return
    # Original handle_message continues below"""
    content = content.replace(old, new)
    open(f3, "w").write(content)
    print("Added solonet handlers to message handler")

print("Done")
