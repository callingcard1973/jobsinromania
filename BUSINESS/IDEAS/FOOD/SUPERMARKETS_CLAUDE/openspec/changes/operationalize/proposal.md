# Change: operationalize

## Intent

Deploy the food distribution contact system for daily use: run enrichment, launch email campaigns, schedule SEAP alerts, and set up the producer directory.

## Current State

- 32,545 contacts in food_distribution DB (20,795 with email, 64%)
- 11,750 contacts still missing email
- 5 campaign tier CSVs ready (1,820 rows)
- 1,824 insolvent contacts to exclude
- SEAP alert dispatcher built but not scheduled
- Email templates + dashboard ready, no campaign orchestrator wired

## Proposed Actions (3 tracks)

### Track A: Enrichment (fill email gaps)

1. **Run `enrich_from_db.py`** on raspibig to pull emails from interjob_master
   ```bash
   ssh tudor@192.168.100.21
   cd /path/to/CODE
   python3 enrich_from_db.py --dry-run   # preview
   python3 enrich_from_db.py             # execute
   ```
2. **Run web enrichment** for top-value contacts without email (distributors, chains)
   ```bash
   python3 web_email_finder.py --category distributor --limit 200
   ```
3. **Re-export campaign segments** after enrichment
   ```bash
   python3 segment_and_analyze.py
   ```

### Track B: Email Campaigns via Brevo

**Week 1 -- Tier 0 (58 warm SEAP winners):**
- Manual test: send 10, wait 7 days, measure response
- If >10% response: send remaining 48
- Template: `campaign_templates.py::tier_0_template()`

**Week 2 -- Tier 1 (469 supermarket chains):**
- Register on 5 chain supplier portals (Kaufland, Lidl, Carrefour, Profi, Penny)
- Send emails in 2 batches (200 + 269)
- Template: `campaign_templates.py::tier_1_template()`

**Week 2-4 -- Tier 2 (1,147 distributors with email):**
- Regional rollout: Bucharest first, then Transylvania, then Moldavia
- Track meetings and LOIs
- Template: `campaign_templates.py::tier_2_template()`

**Week 3 -- Tier 3 (HoReCa, validate first):**
- Call 10 random, validate emails
- Send 100 Bucharest batch, monitor bounces
- Expand only if response >0.5%

**Integration with existing infrastructure:**
- Use `/opt/ACTIVE/INFRA/SKILLS/email_sending_skill.py` (Yahoo/Gmail split, Brevo)
- Use `/opt/ACTIVE/INFRA/SKILLS/global_send_tracker.py` (cross-campaign dedup)
- Wire into campaign orchestrator like CONSTRUCTORI/LICHIDATORI campaigns

### Track C: Automated Monitoring

1. **Schedule SEAP alert dispatcher** as cron on raspibig:
   ```bash
   # Every Monday 09:00
   0 9 * * 1 cd /opt/ACTIVE/supermarkets && python3 seap_alert_dispatcher.py
   ```
2. **Weekly enrichment stats** via existing email_weekly_report infrastructure
3. **Exclude insolvent contacts** -- add 1,824 insolvent emails to DNC list in email_sender DB

## Priority Order

1. Run enrichment (Track A) -- increases contactable pool before campaigns
2. Tier 0 test campaign (Track B, Week 1) -- highest conversion, validates pipeline
3. Schedule SEAP alerts (Track C.1) -- passive, runs automatically
4. Scale campaigns (Track B, Week 2+) -- after Tier 0 validates

## Rollback

Email campaigns: pause via Brevo dashboard. Cron: remove crontab entry. No schema changes.
