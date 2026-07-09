# Lista ONG Romania

## Sursa oficiala principala

Registrul oficial este publicat de Ministerul Justitiei:

- Pagina registrului: https://www.just.ro/registrul-national-ong/
- Registrul este prezentat separat pentru: Asociatii, Fundatii, Federatii, Uniuni, Persoane juridice straine.
- Fisierele `.xlsx` sunt actualizate saptamanal si sunt cea mai practica sursa pentru export si filtrare.

Conform paginii oficiale, fisierele `.xlsx` contin cel putin urmatoarele campuri:

- Denumire
- Numar de inregistrare in Registrul National
- Starea actuala
- Judet
- Localitate
- Adresa
- Lista de asociati/fondatori
- Scopul initial si modificarile scopului
- Consiliu director / organ de conducere
- HG utilitate publica si data HG

## Linkuri utile din registru

Pe pagina Ministerului Justitiei sunt publicate direct fisiere pentru:

- Asociatii (`.xlsx` / `.pdf`)
- Fundatii (`.xlsx` / `.pdf`)
- Federatii (`.xlsx` / `.pdf`)
- Uniuni (`.xlsx` / `.pdf`)
- Persoane juridice straine (`.xlsx` / `.pdf`)

Observatie: linkurile fisierelor se schimba la fiecare actualizare saptamanala, deci sursa stabila este pagina registrului, nu URL-ul punctual al fisierului.

## Sursa secundara utila

Pe data.gov.ro exista seturi de date de la Ministerul Finantelor cu fisiere dedicate ONG-urilor in cadrul situatiilor financiare anuale.

Exemplu validat:

- https://data.gov.ro/dataset/situatii_financiare_2015
- resurse relevante: `WEB_ONG_2015.csv`, `web_ong_2015.txt`, `WEB_ONG_AN2015.txt`

Aceste fisiere sunt utile pentru:

- selectie dupa activitate financiara
- filtrare dupa indicatori economici
- prioritizare comerciala

Dar nu inlocuiesc Registrul National ONG de la Ministerul Justitiei.

## Recomandare practica

Pentru o lista de lucru nationala:

1. Foloseste Registrul National ONG de la Ministerul Justitiei ca baza principala.
2. Descarca fisierele `.xlsx` pentru Asociatii, Fundatii, Federatii si Uniuni.
3. Normalizeaza coloanele `judet`, `localitate`, `denumire`, `stare`, `adresa`.
4. Daca vrei prioritizare comerciala, le unesti ulterior cu datele financiare ONG din data.gov.ro.

## Fisiere generate in workspace

- `ONG_REGISTRU_NATIONAL.csv` - export unificat din registrele oficiale `.xlsx`
- `ONG_ACTIVE.csv` - doar ONG-urile active, utile pentru lucru comercial
- `ONG_SUMAR_JUDETE.csv` - sumar total/active/inactive pe judet si categorie
- `ONG_SUMAR_LOCALITATI.csv` - sumar ONG-uri active pe judet si localitate
- `ong_pe_judete/` - fisiere separate pe judet, doar cu ONG-uri active
- `generate_ong_registry.py` - script reutilizabil pentru refacerea CSV-ului dupa fiecare actualizare saptamanala a registrului
- `ONG_SHORTLIST_5000.csv` - shortlist comercial automat din ONG-urile active
- `ONG_SHORTLIST_5000_SUMAR.md` - sumarul shortlist-ului si al euristicii de prioritizare
- `generate_ong_shortlist.py` - script reutilizabil pentru generarea shortlist-ului comercial

## Concluzie

Daca cerinta este "lista ONG Romania", cea mai buna sursa publica si oficiala este Registrul National ONG al Ministerului Justitiei.