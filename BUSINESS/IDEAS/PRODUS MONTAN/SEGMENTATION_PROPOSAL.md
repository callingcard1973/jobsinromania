# Product Segmentation — AGRIP-Aligned (Annex I TFEU)

## DB Columns Added
- `agrip_sector`: DAIRY, HONEY, MEAT, FISH, BAKERY, FRESH_FV, PROCESSED_FV, HERBS, CEREALS
- `processing`: FRESH, MATURED, PROCESSED, NON_PERISHABLE

## AGRIP Sector Mapping

| AGRIP Sector | CN Chapter | RNPM Source | Est. Products |
|---|---|---|---|
| DAIRY | Ch.04 | LAPTE + OUA | ~1,362 |
| HONEY | Ch.04.09 | PRODUSE APICOLE | 611 |
| FRESH_FV | Ch.07-08 | PRODUSE VEGETALE (fresh) | ~1,600 |
| PROCESSED_FV | Ch.20 | PRODUSE VEGETALE (jams, juices) | ~300 |
| MEAT | Ch.02+16 | CARNE SI PRODUSE DIN CARNE | 179 |
| FISH | Ch.03+16 | PESTE SI PRODUSE DIN PESTE | 34 |
| CEREALS | Ch.10 | PRODUSE VEGETALE (cereals) | ~60 |
| BAKERY | Ch.19 | PAINE, PRODUSE DE PANIFICATIE | 4 |
| HERBS | Ch.12-13 | PRODUSE VEGETALE (herbs) | ~50 |

## AGRIP 2026 Best-Fit Topics

| Topic | Budget | Why |
|---|---|---|
| **AGRIP-SIMPLE-2026-IM-EU-QS** | EUR 13.1M | "Produs montan" = EU optional quality term (Reg. 1151/2012) |
| AGRIP-MULTI-2026-IM | EUR 7M | If partnering with FR/IT org |
| AGRIP-SIMPLE-2026-TC-ALL | EUR 46.8M | For UK/non-EU export campaigns |

## 3 Promotion Lines for AGRIP Application

### Line 1 — Romanian Mountain Dairy (~1,362 products, ~563 producers)
- Products: burduf, cascaval, telemea, cas, urda, smantana, unt, oua
- Target: EU internal (DE/FR/IT diaspora shops, specialty retailers)
- Activities: Anuga Cologne, SIAL Paris, in-store tastings

### Line 2 — Romanian Mountain Honey (611 products, ~254 producers)
- Products: polyflora, acacia, linden, honeydew, pollen, propolis, wax
- Target: UK (post-Brexit artisanal demand), DE, FR
- Activities: IFE London, digital campaign, B2B honey importers

### Line 3 — Romanian Mountain Preserves (~350 products)
- Products: jams (dulceata), syrups, juices, pickles (muraturi), zacusca
- Target: Romanian diaspora (IT/ES/DE/UK/FR — 4M+ Romanians abroad)
- Activities: diaspora shop network, online, trade fairs

## Classification Method
Keyword regex in `produs_montan_parse.py::classify_product()`.
Priority: RNPM category first, then product name keywords for VEGETALE subdivision.

## Verification
```sql
SELECT agrip_sector, processing, COUNT(*)
FROM produs_montan_products GROUP BY 1, 2 ORDER BY 1, 2;

SELECT COUNT(*) FROM produs_montan_products WHERE agrip_sector IS NULL;
-- Expected: 0
```
