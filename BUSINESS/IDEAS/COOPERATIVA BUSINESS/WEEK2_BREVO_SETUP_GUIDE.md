# WEEK 2: BREVO EMAIL CAMPAIGN SETUP GUIDE
## Gospodarii de Altadata EU Export Campaign

**Week**: 2 (March 15-21, 2026)  
**Task**: Configure email automation + test infrastructure  
**Goal**: Ready for Hypermarket campaign launch on March 22  
**Estimated Duration**: 2-3 hours setup + 2 hours testing

---

## OVERVIEW

This guide walks through setting up the Brevo email infrastructure on raspbig to send:
1. **50 hypermarket procurement emails** (Week 3, March 22)
2. **605 Italy diaspora outreach emails** (Week 5, March 29)
3. **Automated 7-day follow-up sequences**

---

## PREREQUISITES CHECKLIST

- [x] SSH access to raspbig confirmed (tudor@192.168.100.21)
- [x] Brevo API key (on raspbig at `/opt/ACTIVE/EMAIL/brevo.key`)
- [x] Contact lists ready (hypermarket_targets_25emails.csv, italy_diaspora_shops_sample.csv)
- [x] Email templates finalized (EMAIL_CAMPAIGN_TEMPLATES.md)
- [x] Internal stakeholder emails for testing
- [ ] **STILL NEEDED**: Contact approval for bulk sending

---

## STEP 1: SSH INTO RASPBIG & VERIFY BREVO KEY

```bash
ssh tudor@192.168.100.21
# Password: [provided separately]

# Check Brevo integration
cd /opt/ACTIVE/EMAIL/
ls -la

# Should see:
# brevo.key (API credentials)
# brevo_config.json (campaign settings)
# contacts/ (contact lists)
```

**Expected Output:**
```
-rw------- tudor tudor brevo.key
-rw-r--r-- tudor tudor brevo_config.json
drwxr-xr-x tudor tudor contacts/
```

---

## STEP 2: VALIDATE BREVO API CONNECTION

```bash
# Check API key is valid
cat brevo.key
# Should output: xps_[alphanumeric]...

# Test connection
python3 << 'EOF'
import requests
import os

api_key = open('brevo.key').read().strip()
headers = {'api-key': api_key}
r = requests.get('https://api.brevo.com/v3/account', headers=headers)

if r.status_code == 200:
    print("✅ Brevo API connection SUCCESSFUL")
    print(f"Remaining email quota: {r.json().get('email_credits', 'N/A')}")
else:
    print(f"❌ API Error: {r.status_code}")
    print(r.json())
EOF
```

**Expected Result**: "✅ Brevo API connection SUCCESSFUL" + email quota display

---

## STEP 3: IMPORT CONTACT LISTS

### 3a. Hypermarket Targets (50 contacts)

```bash
# Navigate to contact directory
cd /opt/ACTIVE/EMAIL/contacts/

# Upload hypermarket CSV to Brevo
python3 << 'EOF'
import csv
import requests
import json

api_key = open('../brevo.key').read().strip()
headers = {'api-key': api_key, 'Content-Type': 'application/json'}

# Read CSV
contacts = []
with open('/d/MEMORY/IDEAS/COOPERATIVA\ BUSINESS/data_working/hypermarket_targets_25emails.csv') as f:
    for row in csv.DictReader(f):
        contacts.append({
            'email': row['Email'],
            'attributes': {
                'COMPANY': row['Chain'],
                'CONTACT_NAME': row['Contact_Name'],
                'COUNTRY': row['Country'],
                'CATEGORY': 'Hypermarket',
                'CAMPAIGN': 'Q1_2026_EU_Export'
            }
        })

# Create list in Brevo
list_data = {
    'name': 'Hypermarket_Q1_2026',
    'description': '50 hypermarket procurement contacts across EU'
}
r = requests.post(f'https://api.brevo.com/v3/contacts/lists', 
                   headers=headers, 
                   json=list_data)

if r.status_code == 201:
    list_id = r.json()['id']
    print(f"✅ List created: ID {list_id}")
    
    # Add contacts
    for contact in contacts:
        contact['listIds'] = [list_id]
        r = requests.post('https://api.brevo.com/v3/contacts',
                         headers=headers,
                         json=contact)
    
    print(f"✅ Added {len(contacts)} contacts to list {list_id}")
else:
    print(f"❌ Error: {r.status_code} - {r.json()}")
EOF
```

