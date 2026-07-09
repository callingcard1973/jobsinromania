# TRADING ROBOT FRUIT

Robot de trading LEGUME-FRUCTE pentru cooperativa: leaga producatori (supply) cu
cumparatori (demand) si tine minte propunerile de pret de la lanturi (Mega Image).

## Cod
| Fisier | Ce face |
|--------|---------|
| `trading_robot.py` | match producatori legume-fructe <-> cumparatori (local + intl export), pe produs normalizat multilingv |
| `mega_image_imap_fetch.py` | citeste apaminerala@yahoo.com (read-only), ia mailurile de la amustatea@mega-image.ro, parseaza tabelul de pret |
| `mega_image_price_memory.py` | registru preturi + raport + sugestie contra-pret |

## Output -> `CLAUDE TRADING ROBOT/`
- `matches_legume_fructe.csv` + `REPORT.md` — match-uri producator<->cumparator
- `mega_image_prices.jsonl` + `.csv` + `MEGA_IMAGE_REPORT.md` — memoria preturilor Mega Image

## Surse de date
- Supply: `../COOP GOSPODARII DE ALTADATA/SURSE_IUNIE/SUPERMARKETURI/FURNIZORI/DATA/via_profi_producers_complete_scraped.csv`
- Demand local: `.../SUPERMARKETURI/DATA/SUPPLIERS/vegetable_buyers_master.csv`
- Demand intl: `.../SUPERMARKETURI/EXPORT/DATA/eu_wholesale_buyers_master.csv`
- Preturi: live IMAP apaminerala@yahoo.com <- amustatea@mega-image.ro

## Reguli
NU trimite/raspunde automat. Deciziile de pret = ale lui Tudor (gated). Mailbox read-only.
Harness: skill `mega-image-price-memory` + agent `price-memory-keeper`; trading match
prin `offers-memory-responder`. Ruleaza saptamanal (cron raspibig recomandat).

## TODO util
- Extinde `legume_taxonomy.py` (conopida, vinete, dovlecei, salata, fasole...) — acum
  doar 49/8500 producatori au produs recunoscut.
- Adauga si alti cumparatori care trimit propuneri (acelasi parser).
