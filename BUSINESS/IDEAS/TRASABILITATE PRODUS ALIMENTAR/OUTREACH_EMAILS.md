# Outreach Emails — Trasabilitate Platform

## Segment 1: HYPERMARKET AGGREGATION (Priority 1-2, HIGH HM)

**Targets**: Péter Miklo, Péter Tankó, Montlact, Zsolt Papp, Afin Fruct, Mister Juice (6 producers, 7.6K kg/month)

**Email Template**:

---

**Subject: Brânza ta la Kaufland? Hai cu noi + Gospodarii de Altadata**

Salut [Nume],

Am văzut răspunsul tău din ianuarie (când am cerut brânza pentru francezi). De atunci am înregistrat o cooperativă, **Gospodarii de Altadata**, care agrégă producători montan ca tine și le vinde la hypermarketuri.

**Problema ta**: Kaufland zice "vreau brânza ta, dar cu HACCP + batch trace" și tu spui "eu nu am timp pentru asta".

**Soluția noastră**: Trasabilitate platform (https://trasabilitate.agroevolution.com/) care ține evidența electronică:
- Batch ID + QR code per lot
- Ingrediente + furnizori
- HACCP zilnic (temperatură, aspect)
- Vânzare / transport / verificări

Hypermarket scanează QR → vede tot. Tu doar: "batch creat, muta aici, temperatura 4°C" (5 minute).

**Cost**: EUR 100-300/month (depinde de volum). Cooperative plătește + negoțiază cu Kaufland.

**Cum merge practic**:
1. Eu deploy platform (1 săptămână)
2. Tu testezi cu 3 loturi (gratis)
3. Hypermarket acceptă (contract)
4. Tu plătești EUR 100/month, eu țin sistemul
5. Cooperative face EUR 1,000+ pe asta pe lună (15-20% margin)

Interesează? Zii.

[Semnătură]

---

## Segment 2: EU EXPORT (HIGH EXP POTENTIAL)

**Targets**: Stupina Igna, Mierecarpatica, Godeanu Stefan, Cristian Pop, Lili Dirnu, Zsolt Papp, Afin Fruct, Mister Juice, Niculesenciuc (9 producers, 8.2K kg/month)

**Email Template**:

---

**Subject: Miere din Carpați → Milano. Cu trasabilitate + EU compliance.**

Salut [Nume],

Știu că vinzi miere (sau ...)în România. Știu că ai calitate, certificări, și că ai încercat să vânzi în străinătate.

Problema: importatorul italian cere:
- "Cine-i furnizorul laptelui ?" → "Cine-i furnizorul zahărului?" → trace backwards
- Certificatoare per lot
- HACCP logs
- "Pdn't lose it" (= movement log din fermă la port)

Și asta îți ia 20 ore / lot. Iar daca-i pentru 100 kg, nu merită.

**Noi oferim**: Sistem unde:
- Scanezi QR pe etichetă
- Apelis PDF-urile de certificare + supplier certs
- Importatorul vede timeline complet (farm → packaging → shipping → port)
- Totul în 10 minute

Importatorii plătesc mai bine (10-20% premium) dacă au proof de compliance. You get EUR 800-2000 pe lot, vs EUR 500-1000 acum.

**Cost**: EUR 200-500/month. Dar daca exporți 2-3 loturi/luna, ROI e in 1 luna.

**Next step**: Sun-te week viitoare. Trebuie să mă gândesc sa te ghidez pe EU documentation (adresa, EAN, etc).

Sunt gata?

[Semnătură]

---

## Segment 3: LOCAL / RESTAURANT / AIRBNB (LOW PRIORITY)

**Targets**: Nicolae Aga, Gheorghe Balteanu, Ovidiu Hura (optional for others) (priority 4-5, willing but lower volume)

**Email Template**:

---

**Subject: Airbnb host? Restaurant? Trasabilitate te face "premium"**

Salut [Nume],

Dacă vânzi brânza / miere / fructe pe piață locală = nu-ți trebuie. Reputația face treaba.

DAR, dacă vânzi către:
- Restaurant (care trebuie să dovedească HACCP la inspector)
- Airbnb / cazare (care vrea "produs curat, certificat")
- Bio shop (care vrea să-și promoveze că e transparent)

Atunci trasabilitate e quick win. Adaugi 10-15% pe preț și gata.

**Sistem**: Same ca mai sus, dar 10 minute/luna.
**Cost**: EUR 80-150/month
**Uplift**: +EUR 150-300/month pe restaurantul care acceptă.

Interesează? (Low priority, doar dacă ești pasionat de vânzări cu valoare adaugată).

[Semnătură]

---

## IMPLEMENTATION TIMELINE

```
Week 1-2: Deploy PostgreSQL + Flask dashboard on raspibig
Week 3:   Testing + pilot with Miklo / Tankó
Week 4:   Kaufland contact + proof-of-concept
Week 5:   Launch Segment 1 email (6 producers)
Week 6:   Launch Segment 2 email (9 producers)
Week 7-8: Onboarding + training
Month 2:  Revenue tracking
```

## EXPECTED OUTCOMES

| Segment | Targets | Adoption | Monthly Revenue |
|---------|---------|----------|-----------------|
| Hypermarket (1-2) | 6 | 80% = 5 producers | EUR 1,500-1,500 |
| Export (HIGH EXP) | 9 | 60% = 5 producers | EUR 2,000-2,500 |
| Local (4-5) | 10 | 20% = 2 producers | EUR 200-300 |
| **TOTAL** | 25 | **50% = 12 producers** | **EUR 3,700-4,300/month** |

---

## FOLLOW-UP SEQUENCE

**If no response in 5 days**: Follow-up 1 (Thursday)
```
Salut [Nume], just checking if you got my email about Trasabilitate platform.
Any Q? Can call. —
```

**If no response in 5 more days**: Follow-up 2 (Phone call)
- Direct call, brief pitch, offer demo

**If interested**: Zoom demo (15 min) showing:
1. Dashboard with real batch data
2. QR scan → full trace
3. PDF export
4. How Hypermarket uses it

**If signed**: Setup (1 hour) + 3 free batches
