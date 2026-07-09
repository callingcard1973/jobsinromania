## Data Extraction Log (2026-04-02)
- Extracted all leads from cifn.eu (constructii, echipamente, servicii, altele)
- Cleaned and deduplicated: 280 unique rows
- Normalized budgets (float), standardized county names
- Output file: cifn_eu_leads_clean.csv (see workspace)

Sample rows:
category,company,project_title,budget,county
constructii,Licitatie restransa atribuire contract lucrari de constructii in cadrul proiectului Construire imobil cu apartamente destinate cazarii de sc,"Anunturi [proceduri de achizitie, beneficiari privati]: Licitatie restransa atribuire contract lucrari de constructii in cadrul proiectului Construire imobil cu apartamente destinate cazarii de scurta durata, imprejmuire si racorduri la utilitati",1706854.0,Neamt
constructii,executia de lucrari si furnizarea de echipamente pentru proiectul cu titlul Imbunatatirea infrastructurii,"Anunturi [proceduri de achizitie, beneficiari privati]: Proiectarea, executia de lucrari si furnizarea de echipamente pentru proiectul cu titlul Imbunatatirea infrastructurii in banda larga si a accesului la internet in judetul Alba",14971255.37,Bucuresti
constructii,Lucrari de constructii si instalatii pentru realizare spatiu necesar pentru prestarea activitatii,"Anunturi [proceduri de achizitie, beneficiari privati]: Procedura de atribuire a contractului de lucrari de constructie: Lucrari de constructii si instalatii pentru realizare spatiu necesar pentru prestarea activitatii de realizarea soft la comanda",5159938.78,Covasna