**Expected Output:**
```
✅ List created: ID XXXXX
✅ Added 50 contacts to list XXXXX
```

### 3b. Italy Diaspora Targets (605 contacts)

```bash
# Similar process for diaspora list
python3 << 'EOF'
import csv
import requests
import json

api_key = open('../brevo.key').read().strip()
headers = {'api-key': api_key, 'Content-Type': 'application/json'}

# Read diaspora CSV
contacts = []
with open('/d/MEMORY/IDEAS/COOPERATIVA\ BUSINESS/data_working/italy_diaspora_shops_sample.csv') as f:
    for row in csv.DictReader(f):
        contacts.append({
            'email': row['Email'],
            'attributes': {
                'COMPANY': row['Shop_Name'],
                'CITY': row['City'],
                'COUNTRY': 'Italy',
                'CATEGORY': 'Diaspora_Retail',
                'CAMPAIGN': 'Q1_2026_EU_Export'
            }
        })

# Create list
list_data = {'name': 'Italy_Diaspora_Q1_2026', 'description': '605 Italian retailer contacts'}
r = requests.post('https://api.brevo.com/v3/contacts/lists', 
                   headers=headers, json=list_data)

if r.status_code == 201:
    list_id = r.json()['id']
    
    # Add in batches (Brevo limits to 500/call)
    batch_size = 500
    for i in range(0, len(contacts), batch_size):
        batch = contacts[i:i+batch_size]
        for contact in batch:
            contact['listIds'] = [list_id]
            requests.post('https://api.brevo.com/v3/contacts',
                         headers=headers, json=contact)
    
    print(f"✅ Added {len(contacts)} diaspora contacts to list {list_id}")
else:
    print(f"❌ Error: {r.status_code}")
EOF
```

---

## STEP 4: CREATE EMAIL TEMPLATES IN BREVO

### 4a. Template 1: Hypermarket Procurement (English)

```bash
python3 << 'EOF'
import requests
import json

api_key = open('../brevo.key').read().strip()
headers = {'api-key': api_key, 'Content-Type': 'application/json'}

template = {
    'name': 'Hypermarket_Procurement_EN',
    'subject': 'Premium Romanian Mountain Products | B2B Opportunity',
    'htmlContent': '''
<html>
<body>
<h2>Hello {{CONTACT_NAME}},</h2>
<p>We are <strong>Gospodarii de Altadata</strong>, an official cooperative aggregator of 680+ certified Romanian mountain producers.</p>

<h3>What We Offer:</h3>
<ul>
<li><strong>Cheese & Dairy</strong> – Traditional mountain brânzeturi (EUR 12-15/kg)</li>
<li><strong>Cured Meats</strong> – Smoked ham, sausages (EUR 16-22/kg)</li>
<li><strong>Honey</strong> – Mountain wildflower, raw (EUR 8-12/kg)</li>
<li><strong>Spirits & Jams</strong> – Traditional țuică, preserves</li>
</ul>

<h3>Why Choose Us?</h3>
✓ Single invoice from one aggregator (simplifies procurement)  
✓ Produs Montan certification (EU protected designation = premium positioning)  
✓ HACCP + FSSC certified producers  
✓ Full EU 178/2002 traceability  
✓ 15-30% margin for distributors  

<h3>Your Advantage at {{COMPANY}}:</h3>
<p>These products appeal to health-conscious consumers seeking <em>authentic, traceable European heritage foods</em>. Premium pricing justified by certification.</p>

<p><strong>Next Step:</strong> Let's discuss a trial order (25-50kg minimum).</p>

<p>Best regards,<br>
<strong>Gospodarii de Altadata Cooperativa Agricolă</strong><br>
CUI: 51957925<br>
Email: [contact@gospodarii.ro]<br>
Phone: +40 (XXX) XXX-XXXX
</p>
</body>
</html>
    ''',
    'type': 'classic'
}

r = requests.post('https://api.brevo.com/v3/smtp/templates',
                   headers=headers,
                   json=template)

if r.status_code == 201:
    print(f"✅ Template created: ID {r.json()['id']}")
else:
    print(f"❌ Error: {r.status_code} - {r.json()}")
EOF
```

