#!/usr/bin/env python3
"""OPS commands: money, workers, email ops, today digest, data, scrapers."""
import subprocess, json, sqlite3
from datetime import datetime, date
from telegram import Update
from telegram.ext import ContextTypes

APPLICANTS_DB = "/opt/ACTIVE/OPENDATA/DATA/master_applicants.db"
CAMPAIGNS_ENV = "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env"
IDEAS_CSV = "/mnt/hdd/MEMORY/IDEAS/INVENTAR/MASTER.csv"

def _run(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return str(e)

def _reply(t): return t[:4000] if len(t) > 4000 else t
def _pg(sql, timeout=10):
    return _run("psql -d interjob_master -t -c " + repr(sql), timeout=timeout)

# ── MONEY / PIPELINE ──────────────────────────────────────────────────────────

async def cmd_revenue(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Total revenue across all pipelines."""
    solo = _pg("SELECT COALESCE(SUM(revenue_eur),0)||' EUR / '||COUNT(*)||' placements' FROM solonet_orders WHERE status='placed'")
    wf   = _pg("SELECT COALESCE(SUM(placement_fee),0)||' EUR / '||COUNT(*)||' placements' FROM workforce_matches WHERE placement_fee>0")
    ebrd = _pg("SELECT COALESCE(SUM(fee),0)||' EUR / '||COUNT(*)||' intros' FROM ebrd_campaign_log WHERE fee>0")
    await update.message.reply_text(
        "REVENUE:\nSolonet: " + solo.strip() +
        "\nWorkforce: " + wf.strip() +
        "\nEBRD: " + ebrd.strip()
    )

async def cmd_pipeline(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Open leads by stage."""
    s = _pg("SELECT status, COUNT(*) FROM solonet_orders GROUP BY status ORDER BY status")
    w = _pg("SELECT CASE WHEN response IS NULL THEN 'no_reply' ELSE 'responded' END,COUNT(*) FROM workforce_matches WHERE sent_at IS NOT NULL GROUP BY 1")
    e = _pg("SELECT CASE WHEN response IS NULL THEN 'no_reply' ELSE 'responded' END,COUNT(*) FROM ebrd_campaign_log WHERE sent_at IS NOT NULL GROUP BY 1")
    await update.message.reply_text(_reply(
        "PIPELINE:\n\nSOLONET:\n" + s.strip() +
        "\n\nWORKFORCE:\n" + w.strip() +
        "\n\nEBRD:\n" + e.strip()
    ))

async def cmd_run_now(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Trigger campaign now. /run_now ebrd|workforce|romania|followup"""
    name = (ctx.args[0] if ctx.args else "").lower()
    env = "export $(grep 'BREVO_CAREWORKERS_API_KEY' " + CAMPAIGNS_ENV + " | head -1) && "
    scripts = {
        "ebrd":      env + "bash /opt/ACTIVE/EBRD_CAMPAIGNS/run_all.sh",
        "workforce": env + "bash /opt/ACTIVE/WORKFORCE/run_workforce.sh",
        "romania":   "bash /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/launch_all.sh",
        "followup":  "cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && /opt/ACTIVE/INFRA/venv/bin/python3 send_followup.py --all-configs configs/ --days 2-3 --limit 50",
    }
    if name not in scripts:
        await update.message.reply_text("Options: " + " | ".join(scripts.keys()))
        return
    await update.message.reply_text("Running " + name + "...")
    _run("nohup bash -c " + repr(scripts[name]) + " > /tmp/run_now_" + name + ".log 2>&1 &", timeout=5)
    await update.message.reply_text("Started. Log: /tmp/run_now_" + name + ".log")

# ── WORKERS ───────────────────────────────────────────────────────────────────

async def cmd_find_worker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Search workers by skill/nationality. /find_worker welding"""
    q = " ".join(ctx.args).lower() if ctx.args else ""
    if not q:
        await update.message.reply_text("Usage: /find_worker <skill or nationality>")
        return
    conn = sqlite3.connect(APPLICANTS_DB)
    rows = conn.execute(
        "SELECT name,nationality,skills,target_jobs FROM applicants WHERE LOWER(skills) LIKE ? OR LOWER(nationality) LIKE ? LIMIT 10",
        (f"%{q}%", f"%{q}%")
    ).fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("No workers for: " + q)
        return
    lines = [f"WORKERS [{q}]:"] + [f"- {r[0]} ({r[1] or '?'}) {r[2] or ''}" for r in rows]
    await update.message.reply_text(_reply("\n".join(lines)))

async def cmd_worker_count(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Worker DB stats."""
    conn = sqlite3.connect(APPLICANTS_DB)
    total = conn.execute("SELECT COUNT(*) FROM applicants").fetchone()[0]
    nats = conn.execute(
        "SELECT nationality,COUNT(*) FROM applicants WHERE nationality IS NOT NULL GROUP BY nationality ORDER BY 2 DESC LIMIT 10"
    ).fetchall()
    conn.close()
    nat_str = "\n".join(f"  {n}: {c}" for n, c in nats)
    await update.message.reply_text(f"WORKERS: {total} total\n\nBy nationality:\n{nat_str}")

async def cmd_add_worker(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Add worker. /add_worker Name | email | skill | nationality"""
    if not ctx.args:
        await update.message.reply_text("Usage: /add_worker Name | email | skill | nat")
        return
    parts = " ".join(ctx.args).split("|")
    name  = parts[0].strip()
    email = parts[1].strip() if len(parts) > 1 else None
    skill = parts[2].strip() if len(parts) > 2 else "general"
    nat   = parts[3].strip() if len(parts) > 3 else None
    conn = sqlite3.connect(APPLICANTS_DB)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO applicants (name,email,nationality,skills,source,created_at) VALUES (?,?,?,?,?,?)",
            (name, email, nat, json.dumps([skill]), "telegram", datetime.now().isoformat())
        )
        conn.commit()
        await update.message.reply_text(f"Added: {name} ({nat}) — {skill}")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    finally:
        conn.close()

# ── EMAIL QUALITY ─────────────────────────────────────────────────────────────

async def cmd_brevo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Brevo credits per key."""
    keys_raw = _run("grep 'BREVO.*API_KEY=' " + CAMPAIGNS_ENV + " | grep -v SMTP | head -20")
    lines = ["BREVO CREDITS:"]
    for line in keys_raw.splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        kname, kval = line.strip().split("=", 1)
        script = (
            "import sib_api_v3_sdk as s; cfg=s.Configuration(); "
            'cfg.api_key["api-key"]="' + kval + '"; '
            "api=s.AccountApi(s.ApiClient(cfg)); acc=api.get_account(); "
            'c=[p.credits for p in acc.plan if p.credits_type=="sendLimit"]; '
            "print(c[0] if c else 0)"
        )
        credits = _run("python3 -c " + repr(script) + " 2>/dev/null", timeout=8)
        short = kname.replace("BREVO_", "").replace("_API_KEY", "")
        lines.append("  " + short + ": " + (credits.strip() or "ERR"))
    await update.message.reply_text(_reply("\n".join(lines)))

async def cmd_test_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Test send. /test_send workforce|ebrd_b email@x.com"""
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /test_send workforce|ebrd_b <email>")
        return
    name, email = ctx.args[0].lower(), ctx.args[1]
    env = "export $(grep 'BREVO_CAREWORKERS_API_KEY' " + CAMPAIGNS_ENV + " | head -1)"
    scripts = {
        "workforce": (env + " && cd /opt/ACTIVE/WORKFORCE && python3 -c "
                      '"from worker_sampler import get_sample_workers; from pitcher import send; '
                      "w=get_sample_workers(3); print(send('Test','" + email + "','Constructii',w))\""),
        "ebrd_b":    (env + " && cd /opt/ACTIVE/EBRD_CAMPAIGNS && python3 -c "
                      '"from campaign_b import get_workers,send_email; w=get_workers(3); '
                      "print(send_email('" + email + "','Test','Energy','RO','Test Project',w))\""),
    }
    if name not in scripts:
        await update.message.reply_text("Options: " + " | ".join(scripts.keys()))
        return
    await update.message.reply_text("Sending to " + email + "...")
    r = _run(scripts[name], timeout=20)
    await update.message.reply_text(_reply(r or "Done"))

async def cmd_dnc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Add to DNC. /dnc email@x.com"""
    if not ctx.args:
        await update.message.reply_text("Usage: /dnc email@x.com")
        return
    email = ctx.args[0].lower().replace("'", "")
    _pg("INSERT INTO master_dnc (email,reason,added_at) VALUES ('" + email + "','telegram',NOW()) ON CONFLICT DO NOTHING")
    await update.message.reply_text("DNC added: " + email)

# ── TODAY DIGEST ──────────────────────────────────────────────────────────────

async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Everything that happened today."""
    t = date.today().isoformat()
    wf   = _pg("SELECT COUNT(*) FROM workforce_matches WHERE sent_at::date='" + t + "'")
    ebrd = _pg("SELECT COUNT(*) FROM ebrd_campaign_log WHERE sent_at::date='" + t + "'")
    app  = _run("sqlite3 " + APPLICANTS_DB + " \"SELECT COUNT(*) FROM applicants WHERE DATE(created_at)='" + t + "'\"", timeout=5)
    solo = _pg("SELECT status,COUNT(*) FROM solonet_orders WHERE created_at::date='" + t + "' GROUP BY status")
    resp = _pg("SELECT COUNT(*) FROM workforce_matches WHERE response IS NOT NULL AND sent_at::date='" + t + "'")
    await update.message.reply_text(_reply(
        f"TODAY {t}:\nWF sent: {wf.strip()}\nEBRD sent: {ebrd.strip()}"
        f"\nWF responses: {resp.strip()}\nNew applicants: {app.strip()}"
        f"\nSolonet:\n{solo.strip() or 'none'}"
    ))

async def cmd_responses_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Today's inbound response log."""
    t = date.today().isoformat()
    r = _run("grep " + t + " /home/tudor/.logs/response_tracker.log 2>/dev/null | grep -E 'INTERESTED|WORKER|REPLY|BOUNCE|ORDER' | tail -20")
    await update.message.reply_text(_reply("RESPONSES TODAY:\n" + (r or "none yet")))

# ── DATA ──────────────────────────────────────────────────────────────────────

async def cmd_enrich(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Look up email across all tables. /enrich email@x.com"""
    if not ctx.args:
        await update.message.reply_text("Usage: /enrich email@x.com")
        return
    email = ctx.args[0].lower().replace("'", "")
    results = []
    checks = [
        ("master_emails", "email"),
        ("master_romania_contacts", "email"),
        ("workforce_matches", "employer_email"),
        ("ebrd_campaign_log", "target_email"),
        ("solonet_orders", "employer_email"),
    ]
    for table, col in checks:
        r = _pg("SELECT * FROM " + table + " WHERE LOWER(" + col + ")='" + email + "' LIMIT 1", timeout=5)
        if r.strip():
            results.append(table + ":\n" + r.strip()[:200])
    await update.message.reply_text(_reply("\n\n".join(results) if results else "Not found: " + email))

async def cmd_idea(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Show idea details. /idea 141"""
    num = ctx.args[0] if ctx.args else ""
    if not num:
        await update.message.reply_text("Usage: /idea <number>")
        return
    r = _run("grep 'IDEA-" + num + ",' " + IDEAS_CSV + " 2>/dev/null || echo 'Not found'")
    await update.message.reply_text(_reply("IDEA-" + num + ":\n" + r))

async def cmd_ideas_live(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """List LIVE ideas."""
    r = _run("grep ',LIVE,' " + IDEAS_CSV + " 2>/dev/null | cut -d, -f1,2,8")
    await update.message.reply_text(_reply("LIVE IDEAS:\n" + (r or "none")))

# ── SCRAPERS ──────────────────────────────────────────────────────────────────

async def cmd_scraper_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Scraper status today."""
    t = date.today().isoformat()
    active = _run("grep -rl '" + t + "' /opt/ACTIVE/SCRAPERS --include='*.log' 2>/dev/null | sed 's|.*/||' | head -15")
    errors = _run("grep -rla 'Traceback\\|ERROR' /opt/ACTIVE/SCRAPERS --include='*.log' 2>/dev/null | sed 's|.*/||' | head -10")
    await update.message.reply_text(_reply(
        "SCRAPERS TODAY:\n" + (active or "none") +
        "\n\nWith errors:\n" + (errors or "none")
    ))

async def cmd_last_scrape(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Last scrape by country. /last_scrape RO|NO|DK|DE|FI|SI"""
    country = (ctx.args[0].upper() if ctx.args else "RO")
    tmap = {
        "RO": "master_romania_contacts", "NO": "no_companies",
        "DK": "dk_companies", "DE": "de_companies",
        "FI": "fi_companies", "SI": "si_companies",
    }
    if country not in tmap:
        await update.message.reply_text("Options: " + " | ".join(tmap.keys()))
        return
    r = _pg("SELECT COUNT(*) total, MAX(created_at)::date last FROM " + tmap[country], timeout=8)
    await update.message.reply_text(country + " (" + tmap[country] + "):\n" + r.strip())
