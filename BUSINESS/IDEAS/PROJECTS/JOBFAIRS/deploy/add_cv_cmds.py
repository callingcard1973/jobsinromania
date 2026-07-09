"""Add /match and /cv_stats commands + auto-match in solonet + auto-ingest in worker_router."""

# 1. Bot commands
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_campaign.py"
lines = open(f).readlines()

new_cmds = [
    '\nasync def cmd_match(update, ctx):\n',
    '    """Match candidates by skill. Usage: /match welding 5"""\n',
    '    skill = ctx.args[0] if ctx.args else "general"\n',
    '    count = ctx.args[1] if len(ctx.args) > 1 else "5"\n',
    '    sql = f"SELECT name, nationality, skills FROM cv_vault WHERE skills LIKE \'%{skill}%\' LIMIT {count}"\n',
    '    r = _run(\'psql -d interjob_master -t -c "\' + sql + \'"\', timeout=10)\n',
    '    total_sql = f"SELECT COUNT(*) FROM cv_vault WHERE skills LIKE \'%{skill}%\'"\n',
    '    total = _run(\'psql -d interjob_master -t -c "\' + total_sql + \'"\', timeout=5)\n',
    '    msg = f"MATCH {skill} ({total.strip()} total):" + chr(10) + (r.strip() or "None")\n',
    '    await update.message.reply_text(_reply(msg), parse_mode="HTML")\n',
    '\n',
    'async def cmd_cv_stats(update, ctx):\n',
    '    """CV vault statistics."""\n',
    '    r1 = _run(\'psql -d interjob_master -t -c "SELECT COUNT(*) FROM cv_vault"\', timeout=5)\n',
    '    r2 = _run(\'psql -d interjob_master -t -c "SELECT unnest(string_to_array(skills,\'|\')), COUNT(*) FROM cv_vault GROUP BY 1 ORDER BY 2 DESC LIMIT 8"\', timeout=5)\n',
    '    r3 = _run(\'psql -d interjob_master -t -c "SELECT nationality, COUNT(*) FROM cv_vault WHERE nationality != \'??\' GROUP BY 1 ORDER BY 2 DESC LIMIT 8"\', timeout=5)\n',
    '    msg = f"CV VAULT: {r1.strip()} CVs" + chr(10)*2 + "Skills:" + chr(10) + r2.strip() + chr(10)*2 + "Nationality:" + chr(10) + r3.strip()\n',
    '    await update.message.reply_text(_reply(msg), parse_mode="HTML")\n',
    '\n',
]
lines.extend(new_cmds)
open(f, "w").writelines(lines)

# 2. Add to registry
f2 = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_infra.py"
content = open(f2).read()
for cmd in ["match", "cv_stats"]:
    if f'"{cmd}"' not in content:
        content = content.replace(
            '"solonet": cmd_solonet,',
            f'"solonet": cmd_solonet, "{cmd}": cmd_{cmd},')
open(f2, "w").write(content)

print("Added /match and /cv_stats commands")

# 3. Add auto-match to solonet_pipeline.create_draft()
f3 = "/opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py"
content = open(f3).read()
if "cv_vault" not in content:
    old = '            alert(f"\\U0001f3e2 <b>NEW ORDER DRAFT</b>\\n"'
    new = '''            # Auto-match candidates from CV vault
            cv_count = 0
            try:
                conn2 = db_conn()
                cur2 = conn2.cursor()
                skill_words = positions.lower().split()
                for sw in skill_words:
                    if len(sw) > 3:
                        cur2.execute("SELECT COUNT(*) FROM cv_vault WHERE LOWER(skills) LIKE %s", (f"%{sw}%",))
                        c = cur2.fetchone()[0]
                        if c > cv_count:
                            cv_count = c
                cur2.close()
                conn2.close()
            except Exception:
                pass
            cv_info = f"\\nCV Vault: {cv_count} matching candidates" if cv_count else ""
            alert(f"\\U0001f3e2 <b>NEW ORDER DRAFT</b>\\n"'''
    content = content.replace(old, new)
    # Add cv_info to the alert message
    content = content.replace(
        'f"/send_solonet_{oid}',
        'f"{cv_info}\\n\\n/send_solonet_{oid}')
    open(f3, "w").write(content)
    print("Added auto-match to solonet pipeline")
else:
    print("Solonet already has cv_vault")

print("Done")
