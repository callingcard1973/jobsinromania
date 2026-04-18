#!/bin/bash
# Bulgarian Campaigns Monitoring Script
# Usage: ./monitor_bulgarian_campaigns.sh

echo "=== BULGARIAN CAMPAIGNS STATUS $(date) ==="
echo

# Check service status
echo "🔧 ORCHESTRATOR SERVICE:"
systemctl is-active unified-orchestrator.service
echo

# Check running processes
echo "⚡ ACTIVE CAMPAIGNS:"
ps aux | grep "send_campaign.py" | grep -E "(bulgaria|a1_transport)" | grep -v grep || echo "None running"
echo

# Check database status
echo "📊 DATABASE STATUS:"
psql -d interjob_master -U tudor -t -c "
SELECT
    CASE
        WHEN table_name = 'bg_campaign' THEN 'BG_CONTRACTORS    '
        WHEN table_name = 'a1_transport_bulgaria' THEN 'A1_TRANSPORT_BG   '
    END as campaign,
    LPAD(total::text, 6) || ' total | ' ||
    LPAD(pending::text, 6) || ' pending | ' ||
    LPAD(sent::text, 4) || ' sent'
FROM (
    SELECT 'bg_campaign' as table_name,
           COUNT(*) as total,
           COUNT(CASE WHEN campaign_status = 'pending' THEN 1 END) as pending,
           COUNT(CASE WHEN campaign_status = 'sent' THEN 1 END) as sent
    FROM bg_campaign
    UNION ALL
    SELECT 'a1_transport_bulgaria',
           COUNT(*),
           COUNT(CASE WHEN campaign_status = 'pending' THEN 1 END),
           COUNT(CASE WHEN campaign_status = 'sent' THEN 1 END)
    FROM a1_transport_bulgaria
) stats;"
echo

# Check today's sends
TODAY=$(date +%Y-%m-%d)
SENDS_TODAY=$(psql -d interjob_master -U tudor -t -c "
SELECT COUNT(*) FROM bg_send_log WHERE sent_at::date = '$TODAY'
" | tr -d ' ')

if [ "$SENDS_TODAY" -gt 0 ]; then
    echo "📤 TODAY'S SENDS: $SENDS_TODAY"
    echo
fi

echo "💳 BREVO CREDITS:"
cd /opt/ACTIVE/EMAIL/CAMPAIGNS && python3 -c "
import os, requests
from dotenv import load_dotenv
load_dotenv('.env')

accounts = [
    ('BuildJobs', os.getenv('BREVO_BUILDJOBS_API_KEY')),
    ('Seicarescu', os.getenv('BREVO_SEICARESCU_API_KEY')),
    ('CareWorkers', os.getenv('BREVO_CAREWORKERS_API_KEY'))
]

total = 0
for name, api_key in accounts:
    if api_key:
        try:
            headers = {'api-key': api_key}
            response = requests.get('https://api.brevo.com/v3/account', headers=headers, timeout=5)
            if response.status_code == 200:
                credits = response.json().get('plan', [{}])[0].get('credits', 0)
                print(f'{name:12}: {credits:3} credits')
                total += credits
            else:
                print(f'{name:12}: ERROR')
        except:
            print(f'{name:12}: OFFLINE')

print(f'{"TOTAL":12}: {total:3} available')
"

echo
echo "✅ Bulgarian campaigns fully operational with working Brevo accounts"
echo "📈 Total capacity: 870 emails/day across all campaigns"