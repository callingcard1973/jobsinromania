# Raspibig Campaign Configurator

Text-based interactive tool for managing email campaigns on raspibig (192.168.100.21).

## Usage

```bash
ssh tudor@192.168.100.21
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_TUDOR_MIGRATED_TO_RASPI/
python3 campaign_configurator.py
```

## Features

**Menu Options:**
1. List campaigns — show all campaign configs + CSV files
2. List senders — show all Brevo/Gmail accounts (enabled/disabled, limits)
3. Add campaign — create new campaign with name, CSV, template
4. Edit campaign — modify enabled status, CSV path, template
5. Delete campaign — remove campaign (with confirmation)
6. Exit

## Data Storage

- **Campaigns** → `configs/campaigns.json` (campaign definitions)
- **Senders** → `configs/senders.json` (Brevo/Gmail accounts + sector routing)
- **Contacts** → `contacts/*.csv` (contact lists per campaign)
- **Configs** → `configs/*.json` (loaded by orchestrator)

## Workflow

### Add New Campaign

```
1. Run campaign_configurator.py
2. Choose "3. Add campaign"
3. Enter:
   - Campaign name (e.g., TUDOR_EBRD)
   - Description
   - CSV file path (e.g., /opt/ACTIVE/EMAIL/CAMPAIGNS/EBRD/contacts.csv)
   - Default template path (e.g., ebrd/template1.txt)
4. Config saved to configs/campaigns.json
```

### Edit Existing Campaign

```
1. Run campaign_configurator.py
2. Choose "4. Edit campaign"
3. Select campaign by number or name
4. Modify enabled status, CSV path, or template
5. Config updated automatically
```

### Run Campaign via Orchestrator

Once campaign is configured:

```bash
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_TUDOR_MIGRATED_TO_RASPI/
python3 orchestrator.py --status                    # list all campaigns
python3 orchestrator.py --config TUDOR_EBRD --once  # run single campaign
python3 orchestrator.py --interval 3600             # continuous loop (hourly)
```

## Integration

- **Orchestrator** reads from `configs/*.json` automatically
- **Senders** routes emails via Brevo/Gmail based on `senders.json`
- **Templates** resolved from template paths in campaign config
- **CSV contacts** loaded at runtime by `sender.py`

## Schema

### Campaign Config

```json
{
  "campaign_name": "TUDOR_ANOFM",
  "enabled": true,
  "description": "ANOFM employers",
  "contacts": {
    "csv_file": "/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_TUDOR_MIGRATED_TO_RASPI/contacts/anofm_contacts.csv"
  },
  "templates": {
    "default": "anofm/tudor_template1.txt",
    "rotation": ["anofm/tudor_template1.txt", "anofm/tudor_template2.txt"]
  },
  "timing": {
    "delay_min": 180,
    "delay_max": 240,
    "batch_size": 10,
    "batch_pause": 300
  },
  "gov_domains": ["gov.ro", "edu.ro", "mil.ro"]
}
```

### Sender Config

```json
{
  "brevo": {
    "buildjobs": {
      "env_key": "BREVO_BUILDJOBS_API_KEY",
      "email": "office@buildjobs.eu",
      "daily_limit": 290,
      "enabled": true
    }
  },
  "gmail": {
    "manpowerdristor": {
      "env_key": "GMAIL_MANPOWERDRISTOR_APP_PASSWORD",
      "email": "manpowerdristor@gmail.com",
      "daily_limit": 100,
      "enabled": true
    }
  },
  "campaigns": {
    "TUDOR_ANOFM": {
      "primary": "brevo:interjob",
      "fallback": ["brevo:mivromania"],
      "sectors": {
        "constructii": "brevo:buildjobs",
        "productie": "brevo:factoryjobs"
      }
    }
  }
}
```

## Monitoring

View campaign status:

```bash
python3 orchestrator.py --status

# Monitor logs
tail -f logs/*.log

# Check CSV contact count
wc -l contacts/*.csv
```

## Troubleshooting

**Campaign not running:**
- Check enabled: true in campaigns.json
- Verify CSV file exists: `ls contacts/your_campaign.csv`
- Check template path in config

**Emails not sending:**
- Check Brevo API key in /opt/EMAIL/.env
- Verify sender email is enabled in senders.json
- Check Brevo bounce rate < 30%

**CSV contacts not found:**
- Verify full path in campaign config
- Ensure CSV has email, company_name, city, sector columns
- Check file permissions: `ls -la contacts/`
