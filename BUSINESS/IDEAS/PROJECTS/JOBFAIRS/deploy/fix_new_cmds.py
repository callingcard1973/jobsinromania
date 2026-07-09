"""Add new commands to bot_commands_infra.py"""
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_infra.py"
lines = open(f).readlines()

insert_at = None
for i, line in enumerate(lines):
    if line.startswith("# Command registry"):
        insert_at = i
        break

new_cmds = [
    # /health — one-shot full health check
    'async def cmd_health(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Full health check — system + bots + campaigns + disk."""\n',
    '    r = _run("python3 /opt/ACTIVE/INFRA/SKILLS/check_all_blocks.py 2>&1", timeout=60)\n',
    '    # Truncate to 4000 chars for Telegram\n',
    '    await update.message.reply_text(_reply(r[:3900]), parse_mode="HTML")\n',
    '\n',
    # /heal — force restart all bots + clear conflicts
    'async def cmd_heal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Force-heal all Telegram bots — clear sessions + restart."""\n',
    '    results = []\n',
    '    for svc, token in [\n',
    '        ("telegram-unified-controller", "8628341440:AAG-dLC-9A5qVL2B_FA4K_c09fvD7622Mv8"),\n',
    '        ("telegram-moderation", "8212960227:AAF_9d-4e_reI4har-HYvRqFzNNKulXWEQI"),\n',
    '    ]:\n',
    '        _run(f"curl -s https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true")\n',
    '        r = _run(f"sudo systemctl restart {svc} 2>&1")\n',
    '        results.append(f"{svc}: restarted")\n',
    '    await update.message.reply_text(_reply("HEAL:\\n" + "\\n".join(results)), parse_mode="HTML")\n',
    '\n',
    # /send — trigger NORWAY_VIRGIL manual send
    'async def cmd_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Trigger campaign send. Usage: /send <campaign> <limit>"""\n',
    '    campaign = ctx.args[0] if ctx.args else "norway_virgil"\n',
    '    limit = ctx.args[1] if len(ctx.args) > 1 else "10"\n',
    '    r = _run(f"cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED && /opt/ACTIVE/INFRA/venv/bin/python3 send_campaign.py --config configs/{campaign}.json --sector NORWAY_VIRGIL --limit {limit} --dry-run 2>&1", timeout=30)\n',
    '    await update.message.reply_text(_reply(f"SEND {campaign} (dry-run):\\n{r}"), parse_mode="HTML")\n',
    '\n',
    # /scrapers — scraper schedule + status
    'async def cmd_scrapers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Scraper status and schedule."""\n',
    '    r = _run("python3 /opt/ACTIVE/INFRA/GOVERNOR/nanoclaw.py --status 2>&1", timeout=15)\n',
    '    r2 = _run("ls -lt /opt/ACTIVE/INFRA/LOGS/scrapers/ 2>/dev/null | head -10")\n',
    '    await update.message.reply_text(_reply(f"SCRAPERS:\\n{r}\\n\\nLogs:\\n{r2}"), parse_mode="HTML")\n',
    '\n',
    # /blockers — quick Brevo + disk blockers
    'async def cmd_blockers(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """What is blocking sends right now."""\n',
    '    r = _run("python3 /opt/ACTIVE/INFRA/SKILLS/check_all_blocks.py 2>&1 | grep -A1 ACTIONS", timeout=30)\n',
    '    await update.message.reply_text(_reply(f"BLOCKERS:\\n{r or \'None found\'}"), parse_mode="HTML")\n',
    '\n',
    # /leads — hot leads summary
    'async def cmd_leads(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Interested employer leads."""\n',
    '    r = _run(\'psql -d interjob_master -t -c "SELECT sender_email, campaign, LEFT(subject,35) FROM campaign_responses WHERE category=\'\'INTERESTED\'\' ORDER BY created_at DESC LIMIT 15"\', timeout=10)\n',
    '    count = _run(\'psql -d interjob_master -t -c "SELECT COUNT(*) FROM campaign_responses WHERE category=\'\'INTERESTED\'\'"\', timeout=5)\n',
    '    await update.message.reply_text(_reply(f"LEADS ({count.strip()} total):\\n{r.strip() or \'None\'}"), parse_mode="HTML")\n',
    '\n',
    # /stop_campaign — disable a campaign
    'async def cmd_stop_campaign(update: Update, ctx: ContextTypes.DEFAULT_TYPE):\n',
    '    """Stop a campaign. Usage: /stop_campaign <name>"""\n',
    '    if not ctx.args:\n',
    '        await update.message.reply_text("Usage: /stop_campaign <config_name>")\n',
    '        return\n',
    '    name = ctx.args[0]\n',
    '    r = _run(f\'python3 -c "import json; f=open(\\\"/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/{name}.json\\\"); c=json.load(f); f.close(); c[\\\"enabled\\\"]=False; json.dump(c, open(\\\"/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/{name}.json\\\",\\\"w\\\"), indent=2); print(\\\"STOPPED:\\\", c[\\\"campaign_name\\\"])"\', timeout=5)\n',
    '    await update.message.reply_text(r or "Failed")\n',
    '\n',
    '\n',
]

if insert_at:
    lines = lines[:insert_at] + new_cmds + lines[insert_at:]

content = "".join(lines)

# Add to INFRA_COMMANDS dict
for cmd in ["health", "heal", "send", "scrapers", "blockers", "leads", "stop_campaign"]:
    if f'"{cmd}"' not in content:
        content = content.replace(
            '"workers": cmd_workers,',
            f'"workers": cmd_workers, "{cmd}": cmd_{cmd},')

open(f, "w").write(content)
print("Added 7 new commands")
