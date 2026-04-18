#!/usr/bin/env python3
"""Inject sender_brand/url/tagline into contact dict before expand_template."""
path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

if "sender_brand" in content:
    print("Already patched")
else:
    old = "contact['catalog_email'] = cfg.get('catalog_email', 'catalog@interjob.ro'); subj, body = expand_template(subj_tpl, body_tpl, contact)"
    new = (
        "contact['catalog_email'] = cfg.get('catalog_email', 'catalog@interjob.ro'); "
        "contact['sender_brand'] = cfg.get('sender_brand', 'InterJob Solutions'); "
        "contact['sender_url'] = cfg.get('sender_url', 'https://interjob.ro'); "
        "contact['sender_tagline'] = cfg.get('sender_tagline', 'Agentie recrutare internationala'); "
        "subj, body = expand_template(subj_tpl, body_tpl, contact)"
    )
    content = content.replace(old, new)

    old2 = "c['catalog_email'] = cfg.get('catalog_email', 'catalog@interjob.ro'); subj, body = expand_template(subj_tpl, body_tpl, c)"
    new2 = (
        "c['catalog_email'] = cfg.get('catalog_email', 'catalog@interjob.ro'); "
        "c['sender_brand'] = cfg.get('sender_brand', 'InterJob Solutions'); "
        "c['sender_url'] = cfg.get('sender_url', 'https://interjob.ro'); "
        "c['sender_tagline'] = cfg.get('sender_tagline', 'Agentie recrutare internationala'); "
        "subj, body = expand_template(subj_tpl, body_tpl, c)"
    )
    content = content.replace(old2, new2)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("send_campaign.py patched OK")
