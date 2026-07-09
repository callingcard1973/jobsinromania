# JOBFAIRS — Physical Recruitment Fairs: Norwegian Oil Employers → Romanian Workers

Organize real job fairs in Romania where Norwegian (and EU) HR managers fly in to interview and hire Romanian workers on the spot. Focus: oil & gas, offshore, construction, industrial.

## Why Now

**Strait of Hormuz stays open → Norway pumps at full capacity → massive worker demand.**

- Norway oil sector: 200,000+ direct employees, chronic labor shortage
- Romanian workers: proven track record in Norwegian oil/offshore (Aker Solutions, Equinor subcontractors)
- Wage gap: Norwegian oil worker EUR 5,000-8,000/mo vs Romanian cost EUR 2,500-4,000/mo = 30-50% savings for employer
- EU free movement: no visa, no work permit needed
- ANOFM regions with mass layoffs (Hunedoara, Gorj, Vaslui) = motivated, available workforce

## Revenue Model

| Stream | Price | Per fair | Annual (12 fairs) |
|--------|-------|----------|-------------------|
| Employer booth fee | EUR 1,000-3,000 | 10 employers = EUR 10-30K | EUR 120-360K |
| Placement success fee | EUR 500-2,000/worker | 30 placements = EUR 15-60K | EUR 180-720K |
| Travel/logistics package | EUR 500-1,000/HR manager | 10 managers = EUR 5-10K | EUR 60-120K |
| Worker preparation fee | EUR 50-100/worker | 100 workers = EUR 5-10K | EUR 60-120K |
| Sponsor (Wizz Air, hotels) | EUR 500-2,000 | 3 sponsors = EUR 1.5-6K | EUR 18-72K |

**Conservative (Year 1, 6 fairs)**: EUR 100-200K
**Full capacity (12 fairs/year)**: EUR 400K-1.3M

## The Fair — What Happens

```
BEFORE (4-6 weeks):
  Tudor emails 335K Norwegian contacts → "Free recruitment event in Romania"
  ANOFM posts event → workers register → pre-screening (CV + skills + language)
  HR managers book flights (Wizz Air Oslo→Bucharest EUR 50-150)
  Tudor books venue (hotel conference room EUR 500-2000/day)

DAY OF FAIR:
  08:00  HR managers arrive at venue (Bucharest/Hunedoara/Timisoara)
  09:00  Opening: sector briefing, Romanian labor law, detachment rules
  09:30  Speed interviews: 15-min slots, employer rotates through pre-matched workers
  12:00  Lunch (networking, follow-up conversations)
  13:00  Afternoon interviews + skills testing (welding, electrical, safety certs)
  16:00  Offers on the spot: "You start Monday in Stavanger"
  17:00  Admin: contracts, A1 forms, travel booking, accommodation briefing

AFTER:
  Tudor handles: A1 detachment paperwork + travel logistics + first-week coordination
  Placement fee collected per hired worker
  Follow-up fair scheduled for next quarter
```

## Target Employers (Norway Oil & Gas)

| Company | What | Workers needed |
|---------|------|---------------|
| Equinor (Statoil) | Oil & gas operator | Offshore, drilling, maintenance |
| Aker Solutions | Engineering, subsea | Welders, pipe fitters, electricians |
| TechnipFMC | Subsea equipment | Assembly, testing, installation |
| Kvaerner | Platforms, yards | Construction, steel, painting |
| Subsea 7 | Subsea engineering | ROV, diving, pipeline |
| Aibel | Maintenance, mods | Multi-discipline trades |
| Apply Sorco | Staffing | All offshore trades |
| Bilfinger | Industrial services | Scaffolding, insulation, blasting |

**Also**: subcontractors, staffing agencies (Adecco NO, Manpower NO, Randstad NO)

**Data available**: 335K Norwegian company contacts in PostgreSQL (IDEA-002)

## Target Workers (Romania)

