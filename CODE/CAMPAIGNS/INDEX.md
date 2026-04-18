# CAMPAIGNS INDEX

| File | Location | What it does |
|------|----------|--------------|
| primarii_campanie_enriched.csv | DATA/RO/ | Enriched Romanian city hall contacts with mayor names, emails, party affiliation |
| primarii_campanie.csv | DATA/RO/ | Base list of Romanian primarii (city halls) for campaign targeting |
| primarii_mayor_lookup.csv | DATA/RO/ | Mayor name lookup table keyed by CUI/locality |
| sicap_defrisare_leads.csv | DATA/RO/ | SICAP procurement leads: deforestation/tree-cutting contracts |
| primarii_parcuri.txt | TEMPLATES/RO/ | Email template for city halls — parks/green spaces pitch |
| furnizori_gazon_en.txt | TEMPLATES/B2B/ | English email template for synthetic grass suppliers |
| ebrd_template_ro.txt | TEMPLATES/EU/ | Romanian-language EBRD contractor outreach template |
| campaign_primarii.py | CODE/senders/ | Sends email campaign to primarii via Brevo API |
| sicap_monitor.py | CODE/scrapers/ | Monitors SICAP for new public procurement contracts |
| sicap_defrisare_monitor.py | CODE/scrapers/ | Monitors SICAP specifically for deforestation/arborist contracts |
| apm_defrisare_scraper.py | CODE/scrapers/ | Scrapes APM (Environmental Protection Agency) deforestation permit data |
| merge_primarii.py | CODE/enrichment/ | Merges multiple primarii data sources into unified CSV |
| scrape_primari.py | CODE/enrichment/ | Scrapes mayor names and contact info from primarie websites |
| scrape_partide.py | CODE/enrichment/ | Scrapes political party affiliation data for mayors |
| campaign_primarii.log | LOGS/ | Send log for primarii email campaign |
