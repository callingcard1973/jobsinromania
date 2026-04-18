# INVENTAR — Sistem unic de inventariere IDEAS

## Fisiere
- **MASTER.csv** — Singurul fisier care conteaza. Toate ideile, codul, datele, statusul.
- **scan.py** — Scaneaza directoarele, compara cu MASTER.csv, raporteaza lipsuri.
- **ARHIVA/** — Inventarele vechi (martie-aprilie 2026). Nu le mai edita.

## Coloane MASTER.csv
| Coloana | Ce inseamna |
|---------|-------------|
| ID | IDEA-001 pana la IDEA-NNN |
| Proiect | Nume scurt |
| Categorie | CAMPANIE / PRODUS / DATE / CERCETARE / REFERINTA / PERSONAL / PARTENERIAT |
| Tip | cod / scraper / date / plan |
| Fisier | Fisierul principal sau directorul |
| Ce_face | Descriere scurta in romaneste |
| Status | ACTIV / GATA / INGHETAT / PLANIFICAT / CERCETARE / UCIS |
| Venit_EUR | Estimare venit (one-shot sau /luna sau /an) |
| Efort_ore | Ore de munca estimate |
| Actualizare | Data ultimei actualizari YYYY-MM-DD |

## Reguli
1. Orice idee noua primeste urmatorul ID liber
2. Orice cod/date noi se adauga in MASTER.csv
3. Status se actualizeaza cand se schimba ceva
4. Ruleaza `python scan.py` sa vezi ce lipseste
5. Sincronizeaza cu raspibig dupa orice modificare:
   ```bash
   scp -r D:/MEMORY/IDEAS/INVENTAR/ tudor@192.168.100.21:/opt/ACTIVE/IDEAS/INVENTAR/
   ```

## Status posibile
- **ACTIV** — se lucreaza sau ruleaza
- **GATA** — pregatit de lansare, asteapta decizie Tudor
- **PLANIFICAT** — ideea exista, codul nu
- **CERCETARE** — in investigare
- **INGHETAT** — valid dar blocat pe ceva extern
- **UCIS** — nu se mai face
