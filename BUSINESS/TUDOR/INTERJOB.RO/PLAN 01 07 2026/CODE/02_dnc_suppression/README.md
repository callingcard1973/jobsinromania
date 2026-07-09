# 02_dnc_suppression — DNC unificat (mirror laptop)

**Sursa canonica (single source of truth): raspibig**
`/opt/ACTIVE/EMAIL/CAMPAIGNS/`:
- `dnc_list.csv` — opt-out-uri (email,source,date)
- `dnc_bounces.txt` — bounce-uri hard
- `dnc_bounces_annotated.csv` — bounce-uri cu motiv
- `SCRIPTS/SHARED/dnc_utils.py` — utilitar comun (load/merge/clean)
- `PROCESSORS/merge_dnc.py` — job de unificare DNC
- `AGENTS/dnc-manager.py` — agent harness email-campaigns (scriere atomica)

Acest folder e un **mirror read-only** pe laptop, pentru inspectie rapida
si curatare lead-uri inainte de campanii. **Nu scrie DNC aici** — orice
opt-out/bounce nou se adauga pe raspibig (agent dnc-manager scrie atomic).
DNC pe raspi (.20) are `anofm_dnc_refresh.log` (cron local) care se
propaga inapoi pe raspibig.

## Sync
```powershell
.\sync_dnc_from_raspibig.ps1
```
Pull `dnc_list.csv` + `dnc_bounces.txt` din raspibig in acest folder.
Ruleaza inainte de orice build audienta pe laptop.

## Reguli (din CLAUDE.md)
- Toate cele 5 directii folosesc ACELASI suppression (acest mirror / sursa raspibig).
- Nicio campanie noua fara DNC check (regula HARD).
- Leads keyed pe email non-null; DNC match pe email lowercase.

## Fisiere generate (gitignored — date personale)
- `dnc_list.csv` (mirror)
- `dnc_bounces.txt` (mirror)
- `.last_sync` (timestamp ultim sync)