### 4b. Repeat for Additional Templates (Romanian, Italian, Follow-up)

Create templates for:
- `Hypermarket_Procurement_RO` (Romanian version)
- `Italy_Diaspora_Outreach_IT` (Italian version)
- `FollowUp_7Day` (Auto-responder for non-opens)

---

## STEP 5: CREATE AUTOMATION WORKFLOW

### Workflow: Hypermarket Campaign (3-stage)

```bash
python3 << 'EOF'
import requests
import json
from datetime import datetime, timedelta

api_key = open('../brevo.key').read().strip()
headers = {'api-key': api_key, 'Content-Type': 'application/json'}

# Stage 1: Cold Email (Tuesday-Thursday, 09:00 CET)
cold_email = {
    'name': 'Hypermarket_Stage1_ColdEmail',
    'description': 'Initial procurement outreach to 50 hypermarkets',
    'trigger': {
        'type': 'contact_added_to_list',
        'listId': '[LIST_ID_HYPERMARKET]'  # Replace with actual ID from Step 3a
    },
    'steps': [
        {
            'type': 'email',
            'delay': {'value': 0, 'unit': 'minutes'},
            'template_id': '[TEMPLATE_ID_HM_EN]',  # Replace with actual template ID
            'conditions': [
                {
                    'type': 'email',
                    'condition': 'was_opened',
                    'wait': False
                }
            ]
        }
    ]
}

r = requests.post('https://api.brevo.com/v3/automation',
                   headers=headers,
                   json=cold_email)

if r.status_code == 201:
    workflow_id = r.json()['id']
    print(f"✅ Workflow created: {workflow_id}")
else:
    print(f"❌ Error: {r.status_code}")
EOF
```

---

## STEP 6: SCHEDULE INITIAL TEST SEND

### Test Send to Internal Team (TODAY)

```bash
python3 << 'EOF'
import requests
import json

api_key = open('../brevo.key').read().strip()
headers = {'api-key': api_key, 'Content-Type': 'application/json'}

# Create test send with internal emails only
test_contacts = [
    {'email': 'tudor@[domain]', 'attributes': {'ROLE': 'Founder'}},
    {'email': '[board_member]@[domain]', 'attributes': {'ROLE': 'Board'}}
]

campaign = {
    'name': 'TEST_Hypermarket_HM_EN_20260315',
    'contacts': test_contacts,
    'sendingTime': datetime.utcnow().isoformat(),
    'template_id': '[TEMPLATE_ID_HM_EN]',
    'type': 'classic'
}

r = requests.post('https://api.brevo.com/v3/smtp/email',
                   headers=headers,
                   json=campaign)

print(f"Test send initiated: {r.status_code}")
EOF
```

---

## STEP 7: COLLECT FEEDBACK (24 HOURS)

**Send this message to internal stakeholders:**

> Subject: Test Email Feedback - Hypermarket Campaign
>
> Hi [Board Member],
>
> Please review the attached test email and provide feedback on:
>
> 1. **Subject line** - compelling enough to open?
> 2. **CTA (Call-to-Action)** - clear what next step is?
> 3. **Product info** - enough detail or too much?
> 4. **Design** - professional appearance?
> 5. **Tone** - appropriate for EU buyers?
>
> Please reply within 24 hours so we can incorporate feedback before mass send on March 22.
>
> Specific feedback helpful:
> - "Subject line should emphasize DISCOUNT" 
> - "Add phone number more prominently"
> - "Include minimum order quantity upfront"
>
> Thanks,  
> [Your name]

**Feedback Integration:**
- Collect responses in a spreadsheet
- Update template based on feedback
- Document changes for next rounds

---

## STEP 8: VALIDATE SENDING LIMITS

Check Brevo account to ensure daily sending limits are set correctly:

```bash
python3 << 'EOF'
import requests

api_key = open('../brevo.key').read().strip()
headers = {'api-key': api_key}

r = requests.get('https://api.brevo.com/v3/account', headers=headers)
account = r.json()

print(f"Email credits remaining: {account.get('email_credits')}")
print(f"Daily limit: {account.get('daily_limit', '300')} emails")
print(f"Sending power: {account.get('sending_power', '100')} emails/hour")

# For Week 3 launch: 50 emails / 5 per day = 10 days (comfortable within limits)
EOF
```

