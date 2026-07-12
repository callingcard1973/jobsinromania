# 03_sent_once_tracking — Dedup cross-campanie (sent-once)

Suppression **intre** campanii, complementar dedup-ului per-campanie (`sent.json`)
si DNC-ului global. Rezolva suprapunerile masurate pe teren (2026-07-12):
374 adrese contactate din >1 campanie, dintre care 61 pe acelasi subiect cereale
(`SILOZURI` × `SILOZURI_CEREALE_11JUD`).

## Principiu
NU e "un email o singura data vreodata". Un lead poate primi legitim mesaje pe
subiecte diferite. Dedup pe:
- **grup de subiect** (`campaign_groups.json`) — o singura data per grup;
- **cooldown global** — optional, nu re-contacta acelasi email in ultimele N zile.

DNC ramane strat separat de hard-suppression (nu se amesteca aici).

## Componente
- `sent_once.py` — ledger SQLite `(email, campaign, grp, ts)` + API:
  `record`, `record_many`, `already_sent(group=, cooldown_days=)`, `filter_new`, `stats`.
- `groups.py` + `campaign_groups.json` — mapare campanie -> grup
  (campanie nemapata => grup = numele ei, deci se comporta ca azi, sigur).
- `backfill_from_sentjson.py` — populeaza ledgerul din `sent.json`-urile existente
  (read-only pe surse). Suporta formatele `by_date`, `by_email`, `sent`, liste.
- `filter_recipients.py` — filtreaza o lista de destinatari inainte de send.
- `tests/test_sent_once.py` — teste unitare (stdlib, fara retea/secrete).

Doar stdlib (sqlite3/json/csv) — ruleaza direct pe raspibig, fara pip.

## Utilizare
```bash
# 1) backfill (dry-run intai)
python3 backfill_from_sentjson.py --base /opt/ACTIVE/EMAIL/CAMPAIGNS --dry-run
python3 backfill_from_sentjson.py --base /opt/ACTIVE/EMAIL/CAMPAIGNS

# 1b) CROSS-MASINA: sent-tracking-ul e per-masina. ANOFM + DEFICIT trimit de pe
#     raspi (.20), restul de pe raspibig (.21). `--base` e repetabil ca ledgerul
#     sa agrege ambele (masurat 2026-07-12: audienta DEFICIT de pe raspi avea 226
#     adrese deja contactate de pe raspibig, 203 in acelasi grup DEFICIT_JOBS).
python3 backfill_from_sentjson.py \
    --base /mnt/raspibig/opt/ACTIVE/EMAIL/CAMPAIGNS \
    --base /mnt/raspi/opt/ACTIVE/EMAIL/CAMPAIGNS \
    --db /opt/ACTIVE/EMAIL/CAMPAIGNS/global_sent_ledger.sqlite

# 2) filtrare inainte de campanie (nu inregistreaza)
python3 filter_recipients.py --campaign SILOZURI_CEREALE_11JUD \
    --in leads.csv --out leads_dedup.csv --cooldown-days 14

# 3) API in cod
from sent_once import SentOnceLedger
from groups import group_for
with SentOnceLedger() as L:
    if not L.already_sent(email, group=group_for(camp), cooldown_days=14):
        ...  # trimite
        L.record(email, camp, group_for(camp))
```

`SENT_ONCE_DB` (default `/opt/ACTIVE/EMAIL/CAMPAIGNS/global_sent_ledger.sqlite`)
si `CAMPAIGN_GROUPS_JSON` sunt configurabile prin env.

## Teste
```bash
python3 -m pytest tests/ -q     # sau: python3 tests/test_sent_once.py
```

## Integrare propusa (fara a atinge senderele)
1. Backfill ledger.
2. La build audienta, ruleaza `filter_recipients.py` (grup + cooldown) dupa DNC.
3. Cron `*/15` care preia intrarile noi din `sent.json`-uri in ledger, SAU
   apeleaza `record` din sender dupa fiecare trimitere.

## Status
Cod + teste. **Nedesfasurat pe raspibig** — deploy dupa aprobare (regula: fara
modificari pe teren fara instructiune explicita).
