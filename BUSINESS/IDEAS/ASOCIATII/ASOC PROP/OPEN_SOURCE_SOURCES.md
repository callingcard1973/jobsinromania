# Surse Open/Public pentru Asociatii de Proprietari din Romania

## Concluzie rapida

Nu am gasit un registru national unic, open-source sau open-data, cu toate asociatiile de proprietari din Romania.

Am gasit insa surse partiale sau reutilizabile public:

1. `data.gov.ro` are seturi open-data pe zona de locuinte si blocuri, dar nu un registru complet de asociatii de proprietari.
2. `fapr.ro` exista ca sursa publica de ecosistem si federatie, utila pentru puncte de intrare institutionale.
3. Multe primarii si sectoare publica local PDF/XLS/PDF scanat cu asociatii, administratori, blocuri sau liste conexe.
4. Registri comerciali/open-company pot ajuta prin filtrare dupa denumiri de forma `ASOCIATIA DE PROPRIETARI`, dar nu am confirmat un export anonim, national, direct utilizabil.

## Ce am validat

### 1. Portalul national de open data

URL: https://data.gov.ro/

Observatii:
- Cautarea exacta pentru `"asociatii de proprietari"` nu a returnat seturi dedicate.
- Cautarea larga dupa `proprietari` a returnat doar seturi conexe pe zona de locuinte.
- Exemplu validat: setul `reab-termica-2016`, cu licenta `OGL-ROU-1.0`.

Exemplu resursa:
- https://data.gov.ro/dataset/reab-termica-2016

Utilitate:
- buna pentru liste de blocuri si programe de reabilitare
- slaba pentru o baza directa de lead-uri cu asociatii

### 2. Federatia Asociatiilor de Proprietari din Romania

URL: https://fapr.ro/

Utilitate:
- buna ca sursa de retea institutionala
- utila pentru identificarea federatiilor membre, contacte si eventuale asociatii afiliate
- nu este, in forma actuala, o baza open-data nationala gata de import

### 3. Surse locale care merita colectate oras cu oras

Tipuri de surse publice de urmarit:
- primarii de municipii si orase
- sectoarele din Bucuresti
- directii de taxe si impozite locale
- compartimente de relatii cu asociatiile de proprietari
- programe locale de reabilitare termica

Tipuri de fisiere intalnite frecvent:
- PDF cu liste de asociatii
- XLS/XLSX cu administratori sau blocuri
- anexe la hotarari de consiliu local
- tabele cu restanti, reabilitare, subventii sau repartizare pe condominii

## Ce NU am validat ca sursa open utilizabila imediat

### OpenCorporates

Am testat API-ul public pentru cautari de forma `ASOCIATIA DE PROPRIETARI` in Romania.

Rezultat:
- API-ul a raspuns cu `Invalid Api Token`

Concluzie:
- sursa poate fi utila doar cu acces API valid
- nu o consider in acest moment sursa open, anonima, gata de folosit

## Recomandare pragmatica

Cea mai realista varianta pentru o baza de date de vanzari este una hibrida:

1. colectare open/public din surse locale ale primariilor
2. extragere entitati dupa pattern-uri de nume `ASOCIATIA DE PROPRIETARI`, `ASOC. PROP.`, `ASOCIATIA LOCATARILOR`
3. normalizare pe judet, localitate, strada, nume asociatie, eventual CUI
4. imbogatire manuala sau semi-automata cu telefon, email, administrator

## Verdict

Exista `surse open/public`, dar nu am validat o `baza nationala open-source completa` gata de descarcat.

Cea mai buna baza initiala, fara cost, va veni din:
- `data.gov.ro` pentru seturi conexe pe blocuri/locuinte
- `fapr.ro` pentru intrari institutionale
- surse locale ale primariilor, colectate sistematic