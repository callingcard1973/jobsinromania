"""Remove from raspibig sources that laptop now handles."""
import re

SCRIPT = "/opt/ACTIVE/OPENDATA/continuous_downloader.py"
with open(SCRIPT) as f:
    code = f.read()

# Disable france_sirene_units (laptop handles france)
code = code.replace(
    '"france_sirene_units": {\n        "url": "https://object.files.data.gouv.fr/data-pipeline-open/siren/stock/StockUniteLegale_utf8.zip",\n        "filename": "france_sirene_units_{timestamp}.zip",\n        "interval_hours": 720,\n        "timeout": 1800,\n        "enabled": True,',
    '"france_sirene_units": {\n        "url": "https://object.files.data.gouv.fr/data-pipeline-open/siren/stock/StockUniteLegale_utf8.zip",\n        "filename": "france_sirene_units_{timestamp}.zip",\n        "interval_hours": 720,\n        "timeout": 1800,\n        "enabled": False,  # laptop handles france'
)

# Disable romania (laptop has direct ONRC CSV links)
code = code.replace(
    '"romania_onrc": {\n        "url": "https://data.gov.ro/dataset/firme-romania",\n        "filename": "romania_onrc_{timestamp}.csv",\n        "interval_hours": 168,\n        "timeout": 300,\n        "enabled": True,',
    '"romania_onrc": {\n        "url": "https://data.gov.ro/dataset/firme-romania",\n        "filename": "romania_onrc_{timestamp}.csv",\n        "interval_hours": 168,\n        "timeout": 300,\n        "enabled": False,  # laptop has direct ONRC CSVs'
)

# Disable italy (no real bulk download exists)
code = code.replace(
    '"italy_opendata": {\n        "url": "https://dati.mise.gov.it/catalog/dataset/registro-delle-imprese/resource/registro-delle-imprese-csv",\n        "filename": "italy_companies_{timestamp}.csv",\n        "interval_hours": 168,\n        "timeout": 600,\n        "enabled": True,',
    '"italy_opendata": {\n        "url": "https://dati.mise.gov.it/catalog/dataset/registro-delle-imprese/resource/registro-delle-imprese-csv",\n        "filename": "italy_companies_{timestamp}.csv",\n        "interval_hours": 168,\n        "timeout": 600,\n        "enabled": False,  # no real bulk download'
)

with open(SCRIPT, "w") as f:
    f.write(code)

print("Raspibig: disabled france/romania/italy (laptop handles or no real source)")
