# SESSION HANDOFF — 13 Aprilie 2026
# EBRD Expansion + ULTRAPLAN D3/D4 + Enrichment + Proposals

---

## CE S-A FACUT IN SESIUNEA ASTA

### TASK 1: EBRD Contractors — 84 gasiti in 14 tari (COMPLET)
Fisiere salvate in `D:\MEMORY\BERD EBRD\{tara}\CONTACTE_CONSTRUCTORI.md`:

| Tara | Constructori | Cu email | Confirmati pe proiect |
|------|-------------|----------|----------------------|
| Egypt | 7 | 7 | Scatec (solar) |
| Hungary | 7 | 6 | Solarpro (Renalfa 450MW) |
| Estonia | 7 | 7 | Evecon (Hertz BESS), Connecto |
| Slovenia | 7 | 7 | NGEN (BESS EUR 70M) |
| N. Macedonia | 6 | 6 | Gulermak (Rail), ENKA (motorway) |
| Latvia | 6 | 5 | Skonto Buve (Riga Airport EUR 75M) |
| Bosnia | 6 | 6 | Euro-Asfalt, Hering (Corridor Vc) |
| Morocco | 6 | 4 | SGTM+STFA (Nador Port EUR 300M) |
| Croatia | 6 | 6 | IE-Energy (BESS 60MW) |
| Kazakhstan | 6 | 3 | Alarko (BAKAD USD 225M), TAV (Almaty) |
| Lithuania | 5 | 3 | E-energija (Kelme Wind) |
| Montenegro | 5 | 4 | Bemax (Bar-Boljare), Nordex (Gvozd) |
| Albania | 5 | 5 | INC (2 railways), Voltalia (140MW) |
| Kosovo | 5 | 5 | KOSTT (grid EUR 29M), Mabetex |

**Total: 50 (anterior) + 84 (nou) = 134 constructori cu contacte**

### TASK 2: 5 campanii EBRD configurate pe raspibig (COMPLET)

| Tara | CSV rows | Sender | Daily | Path on raspibig |
|------|----------|--------|-------|------------------|
| Poland | 449 | buildjobs.eu (Brevo) | 50 | /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/EBRD/poland/ |
| Ukraine | 200 | factoryjobs.eu (Brevo) | 50 | .../EBRD/ukraine/ |
| Moldova | 500 | seicarescu.com (Brevo) | 50 | .../EBRD/moldova/ |
| Bulgaria | 195 | careworkers.eu (Brevo) | 50 | .../EBRD/bulgaria/ |
| Greece | 500 | warehouseworkers.eu (Brevo) | 50 | .../EBRD/greece/ |

**Toate `enabled: false` — asteapta aprobare Tudor.**
Template engleza (PL, UA, BG, GR) + romana (MD).

### TASK 3: Email Enrichment Script (COMPLET + RULAT)
- Script: `/opt/ACTIVE/EBRD/email_enrichment.py`
- **Rezultat RO:** 664 companii procesate, **297 emailuri noi gasite** (44.7%)
- Ruleaza cu: `python3 email_enrichment.py --country BG --limit 5000`
- 1 request/sec, respectful, commit la fiecare 100

### TASK 4: EBRD Procurement Monitor (COMPLET + CRON ACTIV)
- Script: `/opt/ACTIVE/EBRD/ebrd_procurement_monitor.py`
- Cron: zilnic 9:00 AM pe raspibig
- Monitorizeaza ecepp.ebrd.com + TED pt 17 tari target
- Alerte pe manpower.dristor@gmail.com

### D3: AgroEvolution Premium Listings (COMPLET)
- **Landing page LIVE:** agroevolution.com/premium.php
- Pricing: EUR 10/luna sau EUR 100/an
- Contact: WhatsApp + email, tema verde forest
- Campaign: 1,111 producatori Produs Montan, 100/zi, Brevo agroevolution
- Config: `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/agroevolution_premium.json`
- Template: `.../templates/agroevolution_premium/template1.txt`
- **enabled: false** — asteapta aprobare

### D4: Insolvency Alerts (COMPLET)
- **Landing page LIVE:** cifn.eu/alerte-insolventa.html + cifn.info
- Pricing: EUR 19/luna sau EUR 190/an
- Monitor cron: zilnic 7:00 AM, `/opt/ACTIVE/CIFN/insolvency_monitor.py`
- Subscribers: `/opt/ACTIVE/CIFN/subscribers.json`
- Campaign #1: 2,451 liquidatori, 50/zi, Brevo CIFN
- Campaign #2: 2,190 companii, 50/zi, Brevo CIFN
- **Ambele enabled: false** — asteapta aprobare

---

## CE ASTEAPTA APROBARE TUDOR

### Campanii de pornit (set `enabled: true` in JSON):

