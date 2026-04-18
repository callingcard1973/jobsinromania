#!/usr/bin/env python3
"""Patch send_campaign.py to add personalization variables."""
import re

f = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py"
code = open(f).read()

old = """    for old, new in [
        ('{company_name}', company), ('{company}', company), ('{name}', name),
        ('{email}', email_addr), ('{city}', city), ('{county}', county),
        ('{employees}', emp), ('{sector_name}', sector_name),
        ('{org_number}', org),
        ('{unsubscribe_url}', f"https://interjob.ro/unsubscribe.php?email={email_addr}"),
    ]:
        subject = subject.replace(old, new)
        body = body.replace(old, new)"""

new = """    # Personalization helpers
    contact_p = str(contact.get('contact_person_1') or contact.get('contact_name') or '')
    contact_greeting = f' Stimate/a {contact_p},' if contact_p else ','
    occupation_raw = str(contact.get('occupation') or '')
    occ_clean = __import__('re').sub(r'^\\d+ - ', '', occupation_raw).strip()
    position_text = f' pentru pozitia de {occ_clean}' if occ_clean else ''
    positions_n = str(contact.get('positions_available') or '')
    city_text = f' din {city}' if city else ''

    for old, new in [
        ('{company_name}', company), ('{company}', company), ('{name}', name),
        ('{email}', email_addr), ('{city}', city), ('{county}', county),
        ('{employees}', emp), ('{sector_name}', sector_name),
        ('{org_number}', org),
        ('{contact_greeting}', contact_greeting),
        ('{position_text}', position_text),
        ('{city_text}', city_text),
        ('{positions_available}', positions_n),
        ('{contact_person}', contact_p),
        ('{unsubscribe_url}', f"https://interjob.ro/unsubscribe.php?email={email_addr}"),
    ]:
        subject = subject.replace(old, new)
        body = body.replace(old, new)"""

if old in code:
    code = code.replace(old, new)
    open(f, 'w').write(code)
    print("PATCHED OK")
else:
    print("Pattern not found")