---

## WEEK 2 EXECUTION TIMELINE

| Date | Task | Owner | Status |
|------|------|-------|--------|
| Mar 15 (Mon) | SSH setup + API validation | Developer | ⏳ |
| Mar 15 (Mon) | Import contact lists | Developer | ⏳ |
| Mar 16 (Tue) | Create email templates (4 versions) | Designer | ⏳ |
| Mar 17 (Wed) | Setup automation workflows | Developer | ⏳ |
| Mar 18 (Thu) | Send test emails to internal team | QA | ⏳ |
| Mar 18 (Thu) | Collect feedback | Product | ⏳ |
| Mar 19 (Fri) | Incorporate feedback + final approval | Board | ⏳ |
| Mar 20 (Sat) | **CAMPAIGN READY** - Final validation | Developer | ⏳ |
| Mar 22 (Mon) | **LAUNCH: Hypermarket campaign** (50 emails, 5/day) | Sales | 🚀 |

---

## TROUBLESHOOTING

### Problem: "API Key Invalid"
**Solution:**
```bash
# Regenerate API key in Brevo dashboard
# Update /opt/ACTIVE/EMAIL/brevo.key
# Retry connection test (Step 2)
```

### Problem: "Contact import fails"
**Solution:**
```bash
# Check CSV format (should have: Email, Company, Contact_Name)
# Validate email addresses in bulk
python3 << 'EOF'
import re
import csv

email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
with open('hypermarket_targets_25emails.csv') as f:
    errors = []
    for i, row in enumerate(csv.DictReader(f), 1):
        if not re.match(email_pattern, row['Email']):
            errors.append(f"Row {i}: Invalid email '{row['Email']}'")
    
    if errors:
        print("Email validation errors:")
        for err in errors[:10]:  # Show first 10
            print(f"  {err}")
    else:
        print("✅ All emails valid")
EOF
```

### Problem: "Sending limit exceeded"
**Solution:** Reduce daily batch size from 5 to 3 emails/day, extend campaign from 10 days to 17 days

---

## VALIDATION CHECKLIST (BEFORE MARCH 22 LAUNCH)

- [ ] SSH access to raspbig working
- [ ] Brevo API key validated (Step 2)
- [ ] 50 hypermarket contacts imported (Step 3a)
- [ ] 605 diaspora contacts imported (Step 3b)
- [ ] Email templates created in Brevo (Step 4a-4b)
- [ ] Automation workflows configured (Step 5)
- [ ] Test emails sent to internal team (Step 6)
- [ ] Feedback collected & incorporated (Step 7)
- [ ] Daily sending limits verified (Step 8)
- [ ] Contact list deduplicated (no duplicates)
- [ ] Unsubscribe link added to all templates
- [ ] Reply-to email configured ([contact@gospodarii.ro])

**Sign-off**: When all 12 boxes checked, campaign is **READY FOR LAUNCH**

---

## POST-LAUNCH MONITORING (WEEK 3-4)

**Daily Checks:**
- Email open rate (target: 15-20%)
- Click-through rate (target: 5-8%)
- Response rate (target: 2-3%)
- Bounces (target: <0.5%)

**Weekly Report Sent To:** [Board email]
```
Sample Weekly Report:
---
Week 3 Hypermarket Campaign Results (50 emails sent Mar 22-30):
- Opens: 8 (16% open rate) ✓
- Clicks: 2 (4% CTR) 
- Replied: 1 (2% response rate)
- Bounces: 0
- Next steps: Follow-up with non-responders on Day 7
---
```

---

## NEXT STEPS (AFTER WEEK 2)

1. **Week 3**: Monitor hypermarket campaign + start follow-up sequences
2. **Week 4**: Prepare diaspora campaign (similar setup for 605 Italy contacts)
3. **Week 5**: Scale to Germany/Austria if hypermarket metrics on track
4. **Ongoing**: Weekly reporting + A/B testing of subject lines

---

*Prepared by: Gospodarii de Altadata  
Date: March 15, 2026  
Status: Ready for implementation*
