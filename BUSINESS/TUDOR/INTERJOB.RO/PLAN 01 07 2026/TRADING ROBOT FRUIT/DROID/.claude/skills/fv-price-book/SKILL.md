---
name: fv-price-book
description: "Mentine price book-ul F&V: toate ofertele primite, benchmark pe produs/calitate/origine/sezon, min/max/avg per produs, detectare trenduri. Use cand se cere 'show price book', 'benchmark preturi', 'ce pret e corect pentru X', 'cumpar cel mai ieftin Y', 'price trends', 'istoric preturi Z'. Trigger obligatoriu la orice cerere de preturi/benchmark/piata F&V."
---

# Skill: fv-price-book

**Cand se foloseste:** la cereri de preturi, benchmark, piata, sau automat
dupa fiecare extractie de oferte.

## Ce face
1. Citeste toate ofertele din offers_ledger.jsonl
2. Grupeaza pe (produs, calitate, origine)
3. Calculeaza: min, max, avg, median, count, ultimul pret
4. Detecteaza trend: urcare/coborare/stabil (ultimele 3 oferte vs ultimele 30 zile)
5. Incruciseaza cu datele din EU wholesale scrapere (Rungis, Berlin, Madrid etc.)
6. Salveaza price_book.json

## Output
```json
{
  "product": "rosii",
  "quality": "extra",
  "origin": "Romania",
  "last_updated": "2026-06-28",
  "benchmark": {
    "min_price_eur_kg": 1.20,
    "max_price_eur_kg": 2.10,
    "avg_price_eur_kg": 1.55,
    "median_price_eur_kg": 1.50,
    "offer_count": 24,
    "last_price_eur_kg": 1.50,
    "trend": "stable"
  },
  "eu_market_comparison": {
    "rungis_eur_kg": 2.10,
    "berlin_eur_kg": 1.95,
    "madrid_eur_kg": 1.80
  },
  "seasonal": {
    "peak_months": ["June", "July", "August"],
    "low_months": ["December", "January"]
  },
  "available_offers": [
    {"from": "Ferma SRL", "price": 1.50, "qty_kg": 10000, "date": "2026-06-28"}
  ]
}
```

## Comenzi
```bash
python CODE/fv_price_book.py --rebuild      # re-citeste tot offers_ledger
python CODE/fv_price_book.py --product rosii # doar un produs
python CODE/fv_price_book.py --trends        # produse cu fluctuatii >20%
python CODE/fv_price_book.py --dump          # price_book.json complet
```

## Sursa date
- Primar: offers_ledger.jsonl (din emailuri)
- Secundar: EU wholesale scrapere (Rungis, Berlin, Madrid etc.)
- Tertiar: date COOP existente (preturi istorice)

## Reguli
- Ofertele expirate (>30 zile sau valid_until trecut) nu intra in benchmark
- Daca <5 oferte pentru un produs, marcheaza "low_confidence"
- Trendul se calculeaza pe minim 10 oferte in 60 zile
