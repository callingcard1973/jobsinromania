"""Add small/medium global sources to raspibig (laptop handles the big ones)."""

SCRIPT = "/opt/ACTIVE/OPENDATA/continuous_downloader.py"
with open(SCRIPT) as f:
    code = f.read()

NEW = '''
    # === AMERICAS (small sources, raspibig) ===
    "usa_sec_tickers": {
        "url": "https://www.sec.gov/files/data/company_tickers.json",
        "filename": "usa_sec_tickers_{timestamp}.json",
        "interval_hours": 168,
        "timeout": 120,
        "enabled": True,
        "value": "US SEC listed companies index",
        "size_estimate": "2MB"
    },
    "canada_federal": {
        "url": "https://ised-isde.canada.ca/site/corporations-canada/opendata/OPEN_DATA.csv",
        "filename": "canada_federal_{timestamp}.csv",
        "interval_hours": 720,
        "timeout": 600,
        "enabled": True,
        "value": "Canadian federal corporations",
        "size_estimate": "50MB"
    },
    "colombia_rues": {
        "url": "https://www.datos.gov.co/api/views/c762-zz4h/rows.csv?accessType=DOWNLOAD",
        "filename": "colombia_companies_{timestamp}.csv",
        "interval_hours": 720,
        "timeout": 600,
        "enabled": True,
        "value": "Colombian companies registry",
        "size_estimate": "40MB"
    },
    # === ASIA PACIFIC (small) ===
    "singapore_acra": {
        "url": "https://data.gov.sg/dataset/entities-with-uen",
        "filename": "singapore_acra_{timestamp}.csv",
        "interval_hours": 720,
        "timeout": 300,
        "enabled": True,
        "value": "Singapore registered entities",
        "size_estimate": "20MB"
    },
    "hongkong_cr": {
        "url": "https://data.gov.hk/en-data/dataset/hk-cr-cr-particulars-of-local-companies",
        "filename": "hongkong_cr_{timestamp}.csv",
        "interval_hours": 720,
        "timeout": 600,
        "enabled": True,
        "value": "Hong Kong company particulars",
        "size_estimate": "30MB"
    },
    "newzealand_nzbn": {
        "url": "https://catalogue.data.govt.nz/dataset/new-zealand-business-number-nzbn-data",
        "filename": "newzealand_nzbn_{timestamp}.csv",
        "interval_hours": 720,
        "timeout": 600,
        "enabled": True,
        "value": "New Zealand business numbers",
        "size_estimate": "25MB"
    },
    # === AFRICA/MIDDLE EAST ===
    "israel_companies": {
        "url": "https://data.gov.il/dataset/companies",
        "filename": "israel_companies_{timestamp}.csv",
        "interval_hours": 720,
        "timeout": 600,
        "enabled": True,
        "value": "Israeli companies registry",
        "size_estimate": "30MB"
    },
    "kenya_brs": {
        "url": "https://www.opendata.go.ke/Business/Business-Registration-Service/n2jz-ge4z",
        "filename": "kenya_brs_{timestamp}.csv",
        "interval_hours": 720,
        "timeout": 300,
        "enabled": True,
        "value": "Kenya business registrations",
        "size_estimate": "10MB"
    },
    # === GLOBAL ===
    "gleif_relations": {
        "url": "https://leidata.gleif.org/api/v1/concatenated-files/rr/get/30448/zip",
        "filename": "gleif_relations_{timestamp}.zip",
        "interval_hours": 168,
        "timeout": 900,
        "enabled": True,
        "value": "GLEIF parent-child company relationships",
        "size_estimate": "50MB"
    },
'''

# Insert before the closing } of SMART_SOURCES
# Find the last source entry closing and add after
marker = '\n}\n\n\ndef load_state'
if marker in code:
    code = code.replace(marker, NEW + '\n}\n\n\ndef load_state')
else:
    marker2 = '\n}\n\ndef load_state'
    if marker2 in code:
        code = code.replace(marker2, NEW + '\n}\n\ndef load_state')

with open(SCRIPT, "w") as f:
    f.write(code)

print("Added 9 global sources to raspibig")
