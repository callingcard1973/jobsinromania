#!/usr/bin/env python3
import requests
requests.packages.urllib3.disable_warnings()
r = requests.get("https://beneficiar.fonduri-ue.ro:8080/dwl-spec?ann=51950&lot=67929", verify=False, timeout=60)
print("Type:", r.headers.get("content-type"))
print("Disposition:", r.headers.get("content-disposition"))
print("Size:", len(r.content), "bytes")
print("Magic:", r.content[:4])

from parsers import fetch_spec
url, text = fetch_spec(51950, 67929)
print("Text (%d chars):" % len(text), text[:300])
