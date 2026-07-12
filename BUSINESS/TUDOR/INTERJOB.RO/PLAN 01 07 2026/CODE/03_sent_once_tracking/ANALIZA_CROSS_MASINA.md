# Analiza dedup cross-masina (raspi + raspibig)

Masurat 2026-07-12, read-only pe teren (fara trimiteri, fara modificari de date).
Fara adrese individuale — doar numere.

## Context
Sent-tracking-ul e per-masina: ANOFM + DEFICIT trimit de pe **raspi** (.20),
restul campaniilor de pe **raspibig** (.21). DNC e mirror identic pe ambele
(`dnc_list.csv`=8498, `dnc_bounces.txt`=8582). DNC prinde doar bounce/opt-out,
NU si adresele deja contactate → golul e real.

## Ledger global (ambele masini)
- fisiere `sent.json` procesate: **50** (raspibig 46 + raspi 4)
- inregistrari vazute: **12.042**
- randuri unice in ledger: **10.925**
- emailuri unice in grupul `DEFICIT_JOBS`: **4.968**
- DNC unic: **8.526**

## Audiente DEFICIT pe raspi vs istoric global

| audienta (fisier) | total | in DNC | deja trimis (orice) | acelasi grup DEFICIT_JOBS | NOU |
|---|---:|---:|---:|---:|---:|
| audienta_nonyahoo_FULL50.csv | 480 | 0 | 195 | 188 | 285 |
| audienta_yahoo.csv | 149 | 0 | 4 | 4 | 145 |
| audienta_yahoo_1065.csv | 590 | 0 | 17 | 9 | 573 |
| audienta_yahoo_FULL50.csv | 213 | 0 | 13 | 5 | 200 |

(Numerele sunt per-fisier, cu suprapuneri intre fisiere.)

## Concluzie
- Trimiterea acestor audiente de pe raspi fara verificare cross-masina ar
  **recontacta sute de adrese** deja atinse de pe raspibig, majoritatea in
  **acelasi grup de subiect** (`DEFICIT_JOBS`).
- DNC (mirror-uit) NU acopera aceste dubluri (0 din audienta in DNC).
- Fix: ledger sent-once alimentat din **ambele** masini
  (`backfill_from_sentjson.py --base <raspibig> --base <raspi>`), apoi
  `filter_recipients.py` inainte de fiecare campanie.

## Note operationale
- Nu s-a trimis niciun email si nu s-a modificat niciun fisier pe servere.
- Listele "safe-to-send" (adrese ramase dupa filtrare) se genereaza local si
  **nu se comit** (contin date personale).
