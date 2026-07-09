---
name: fv-email-poller
description: "Polls Yahoo IMAP (apaminerala@yahoo.com) for fruit & vegetable offer emails. Filters by F&V keywords (product names, 'oferta', 'pret', 'disponibil', 'livrare'). Reuses yahoo-imap-reader infrastructure. Use when asked to 'poll email for offers', 'check new offers', 'fetch F&V emails', 'read suppliers inbox', 'get latest offers from email'. Trigger obligatoriu pentru orice cerere de tip 'citeste/verifica/ia emailuri cu oferte legume-fructe'."
---

# Skill: fv-email-poller

**Cand se foloseste:** la orice cerere de tip "citeste emailuri cu oferte",
"ia oferte noi din inbox", "poll suppliers", "check new F&V offers".

Reutilizeaza infrastructura existenta `yahoo-imap-reader` (yahoo-imap-reader = global user skill in ~/.claude/skills, nu skill local) (IMAP Yahoo,
app password din memorie/.env (gmail_app_passwords), host imap.yahoo.com:993).

## Ce face
1. Conectare IMAP la apaminerala@yahoo.com
2. Cauta emailuri cu cuvinte cheie F&V din ultimele N zile (default 7)
3. Filtreaza OFERTE (exclude facturi, newsletters, spam)
4. Intoarce lista de emailuri cu oferte, marcate ca "new" / "already_processed"
5. Salveaza raw text in `DATA/raw_emails/` pentru parsare ulterioara

## Cuvinte cheie F&V
```
# general
oferta, ofertă, pret, preț, disponibil, stoc, livrare, vând, vand, produse

# produse
rosii, tomate, castraveti, ardei, ceapa, usturoi, cartofi, morcovi, varza,
conopida, brocoli, salata, spanac, vinete, dovlecei, fasole, mazare, porumb,
ciuperci, pepene, struguri, mere, pere, prune, capsuni, zmeura, afine, cirese,
visine, caise, piersici, nectarine, gutui, nuci, alune, migdale

# cantitati/ambalaj
kg, tone, paleti, cutii, ladite, bigbag, europalet, container, camion,

# calitate
extra, clasa I, clasa II, calitate, sortare, certificare, globalgap

# fructe exotice
banane, portocale, lamai, grepfrut, kiwi, avocado, mango, ananas
```

## Output
```json
{
  "batch_id": "2026-06-28-1630",
  "total_fetched": 12,
  "new_offers": 5,
  "offers": [
    {
      "email_id": "<unique>",
      "from": "contact@ferma.ro",
      "date": "2026-06-28T14:30:00",
      "subject": "Oferta rosii extra - 10 tone",
      "fv_keywords_found": ["rosii", "oferta", "tone"],
      "has_pricing": true,
      "body_path": "DATA/raw_emails/2026-06-28-1630_001.txt"
    }
  ]
}
```

## Comenzi cod
```bash
python CODE/fv_email_poller.py --days 3 --save-raw
python CODE/fv_email_poller.py --email-id "<id>"  # re-fetch specific
python CODE/fv_email_poller.py --stats  # numara oferte per sapt/produs
```

## Reguli
- Nu modifica emailurile in Yahoo (read-only)
- Skip emailuri deja procesate (verifica GUID in offers_ledger.jsonl)
- Timestamp batch pentru urmarire
- Daca IMAP e down: retry 3x cu 30s pauza, apoi raporteaza
