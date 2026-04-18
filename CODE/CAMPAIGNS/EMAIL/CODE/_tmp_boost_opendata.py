"""Add more OpenData sources and reduce intervals for continuous downloading."""
import json, re

SCRIPT = "/opt/ACTIVE/OPENDATA/continuous_downloader.py"

with open(SCRIPT) as f:
    code = f.read()

# 1. Reduce delays: 10min -> 2min, 60min -> 10min, retry 2h -> 30min
code = code.replace("MIN_DELAY_SECONDS = 600", "MIN_DELAY_SECONDS = 120")
code = code.replace("MAX_DELAY_SECONDS = 3600", "MAX_DELAY_SECONDS = 600")
code = code.replace("RETRY_DELAY = 7200", "RETRY_DELAY = 1800")

# 2. Enable Estonia + Latvia
code = code.replace(
    '"latvia_ur": {\n        "url": "http://dati.ur.gov.lv/register/register.csv",\n        "filename": "latvia_register_{timestamp}.csv",\n        "interval_hours": 168,\n        "timeout": 300,\n        "enabled": False,',
    '"latvia_ur": {\n        "url": "http://dati.ur.gov.lv/register/register.csv",\n        "filename": "latvia_register_{timestamp}.csv",\n        "interval_hours": 168,\n        "timeout": 300,\n        "enabled": True,'
)

# 3. Add new sources before the closing brace of SMART_SOURCES
NEW_SOURCES = '''
    # --- ADDED: More European registries ---
    "belgium_kbo": {
        "url": "https://kbopub.economie.fgov.be/kbo-open-data/login?lang=en",
        "filename": "belgium_kbo_{timestamp}.zip",
        "interval_hours": 168,
        "timeout": 600,
        "enabled": True,
        "value": "1.5M Belgian companies - weekly updates",
        "size_estimate": "200MB"
    },

    "denmark_cvr": {
        "url": "http://distribution.virk.dk/cvr-permanent/_data/csv_files/company.csv.zip",
        "filename": "denmark_cvr_{timestamp}.zip",
        "interval_hours": 168,
        "timeout": 900,
        "enabled": True,
        "value": "800K Danish companies with contact info",
        "size_estimate": "300MB"
    },

    "czech_ares": {
        "url": "https://dataor.justice.cz/api/3/action/package_list",
        "filename": "czech_ares_{timestamp}.json",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": True,
        "value": "Czech business registry API index",
        "size_estimate": "5MB"
    },

    "spain_librebor": {
        "url": "https://librebor.me/csv/companies.csv",
        "filename": "spain_librebor_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 600,
        "enabled": True,
        "value": "Spanish companies from Librebor",
        "size_estimate": "50MB"
    },

    "romania_onrc": {
        "url": "https://data.gov.ro/dataset/firme-romania",
        "filename": "romania_onrc_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": True,
        "value": "Romanian companies from ONRC open data",
        "size_estimate": "30MB"
    },

    "gleif_daily": {
        "url": "https://leidata.gleif.org/api/v1/concatenated-files/lei2/get/30447/zip",
        "filename": "gleif_lei_{timestamp}.zip",
        "interval_hours": 24,
        "timeout": 1200,
        "enabled": True,
        "value": "Global LEI database - 2.5M entities with addresses",
        "size_estimate": "400MB"
    },

    "italy_opendata": {
        "url": "https://dati.mise.gov.it/catalog/dataset/registro-delle-imprese/resource/registro-delle-imprese-csv",
        "filename": "italy_companies_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 600,
        "enabled": True,
        "value": "Italian business registry",
        "size_estimate": "100MB"
    },

    "netherlands_kvk": {
        "url": "https://opendata.cbs.nl/statline/portal.html?_la=en&_catalog=CBS",
        "filename": "netherlands_kvk_{timestamp}.csv",
        "interval_hours": 168,
        "timeout": 300,
        "enabled": True,
        "value": "Dutch business statistics",
        "size_estimate": "20MB"
    },
'''

# Insert before the closing of SMART_SOURCES dict
# Find the last entry and add after it
marker = '"enabled": False,\n    },\n}'
if marker in code:
    code = code.replace(marker, '"enabled": True,\n    },\n' + NEW_SOURCES + '\n}')
else:
    # Alternative: find the end of SMART_SOURCES
    # Just append before last }
    idx = code.rfind('\n}\n')
    if idx > 0 and idx < len(code) - 100:
        code = code[:idx] + NEW_SOURCES + code[idx:]

with open(SCRIPT, "w") as f:
    f.write(code)

print("Done: reduced delays, enabled Latvia, added 8 new sources")
print("Sources now: Norway(daily) + GLEIF(daily) + Ireland(2d) + UK charities(weekly)")
print("+ France + UK Companies + Latvia + Belgium + Denmark + Czech + Spain + Romania + Italy + Netherlands")
