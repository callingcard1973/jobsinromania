# Todo

## Clone Telegram bot for missing sectors
careworkers, electricjobs, farmworkers, horecaworkers, warehouseworkers, mechanicjobs all lack bots.
Pattern is in `meatworkers_bot/` — copy, swap CONFIG block, register BotFather token.

## Audit FLIGHTS agents vs pipeline.md steps
`.claude/pipeline.md` documents steps 1-46. Cross-check which FLIGHTS agents cover which steps.
Steps 22-36 marked pending — verify if any FLIGHTS scripts actually implement them.

## Wire event_publisher into Node-RED schedule
`job_publisher.py` posts to Telegram channels but scheduling unclear.
Check Node-RED for existing flows; if missing, add daily 09:00 trigger.

## Document all active Node-RED flows
`http://localhost:1880` runs all scheduling. No flow documentation exists.
Export flows JSON and document what each flow does, its schedule, and which script it calls.

## Consolidate EU_FUNDING scrapers into scrapers tentacle
`/opt/ACTIVE/EU_FUNDING/` has PNRR + beneficiari scrapers.
Determine which are active, add to scrapers inventory, wire results into campaigns pipeline.

## Health-check all 3 Telegram bots
Confirm meatworkers_bot, buildjobs_bot, factoryjobs_bot are running and receiving submissions.
Check `cv_submissions/` dirs for recent files; test `/start` command on each.