| Region | Why | Workers available |
|--------|-----|-------------------|
| Hunedoara | Steel industry decline, skilled metalworkers | 5,000+ |
| Gorj | Mining decline, heavy equipment operators | 3,000+ |
| Timisoara | Industrial hub, multilingual workforce | 10,000+ |
| Galati | Shipyard workers (ArcelorMittal), welders | 4,000+ |
| Constanta | Port workers, offshore-adjacent skills | 3,000+ |

**Key skills in demand**: welding (MIG/TIG/SMAW), pipe fitting, scaffolding, electrical, crane operation, NDT, HSE, offshore survival (BOSIET/HUET)

## Venue Strategy

| City | Venue type | Cost/day | Why |
|------|-----------|----------|-----|
| Bucharest | Hotel conference (Marriott/Hilton) | EUR 1,000-2,000 | Flights, international feel |
| Hunedoara | ANOFM office / Casa de Cultura | EUR 200-500 | Mass layoff region, ANOFM co-hosts |
| Timisoara | University aula / hotel | EUR 500-1,000 | Western Romania, close to EU border |
| Constanta | Port conference center | EUR 500-1,000 | Offshore/maritime workers |

## What Already Exists (5,601 lines code)

| Module | What it does | Ready? |
|--------|-------------|--------|
| `src/database/` | 7 tables: employers, workers, matches, events, compliance, comms, finance | Yes |
| `src/data/` | Extract employers from 50M+ master DB by sector | Yes |
| `src/communications/` | Brevo email campaigns with templates | Yes |
| `src/anofm/` | Scrape ANOFM job fair calendar | Yes |
| `src/legal/` | GDPR consent + retention + right-to-forget | Yes |
| `config.py` | Pydantic config with phased limits | Yes |

## NORWAY_VIRGIL Campaign — DEPLOYED (2026-04-14)

**45,925 Norwegian employers** consolidated into single campaign `norway_virgil` on raspibig.

| Source | Contacts |
|--------|----------|
| Construction | 18,420 |
| TED Winners (EU contracts) | 7,931 |
| Transport & Logistics | 6,503 |
| Industrial (fish, food, cleaning) | 4,992 |
| HoReCa (hotels, restaurants) | 4,157 |
| Oil & Offshore | 3,006 |
| EURES employers + agencies | 655 |
| HR Managers (named) | 261 |

- **Config**: `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/norway_virgil.json`
- **Template**: `/opt/.../templates/jobfairs/template1.txt`
- **DB tables**: `norway_virgil`, `norway_virgil_send_log`, `norway_virgil_dnc`
- **Sender**: tudor@seicarescu.com via Brevo (BREVO_SEICARESCU_API_KEY)
- **Reply-to**: tudor@seicarescu.com
- **Status**: DISABLED — set `"enabled": true` when ready
- **Local CSV**: `D:\MEMORY\JOBFAIRS\campaign\CSV\norway_virgil_45925.csv`
- **Virgil manages** this campaign

## What Still Needs Building

### P1: Landing Page + Registration (Week 1-2)
- Landing page on `buildjobs.eu/norway-fair` or `factoryjobs.eu/offshore`
- Registration form: company, positions, headcount, dates available

### P2: Worker Pre-Screening (Week 2-3)
- ANOFM partnership: co-host event, they provide venue + worker list
- Worker registration: CV, certifications (welding/BOSIET), language level
- Pre-matching algorithm: employer needs ↔ worker skills
- Interview schedule generator: 15-min slots, optimized rotation

### P3: Fair Logistics (Week 3-4)
- Venue booking workflow
- HR manager travel package (flights, hotel, airport transfer)
- Day-of-fair checklist and run-of-show
- Contract templates (Romanian + Norwegian labor law)
- A1 detachment form automation

