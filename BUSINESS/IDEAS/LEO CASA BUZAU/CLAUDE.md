# LEO CASA BUZAU — Commercial Space Rental in Buzau

Finding tenants for ~220 sqm office/commercial space in Buzau, Cring neighborhood. Owner: Leo (+40 722 456 890).

## Status: READY FOR OUTREACH — 374 Companies with Email

## The Property

- Location: Buzau, Cring neighborhood
- Size: ~220 sqm + garden + parking
- Type: Office/commercial (suitable for IT, call centers, consulting, design agencies)

## Data Assets

| File | Rows | What |
|------|------|------|
| `LEO_BUZAU_WITH_EMAIL.csv` | 374 | Best list — companies with verified email+phone |
| `buzau_potrivite_companies_FINAL.csv` | 45,561 | Full company database (4 counties) |
| `leo_ultimate.csv` | ~45,563 | ANAF-enriched (phone, CAEN, VAT status) |
| `LEO_BUZAU_FINAL_ENRICHED.csv` | 44,268 | Simplified enriched version |

**Coverage**: Buzau, Ialomita, Prahova, Vrancea (34,303 companies across 4 counties).

## Target Tenant Profile

- **Legal form**: SRL preferred
- **Keywords**: SOFTWARE, IT, TECH, DESIGN, CONSULTING, CALL, SERVICE
- **CAEN codes**: 62xx (IT), 8220 (call centers), 70xx (engineering/design), 8219 (business services)
- **Excluded contacts**: Mirel, Aurelia

## Enrichment Fields

Base data + ANAF enrichment: email, phone, anaf_phone, anaf_address, anaf_caen, anaf_status, anaf_vat.

## Next Steps

1. Filter `LEO_BUZAU_WITH_EMAIL.csv` for target CAEN codes
2. Send rental announcement email (template in original claude.md)
3. Track responses, schedule property visits
4. Follow up with phone calls to non-responders

## Related

- `D:\MEMORY\IDEAS\UNIFIED DB USAGE\` — Company lookup tool (can query more companies)
- `D:\MEMORY\CLAUDE\CALLCENTERS\` — Call center data (potential tenants)
