#!/usr/bin/env python3
"""Test spec extraction."""
import requests
requests.packages.urllib3.disable_warnings()
from parsers import parse_anunt

r = requests.get("https://beneficiar.fonduri-ue.ro:8080/anunturi/details/2/51957/", verify=False, timeout=30)
d = parse_anunt(r.text, 51957)
print("Email:", d["email"])
print("Descriere:", d["descriere"][:150])
print("Spec URL:", d["spec_url"])
print("Spec text (%d chars):" % len(d["spec_text"]), d["spec_text"][:400])
