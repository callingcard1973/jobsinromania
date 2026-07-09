---
name: fv-deal-flow
description: "Match oferte F&V cu cumparatori + deal lifecycle. Extinde offers-memory-responder deal_broker pentru F&V: match pe produs+calitate+pret+origine, track status proposed->negotiating->accepted->closed->shipped. Use cand se cere 'match offers to buyers', 'find buyer for X', 'deschide deal', 'status deals', 'close deal', 'ce oferte n-au cumparator'. Trigger obligatoriu la match/deal/trading F&V."
---

# Skill: fv-deal-flow

**Cand se foloseste:** dupa ce ofertele sunt in price book, acest skill
gaseste cumparatori si deschide dealuri.

Integreaza cu `offers-memory-responder` (offers_ledger, requests_ledger,
auto_matcher, deal_broker) — extinde pentru F&V specific.

## Componente

### 1. Buyer Matching
Match oferta cu cumparatori din:
- `DATA/buyers_list.csv` (cumparatori existenti COOP)
- `requests_ledger.jsonl` (cereri de cumparare primite)
- Cumparatori noi identificati din emailuri

Match criteria (weighted):
| Criteriu | Greutate | Descriere |
|----------|----------|-----------|
| Produs | 40% | Match exact produs (rosii-rosii) |
| Calitate | 25% | Aceeasi clasa sau superioara |
| Pret | 20% | Oferta pret <= buyer max_price (sau fara pret) |
| Origine | 10% | Aceeasi tara / apropiere geografica |
| Cantitate | 5% | Buyer qty <= oferta qty (sau fractionabil) |

Score >= 60% = lead. Score >= 80% = deal ready.

### 2. Deal Lifecycle
```
proposed → negotiating → accepted → closed → shipped
                                  → rejected
                                  → stalled (7 zile fara raspuns)
```

Fiecare tranzitie logata in `deals.jsonl` cu timestamp + actiune.

### 3. Deal Struct
```json
{
  "deal_id": "deal_fv_20260628_001",
  "status": "proposed",
  "score": 85,
  "product": "rosii",
  "quantity_kg": 10000,
  "price_eur_kg": 1.50,
  "supplier": {"name": "Ferma SRL", "email": "contact@ferma.ro"},
  "buyer": {"name": "Lidl RO", "email": "buyer@lidl.ro"},
  "offer_id": "fv_20260628_001",
  "request_id": "req_20260625_003",
  "history": [
    {"date": "2026-06-28T16:35", "action": "proposed", "by": "fv-trader"},
    {"date": "2026-06-28T17:00", "action": "negotiating", "by": "fv-dealer", "note": "draft trimis spre aprobare"}
  ],
  "negotiation_rounds": 0,
  "terms": {
    "delivery": "FOB",
    "payment": "30 zile",
    "valid_until": "2026-07-15"
  }
}
```

## Comenzi
```bash
python CODE/fv_deal_flow.py --match           # run buyer matching
python CODE/fv_deal_flow.py --match --export   # export shortlist
python CODE/fv_deal_flow.py --open-deal --id <offer_id> --buyer <email>
python CODE/fv_deal_flow.py --deals --status proposed
python CODE/fv_deal_flow.py --deals --summary  # KPIs
```

## Reguli
- Nu deschide deal daca acelasi supplier+buyer+produs are deja un deal active (proposed/negotiating)
- Deal-uri cu score <60%: listeaza ca "potential" dar nu deschide automat
- Daca buyer nu are email valid (null), nu propune — flag pt outreach manual
- Integrare cu DNC: daca buyer/supplier e in DNC, skip
