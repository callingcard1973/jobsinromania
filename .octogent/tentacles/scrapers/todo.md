# Todo

## EU Funding — Campaign Integration

### beneficiari_privati → campaigns pipeline
- **Task:** `beneficiari_privati` table has ~48,000 records with CUI, phone, email, contact name, county, budget. These are private companies that won EU funding and must publish procurement notices — they are prime subcontractor/supplier leads.
- **Action needed:** Cross-ref CUIs against enrichment pipeline, then feed emails into a Brevo campaign variant targeting EU-funded private beneficiaries (similar to EBRD campaign structure).
- **Files:** `SCRAPER_beneficiar.fonduri-ue/CODE/async_scraper.py`, table `interjob_master.beneficiari_privati`

### PNRR scraper — resume and complete
- **Task:** `scrape_distributed.py` stopped at page 1000/~20000 on the forwards run. Backwards run from raspibig status unknown. ~10,000 records remain unscraped.
- **Action needed:** SSH to raspi, check `PNRR/distributed_state.json`, resume with `bash /opt/ACTIVE/EU_FUNDING/PNRR/run_forwards.sh`. Then check raspibig backwards state.
- **Files:** `PNRR/scrape_distributed.py`, `PNRR/run_forwards.sh`, `PNRR/distributed_state.json`

### PNRR table → campaigns pipeline
- **Task:** Once PNRR scrape is complete, PNRR project beneficiaries (companies with SMIS codes, operational program names) are high-value targets for subcontracting/staffing outreach.
- **Action needed:** Confirm DB table name for PNRR on raspibig, enrich CUIs, add to campaign pipeline.
