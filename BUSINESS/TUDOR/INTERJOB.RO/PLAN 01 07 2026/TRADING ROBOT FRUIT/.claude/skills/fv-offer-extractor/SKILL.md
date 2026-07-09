---
name: fv-offer-extractor
description: "Parseaza emailuri F&V si extrage oferte structurate: produs, varietate, clasa calitate, cantitate, pret/unitate, moneda, origine, termeni livrare, plata, valabilitate. Reutilizeaza offers-memory-responder (offers_ledger). Use cand se cere 'extrage oferte din email', 'parseaza emailuri F&V', 'structureaza ofertele', 'fa lista de produse din emailuri'. Trigger obligatoriu orice cerere de parsat oferte F&V."
---

# Skill: fv-offer-extractor

**Cand se foloseste:** dupa ce fv-email-poller a adus emailurile raw, acest skill
parseaza continutul si extrage oferte structurate.

## Input
- Fisier text raw (din `DATA/raw_emails/`) sau text direct
- Context: produse cunoscute din price book (ajuta la recunoastere)

## Output - structura ofertei
```json
{
  "offer_id": "fv_20260628_001",
  "source_email_id": "<email_id>",
  "extracted_at": "2026-06-28T16:30:00",
  "products": [
    {
      "product_ro": "rosii",
      "product_en": "tomatoes",
      "variety": "bune",
      "quality_class": "extra",
      "quantity_kg": 10000,
      "price_per_unit": 1.50,
      "currency": "EUR",
      "unit": "kg",
      "origin": "Romania, Giurgiu",
      "delivery_terms": "FOB Bucuresti",
      "payment_terms": "30 zile",
      "valid_until": "2026-07-15",
      "certification": ["GlobalGAP"],
      "packaging": "ladite 10kg",
      "availability": "imediat"
    }
  ],
  "contact": {
    "name": "Ion Popescu",
    "email": "contact@ferma.ro",
    "phone": "0722...",
    "company": "Ferma SRL"
  },
  "raw_snippet": "Oferim 10 tone rosii extra, pret 1.5 EUR/kg FOB..."
}
```

## Campuri obligatorii
- `product_ro` (minim)
- `quantity_kg` sau `price_per_unit` (macar unul)
- Restul: optional, marcheaza null daca nu se poate extrage

## Cum parseaza
1. Citeste email text (body + attachment text)
2. Identifica produsele (lista cunoscuta + regex)
3. Extrage cantitati (regex: `\d+\.?\d*\s*(tone|kg|to)` )
4. Extrage preturi (regex: `\d+[.,]\d{2}\s*(EUR|RON|€|lei|euro)` )
5. Extrage termeni (livrare, plata, valabilitate)
6. Scrie in offers_ledger.jsonl (append)

## Reguli
- Daca acelasi produs+origine+pret apare in ultimele 7 zile -> flag "duplicate", skip
- Daca <50% campuri completate -> marcheaza "partial_offer", nu bloca pipeline
- Pret lipsa -> incearca sa estimeze din price book; daca nu, "price_unknown"
- Moneda implicita: EUR (daca nu specificat, presupune EUR pentru export, RON pentru RO)