| # | Campanie | Contacte | Ritm | Config path |
|---|----------|----------|------|-------------|
| 1 | EBRD Romania constructori | 685 | 50/zi | /opt/.../ROMANIA/configs/ebrd_constructori.json |
| 2 | EBRD Poland | 449 | 50/zi | /opt/.../EBRD/poland/ebrd_poland.json |
| 3 | EBRD Ukraine | 200 | 50/zi | /opt/.../EBRD/ukraine/ebrd_ukraine.json |
| 4 | EBRD Moldova | 500 | 50/zi | /opt/.../EBRD/moldova/ebrd_moldova.json |
| 5 | EBRD Bulgaria | 195 | 50/zi | /opt/.../EBRD/bulgaria/ebrd_bulgaria.json |
| 6 | EBRD Greece | 500 | 50/zi | /opt/.../EBRD/greece/ebrd_greece.json |
| 7 | AgroEvolution premium | 1,111 | 100/zi | /opt/.../configs/agroevolution_premium.json |
| 8 | Insolventa liquidatori | 2,451 | 50/zi | /opt/.../configs/cifn_insolvency.json |
| 9 | Insolventa companii | 2,190 | 50/zi | /opt/.../configs/cifn_insolvency_companies.json |
| 10 | Agencies D2 | 18,133 | 500/zi | /opt/.../configs/recruitment_agencies.json |

### Actiuni manuale Tudor (35 min total):
1. Aproba 15 leaduri Telegram @raspi_n8n_alerts_bot (5 min)
2. Creeaza cont Gumroad/LemonSqueezy — 5 CSV-uri gata (15 min)
3. Aproba template agentii D2 (5 min)
4. Suna Toubeaux Delecroix +33 6 08 09 97 20 (10 min)

---

## PROPUNERI NEPORNITE (urmatoarea sesiune)

### P1. TED Winners Mega-Campaign — 370K emailuri, 27 tari
- DE 57K, FR 57K, ES 26K, PL 25K, SE 25K emailuri castigatori licitatii
- Template: "We supply skilled workers for EU procurement project execution"
- 5 sendere x 250/zi = 1,250/zi = 296 zile
- **Revenue:** La 1% raspuns = 3,700 contractori interesati

### P2. Accelereaza Norway — 314K emailuri, doar 972 trimise
- Creste de la 50/zi la 200-500/zi

### P3. France Companies — 29M companii, 529K contacte extrase
- Enrichment + campanie franceza

### P4. Master Emails Audit — 1.89M emailuri deduplicate
- Verifica ce contine, cate sunt fresh, cate folosite deja

### P5. Bilant Financiar Service — 2.87M bilantouri
- Verificare parteneri, due diligence, EUR 9/luna

### P6. ONRC Verification API — 4.14M companii
- Verificare firma activa/inactiva, EUR 5/check sau 49/luna

### P7. Procurement Intelligence — 5.14M licitatii + 6.2M premii
- "Cine castiga licitatii in sectorul tau?" EUR 29-99/luna

### P8. UK Companies — 5.67M
- Brexit, deficit muncitori, piata mare

### P9. Enrichment Masiv
- RO: 715K companii, 3.9% cu email → ruleaza enrichment
- MD: 1.06M, 0.8% cu email
- BG: 160K, 16%

### P10. Data Marketplace API
- 209M companii, 370K TED, 5M licitatii ca API EUR 99-999/luna

---

## BAZA DE DATE — SNAPSHOT

| Tabel | Randuri | Cu email | Obs |
|-------|---------|----------|-----|
| companies | 209,480,390 | ~440K | Master DB |
| companies_clean | 40,644,215 | ? | Deduplicate |
| fr_companies | 29,225,733 | ? | Franta |
| master_romania_companies | 8,936,353 | ~145K | RO master |
| ted_awards | 6,199,274 | ? | Premii TED |
| uk_companies | 5,679,440 | ? | UK |
| de_companies | 5,302,933 | ? | Germania |
| tenders | 5,144,446 | ? | Licitatii |
| ro_companies_onrc | 4,147,103 | ? | ONRC complet |
| procurement_awards | 3,460,984 | ? | Premii achizitii |
| bilant_years | 2,876,723 | — | Bilanturi RO |
| master_emails | 1,890,339 | 1.89M | Deduplicate |
| ted_winners | 1,568,685 | 370K | Castigatori TED |
| no_companies_full | 1,152,277 | 324K | Norvegia |
| insolvency | 1,033,537 | ~12K | Faliment RO |
| ebrd_projects | 4,176 | 1,486 | EBRD mondial |
| produs_montan_producers | 1,507 | 1,111 | Producatori montani |

## INFRASTRUCTURA ACTIVA

### Cron jobs pe raspibig:
- Email pipeline: la 2h
- Email poller: la 15min  
- Orchestrator: la 5min, ~3,600/zi
- EBRD PSD scraper: la 10min
- EBRD procurement monitor: zilnic 9:00 AM (NOU)
- Insolvency monitor: zilnic 7:00 AM (NOU)
- Zoho warmup: zilnic la miezul noptii
- Health check: la 1h

### Landing pages LIVE:
- agroevolution.com/premium.php (NOU)
- cifn.eu/alerte-insolventa.html (NOU)
- cifn.info/alerte-insolventa.html (NOU)
- expatsinromania.org/services/

### Email capacity: 6,300/zi
- Brevo: 2,984/zi (11 conturi)
- Mailrelay: 2,666/zi
- Gmail: 400/zi (13 conturi)
- Zoho: 100/zi (warming)
- Resend: 100/zi
- A2: 50/zi

---

## REGULI (din sesiunile anterioare)
- Max 250 linii/script
- NU trimite email fara aprobare Tudor
- Semnatura Tudor Seicarescu, reply-to manpower.dristor@gmail.com
- Corporate → Brevo/A2, personal → Gmail
- SSH raspibig: tudor@192.168.100.21 (key auth)
- A2: cPanel API only, NU SSH
- Salveaza pe disk la fiecare pas
- SCP pt transfer fisiere la raspibig (nu heredoc)
