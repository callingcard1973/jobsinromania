# HANDOFF — Bogdan Gavra Project
**Data:** 2026-04-18

---

## Ce s-a construit azi

### Linii de business
| Linie | Status | Revenue estimat |
|-------|--------|-----------------|
| Parcuri copii primării (AVP Park) | LIVE — campanie pornește luni | €3K-25K/proiect |
| Compensare CO2 / plantare arbori | LIVE — pagina + lead activ 1M RON | 200-400 RON/arbore |
| Gazon sintetic terenuri sport | În negociere — 3 emailuri trimise | €9K-16K/teren |

---

## Acțiuni imediate

### 🔴 Urgent — CN1091634
**Licitație activă: plantare arbori + reabilitare terenuri, 1,008,404 RON, deadline 25.05.2026**
- URL: https://sicap.pro/anunturi/CN1091634
- Bogdan trebuie să depună ofertă

### 🟡 Săptămâna aceasta
1. **ISCIR autorizare instalare** — fără asta nu poate câștiga licitații SICAP pentru parcuri
2. **Telegram chat_id** — trimite-l pentru alertele SICAP (sicap_monitor.py)
3. **Răspunsuri furnizori gazon** — Nurteks răspunde în 24-48h

---

## Ce rulează automat (luni 08:00)

| Script | Ce face |
|--------|---------|
| `campaign_primarii.py` | 100 emailuri/zi către primării — catalog PDF atașat |
| `sicap_monitor.py` | Alerte parcuri copii CPV 37535200 |
| `sicap_monitor_gazon.py` | Alerte gazon sintetic — 3,000 licitații în DB |
| `sicap_defrisare_monitor.py` | Alerte defrișare CPV 77211400 |
| `apm_defrisare_scraper.py` | Avize APM tăiere arbori |

---

## Pagini LIVE pe agroevolution.com

- **Parcuri copii:** https://agroevolution.com/index.php/spatii-verzi/
- **Plantare arbori / CO2:** https://agroevolution.com/index.php/plantare-arbori/

---

## Structură fișiere

```
D:\MEMORY\BUSINESS\BOGDAN GAVRA\
├── DATA\        — CSV-uri primării (3,027 emailuri) + leads SICAP
├── CODE\        — scripturi Python (campanie + monitoare SICAP)
├── TEMPLATES\   — emailuri gata de trimis
├── DOCS\        — research gazon, CO2, SICAP
├── CATALOGS\    — catalog_parcuri.pdf + .html
└── LOGS\        — loguri rulări
```

---

## Reguli importante
- Comunicare externă: **Tudor Seicărescu / AgroEvolution** — niciodată Bogdan sau HYPER BNDF
- Nu se menționează AVP Park în emailuri către terți
- Sender campanie: office@buildjobs.eu | Reply-To: tudor@agroevolution.com

---

## Furnizori gazon contactați azi
| Furnizor | Email | Status |
|----------|-------|--------|
| Nurteks (TR) | export@nurteks.com.tr | ✅ Trimis 2026-04-18 |
| CCGrass (CN) | sales@ccgrass.com | ✅ Trimis 2026-04-18 |
| Hatko Sport (TR) | info@hatkosport.com | ✅ Trimis 2026-04-18 |
