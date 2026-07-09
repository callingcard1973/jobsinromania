# Colectare pe Judete si Orase

## Fisiere de lucru

- `JUDETE_ORASE_RO.csv` contine toate judetele si orasele prioritare.
- Acest fisier descrie cum se colecteaza sursele publice pentru fiecare judet si oras.

## Ordine recomandata de lucru

1. Bucuresti
2. Ilfov
3. Cluj
4. Timis
5. Iasi
6. Constanta
7. Brasov
8. Prahova
9. Dolj
10. restul judetelor

## Pentru fiecare judet

Colecteaza minimum aceste puncte:

1. Primaria municipiului resedinta de judet
2. Consiliul Judetean
3. Compartimentul sau serviciul pentru asociatii de proprietari
4. Directia de locuinte, patrimoniu sau reabilitare termica
5. PDF-uri, XLS-uri si anexe HCL cu blocuri sau asociatii

## Pentru fiecare oras prioritar

Cauta dupa urmatoarele expresii:

- `"asociatii de proprietari" + nume oras + filetype:xls`
- `"asociatii de proprietari" + nume oras + filetype:pdf`
- `"lista asociatiilor de proprietari" + nume oras`
- `site:primarie + nume oras + asociatii de proprietari`
- `site:gov.ro + nume oras + asociatii de proprietari`
- `reabilitare termica + nume oras + blocuri + xls`

## Ce campuri sa extragi

- judet
- localitate
- nume_asociatie
- adresa
- bloc_scara
- administrator
- telefon
- email
- sursa_url
- tip_sursa
- data_document
- observatii

## Tipuri de surse utile

- lista asociatii de proprietari
- lista administratori condominii
- program reabilitare termica
- anexa HCL cu blocuri sau condominii
- liste de debite sau subventii publice
- registre de corespondenta pentru asociatii

## Status recomandat la colectare

- `de cautat`
- `sursa gasita`
- `extras partial`
- `extras complet`
- `fara rezultat public`

## Observatie importanta

In multe orase nu vei gasi un tabel numit exact `asociatii de proprietari`.
Cele mai bune rezultate apar in documente conexe:

- reabilitare termica
- lucrari pe blocuri
- repartizare ajutoare sau subventii
- evidenta administratorilor
- hotarari locale cu anexe

## Pasul urmator recomandat

Incepe cu:

1. Bucuresti pe sectoare
2. Ilfov
3. Cluj-Napoca
4. Timisoara
5. Iasi

Aceste zone au cea mai mare densitate de condominii si cele mai multe sanse de publicare online.