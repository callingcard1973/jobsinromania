"""Add followup handlers to bot + check Gmail auth issues."""

# 1. Add followup handlers to controller message handler
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_handlers.py"
content = open(f).read()
if "followup_send" not in content:
    old = "    # Original handle_message continues below"
    new = """        if text.startswith("/followup_send_"):
            fid = text.replace("/followup_send_", "")
            import subprocess, psycopg2 as pg2
            # Get followup details
            conn = pg2.connect(host="/var/run/postgresql", dbname="email_sender", user="tudor")
            cur = conn.cursor()
            cur.execute("SELECT email, company, reason FROM followup WHERE id=%s", (fid,))
            row = cur.fetchone()
            if row:
                email_to, company, reason = row
                template = "position_filled" if "ocupat" in (reason or "").lower() else "default"
                # Send the follow-up
                r = subprocess.run(
                    ["python3", "-c", f"from auto_followup import send_followup, mark_sent, load_env, FOLLOWUP_TEMPLATES; env=load_env(); send_followup('{email_to}', 'Follow-up: {company}', FOLLOWUP_TEMPLATES['{template}'], env); mark_sent({fid}); print('Sent')"],
                    capture_output=True, text=True, timeout=30, cwd="/opt/ACTIVE/INFRA/SKILLS")
                await update.message.reply_text(r.stdout.strip() or "Sent")
            else:
                await update.message.reply_text("Follow-up not found")
            cur.close(); conn.close()
            return
        if text.startswith("/followup_skip_"):
            fid = text.replace("/followup_skip_", "")
            import psycopg2 as pg2
            conn = pg2.connect(host="/var/run/postgresql", dbname="email_sender", user="tudor")
            cur = conn.cursor()
            cur.execute("UPDATE followup SET status='skipped' WHERE id=%s", (fid,))
            conn.commit()
            cur.close(); conn.close()
            await update.message.reply_text("Skipped")
            return
    # Original handle_message continues below"""
    content = content.replace(old, new)
    open(f, "w").write(content)
    print("Added followup handlers")

# 2. Check Gmail passwords
import subprocess
env = {}
with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
    for l in f:
        if "=" in l and not l.startswith("#"):
            k, v = l.strip().split("=", 1)
            env[k] = v.strip().strip('"')

gmail_accounts = {
    "manpowersearchromania@gmail.com": "GMAIL_MANPOWER_APP_PASSWORD",
    "lucian.bpandp@gmail.com": "GMAIL_LUCIAN_APP_PASSWORD",
}
for acct, key in gmail_accounts.items():
    pwd = env.get(key, "")
    if pwd:
        print(f"{acct}: password EXISTS ({key}={pwd[:4]}...)")
    else:
        print(f"{acct}: NO PASSWORD for {key}")
