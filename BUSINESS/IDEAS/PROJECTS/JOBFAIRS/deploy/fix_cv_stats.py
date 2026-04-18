"""Fix cv_stats command quote issue."""
f = "/opt/ACTIVE/INFRA/SKILLS/bot_commands_campaign.py"
lines = open(f).readlines()

# Remove broken cv_stats function
result = []
skip = False
for line in lines:
    if "async def cmd_cv_stats" in line:
        skip = True
        continue
    if skip and line.startswith("async def "):
        skip = False
    if skip:
        continue
    result.append(line)

# Add clean version
result.append('\nasync def cmd_cv_stats(update, ctx):\n')
result.append('    """CV vault statistics."""\n')
result.append('    r1 = _run(\'psql -d interjob_master -t -c "SELECT COUNT(*) FROM cv_vault"\', timeout=5)\n')
result.append('    skills_sql = "SELECT unnest(string_to_array(skills,chr(124))), COUNT(*) FROM cv_vault GROUP BY 1 ORDER BY 2 DESC LIMIT 8"\n')
result.append('    r2 = _run(\'psql -d interjob_master -t -c "\' + skills_sql + \'"\', timeout=5)\n')
result.append('    nat_sql = "SELECT nationality, COUNT(*) FROM cv_vault WHERE nationality != chr(63)||chr(63) GROUP BY 1 ORDER BY 2 DESC LIMIT 8"\n')
result.append('    r3 = _run(\'psql -d interjob_master -t -c "\' + nat_sql + \'"\', timeout=5)\n')
result.append('    msg = "CV VAULT: " + r1.strip() + " CVs" + chr(10)*2 + "Skills:" + chr(10) + r2.strip() + chr(10)*2 + "Nationality:" + chr(10) + r3.strip()\n')
result.append('    await update.message.reply_text(_reply(msg), parse_mode="HTML")\n')
result.append('\n')

open(f, "w").writelines(result)
print(f"Fixed. {len(result)} lines")
