# PROCEDURA — Trading Robot F&V

**Iulie 2026** · Scop: compari ofertele, nu le uiti, si potrivesti cererile clare
cu furnizori. Fara scoruri afisate. Niciun send fara aprobare numerotata.

## Principii
- Robotul **tine minte** tot (oferte + cereri) si **compara preturile**.
- Vointa (preturi Profi) = `internal_only` — referinta de pret, NU se revinde.
- Pornim mereu de la **cererile clare** (produs + tonaj + calitate + judet).
- Email numai ASCII. Leads keyed pe email non-null.

## Bucla de operare (repetabila)

1. **Aduna cererile** — `requests_ledger.jsonl` (cereri conserve) + cereri concrete
   cu tonaj. Sorteaza dupa claritate: cele cu produs+tonaj+calitate primele.

2. **Aduna ofertele** — `offers_ledger.jsonl`. Marcheaza `internal_only` ce e doar
   inteligenta de pret (Vointa). Restul = marfa reala.

3. **Compara pret** — `price_book.json`: min/avg/max per produs. Asta ramane viu,
   sa stim daca un pret e bun.

4. **Pentru fiecare cerere clara** → cauta in `suppliers_list.csv` furnizori care
   livreaza acel produs SI au email. Prioritate: acelasi judet > Romania > import.

5. **Draft cerere-de-oferta** (gated) catre furnizor: "ce pret/calitate/tonaj poti
   da pentru X?" ASCII. NU se trimite pana Tudor nu aproba (numar).

6. **Raspuns furnizor cu pret** → adauga in `offers_ledger` + update `price_book`
   (memoreaza). Acum avem oferta reala pentru acea cerere.

7. **Potriveste oferta cu cererea** → daca acopera (produs+calitate+tonaj+pret),
   pregateste draft intro/deal (gated) catre cumparator. Pragul de potrivire e
   intern in cod; NU se afiseaza scor.

8. **Inregistreaza** perechea cerere↔furnizor↔cumparator ca sa nu se piarda.
   Gol de aprovizionat (cerere fara furnizor contactabil) = task de gasit contact.

## Reguli de gating
- Pasii 5 si 7 produc DOAR drafturi. Send = aprobare numerotata explicita.
- Fara commit/push fara instructiune.
- Daca pornim trimiterea = inregistrare in dashboard 8096 + DNC unificat.

## Stare curenta (2026-06-30)
- Cereri clare cu tonaj: visine 100to (Buzau), ardei kapia 100to, vinete 60to,
  gogosari 100to (toate MIB/Buzau, industrial).
- Furnizori contactabili: visine→Partenope+Moldova; ardei/vinete→Bioprod/Hortifruct/Roua.
- Gol: gogosari (furnizorii Olt/Mures n-au email).
- Urmator pas: drafturi cerere-de-oferta (gated).