### P4: Post-Fair Pipeline (ongoing)
- Placement tracking: worker → employer → start date → success
- Invoice generation: booth fee + placement fee
- Follow-up campaign: "Next fair in 3 months — book early"

## First Fair Plan

**Target**: June/July 2026 (summer = offshore season ramp-up)
**Location**: Bucharest (best flight access for Norwegians)
**Sector**: Oil & gas, offshore, industrial maintenance
**Employers**: 10 Norwegian companies (Aker, Aibel, Bilfinger + 7 staffing agencies)
**Workers**: 100 pre-screened (welders, fitters, electricians from Hunedoara/Galati)
**Goal**: 30 placements = EUR 15-60K in placement fees + EUR 10-30K booth fees

## Competitive Advantage

- **335K Norwegian contacts** — no recruiter in Romania has this
- **15 .eu job domains** — SEO traffic + credibility
- **50M+ employer database** — can target any sector/country
- **6,300 emails/day capacity** — mass outreach infrastructure
- **ANOFM relationships** — co-hosting = free venue + worker access + government stamp
- **Email + LLM automation** — follow-ups, matching, scheduling at scale
- **Existing code** — 5,601 lines of DB, email, GDPR, ANOFM integration ready

## Response & Autoheal (2026-04-15) ✅ LIVE

### Response Tracker
- 19 IMAP inboxes monitored every 5 min
- Classifies: INTERESTED, NOT_INTERESTED, WORKER_APPLICATION, REPLY, BOUNCE
- Workers auto-routed to `master_applicants.db` (734+ applicants) + auto-reply with apply form
- Matches responses to campaigns via `email_sender.send_log`
- Telegram alerts for employer leads
- Script: `/opt/ACTIVE/INFRA/SKILLS/response_tracker.py` + `response_tracker_inboxes.py` + `worker_router.py`

### Solonet Order Pipeline
- `/opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py` — auto-creates drafts from .ro employer responses
- DB: `interjob_master.solonet_orders` (status: draft→sent→responded→placed + revenue)
- Flow: response_tracker finds .ro INTERESTED → draft created → Telegram `/send_solonet_X` → email to solonet.vacancy@gmail.com
- Auto follow-up after 3 days if no response
- Revenue tracking: `/solonet_placed_X <workers> <eur>`
- No LLM tokens used

### Email Processor
- `/opt/ACTIVE/INFRA/SKILLS/email_processor.py` — every 10 min, sklearn + Ollama classification
- `/opt/ACTIVE/INFRA/SKILLS/email_executor.py` — executes approved actions
- DNC table: `email_sender.dnc` (reason + expiry)
- Follow-up table: `email_sender.followup` (company + date)

### Results (2026-04-16)
- 30,824 emails sent → 80 responses → 8 INTERESTED employers + 18 worker applications
- 3 Romanian employer orders created for solonet (BADENMOB, DAROM, DROPIA)
- Norwegian lead: post@hlev.no (healthcare — forwarded to boss)

### Autoheal Watchdog
- Raspibig: 10 checks (services, 409 conflicts, dashboard, orchestrator, disk, Ollama, NanoClaw heartbeat, Caddy, response tracker cron, solonet follow-ups)
- Raspi: 8 checks (services, disk, PostgreSQL, Node-RED, Caddy, bot conflicts, raspibig reachability)
- Both run every 15 min via cron, alert only on failure

## Related

- `D:\MEMORY\IDEAS\INVENTAR\MASTER.csv` — IDEA-092 (active)
- `D:\MEMORY\IDEAS\NATO\` — MK base expansion = similar model for military contractors
- `D:\MEMORY\FACTORYJOBS\` — 3,751 factory employers (diversify beyond oil)
- `D:\MEMORY\CONSTRUCTION PROJECTS\` — construction sector fairs
- `D:\MEMORY\IDEAS\COOPERATIVA BUSINESS\` — cooperative handles worker contracts
- Norway 335K campaign — IDEA-002 in MASTER.csv
