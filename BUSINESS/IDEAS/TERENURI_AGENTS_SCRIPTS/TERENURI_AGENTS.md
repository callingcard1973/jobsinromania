# IDEA-056: Terenuri / Ferme / Lichidari — 10 Agenti Automatizati

## Concept
Sistem automat de detectare chilipiruri imobiliare din surse publice romanesti.
Scraping + analiza pret + geo + juridic + alerte timp real.

## Surse de date
- **OLX** — scraping (fara API oficial)
- **Imobiliare.ro** — scraping
- **Storia.ro** — scraping
- **ANAF executari silite** — https://www.anaf.ro/licitatii/
- **BPI** (Buletinul Procedurilor de Insolventa) — bpi.ro
- **Primarii** — site-uri individuale
- **ANCPI/eTerra** — verificare CF
- **MADR** — date agricole (scraper existent pe raspibig)

## Agentii

### 1. Listing Hunter (baza sistemului)
- Scaneaza: OLX, Imobiliare.ro, Storia, executari ANAF
- Filtreaza: "urgent", "lichidare", "sub pret piata"
- Output: lista zilnica "posibile chilipiruri"
- Cron: zilnic 6 AM + 18 PM

### 2. Price Anomaly Detector
- Compara: pret/mp vs zona
- Detecteaza: "prea ieftin ca sa fie normal"
- Exact ca la zboruri dar mai profitabil
- Foloseste: mediana pret/mp pe localitate din anunturi colectate

### 3. Geo Intelligence Agent
- Foloseste: coordonate + harta
- Verifica: apropiere oras, drumuri, utilitati
- "Ieftin" in mijlocul pustietatii = capcana
- API: OpenStreetMap Nominatim (gratuit) + distanta la drum national

### 4. Legal Risk Scanner
- Cauta: litigii, executari, probleme juridice
- Surse: portal.just.ro, BPI, ANAF datornici
- Cross-match CUI/CNP cu liste insolventa (222K in DB)
- Diferenta dintre profit si cosmar

### 5. Development Potential Agent
- Analizeaza: teren agricol vs intravilan
- Posibilitate constructie (PUG/PUZ zona)
- Transforma: teren ieftin → oportunitate mare
- Surse: primarii + ANCPI categorii

### 6. CMA Agent (Comparative Market Analysis)
- Compara cu: vanzari similare in zona
- Estimeaza: pret real vs pret cerut
- Mini-evaluator automat
- Baza: istoric anunturi colectate de Agent 1

### 7. Resale Opportunity Detector
- Detecteaza: ce poti cumpara si revinde rapid
- Flip-uri cu date, nu feeling
- Scor: (pret piata estimat - pret cerut) / pret cerut > 30% = oportunitate

### 8. Deal Alert Agent
- Trimite: "teren sub 50% din pret piata" in timp real
- Telegram instant + email
- Viteza = avantaj

### 9. Seller Motivation Analyzer
- Analizeaza textul anuntului cu LLM (Qwen)
- Detecteaza: "urgent", "plec din tara", "lichidare", "pret negociabil", "accept orice oferta"
- Astea sunt aur — vanzator motivat = pret mai mic

### 10. Portfolio Builder Agent
- Tine evidenta oportunitatilor salvate
- Scoruri agregate (pret + geo + legal + potential)
- Prioritizeaza ce merita urmarit
- Dashboard pe raspibig (Node-RED sau HTML)

## Arhitectura

```
OLX + Imobiliare + Storia + ANAF + BPI
              |
         [1. Listing Hunter] — cron 2x/zi
              |
    +---------+---------+
    |         |         |
[2. Price] [3. Geo] [4. Legal]
    |         |         |
    +----+----+----+----+
         |
   [5. Development] + [6. CMA]
         |
   [7. Resale Detector]
         |
   [8. Deal Alert] → Telegram
         |
   [9. Seller Motivation] — LLM Qwen
         |
   [10. Portfolio] → Dashboard
```

## Ce exista deja
- **MADR scraper** — ruleaza pe raspibig, date teren agricol
- **AgroEvolution map** — 9,469 listings geocoded
- **Insolventa DB** — 222K records in PostgreSQL
- **BPI monitor** — bpi_monitor.py exista
- **ANAF datornici** — 44K companii
- **land_alerts_v2.py** — cron 4h pe raspibig (MADR)
- **Telegram alerts** — infrastructura existenta

## Implementare
- Agent 1 (Hunter) + 8 (Alert) + 9 (Motivation): prioritate maxima
- Agent 2 (Price) + 6 (CMA): dupa ce ai date (2-3 saptamani colectare)
- Agent 3 (Geo) + 4 (Legal) + 5 (Development): imbogatire pe masura ce vine data
- Agent 7 (Resale) + 10 (Portfolio): dupa ce pipeline-ul produce
