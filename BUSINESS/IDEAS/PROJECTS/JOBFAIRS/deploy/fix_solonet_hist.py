"""Fix solonet_history command."""
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_campaign.py"
lines = open(f).readlines()

# Remove broken cmd_solonet_history
result = []
skip = False
for line in lines:
    if "async def cmd_solonet_history" in line:
        skip = True
        continue
    if skip and (line.startswith("async def ") or line.startswith("# ")):
        skip = False
    if skip:
        continue
    result.append(line)

# Add clean version
result.append('\n')
result.append('async def cmd_solonet_history(update, ctx):\n')
result.append('    """Solonet conversation history."""\n')
result.append('    oid = ctx.args[0] if ctx.args else ""\n')
result.append('    if oid:\n')
result.append('        sql = "SELECT direction, sender_email, LEFT(subject,30), created_at::date FROM solonet_conversations WHERE order_id=" + oid + " ORDER BY created_at"\n')
result.append('    else:\n')
result.append('        sql = "SELECT direction, sender_email, LEFT(subject,30), created_at::date FROM solonet_conversations ORDER BY created_at DESC LIMIT 15"\n')
result.append('    r = _run(\'psql -d interjob_master -t -c "\' + sql + \'"\', timeout=10)\n')
result.append('    msg = "SOLONET HISTORY:" + chr(10) + (r.strip() or "No conversations yet")\n')
result.append('    await update.message.reply_text(_reply(msg), parse_mode="HTML")\n')
result.append('\n')

open(f, "w").writelines(result)
print(f"Fixed. {len(result)} lines")
