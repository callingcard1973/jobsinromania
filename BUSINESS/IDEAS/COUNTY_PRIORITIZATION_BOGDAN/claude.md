# IDEA-151: County Prioritization for Bogdan
SQL: cross-ref primarii_campanie_enriched.csv cu contracte SICAP trecute din seap_romania_construction.csv.
Identifica judete care AU cumparat echipamente joaca -> probabilitate mai mare de repetare.
Filtreaza si dupa partid_primar (PSD/PNL coalition = mai deschisi la infrastructura).
Output: CSV primarii prioritizate cu scor 1-3.
