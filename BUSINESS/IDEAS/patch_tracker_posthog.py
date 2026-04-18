#!/usr/bin/env python3
content = open("/opt/ACTIVE/INFRA/SKILLS/response_tracker.py").read()

if "POSTHOG_KEY" not in content:
    old_imports = "import psycopg2"
    new_imports = """import psycopg2
import requests as _req

POSTHOG_KEY = "phx_ZKBT7BuYJ2UQZZVJN62uqp95U5nrYZK79auQzCxc7Ad7n64i"
POSTHOG_PROJECT = "377581"

def _ph_event(event, props):
    try:
        _req.post("https://us.i.posthog.com/capture/", json={
            "api_key": POSTHOG_KEY,
            "event": event,
            "distinct_id": props.get("email", "unknown"),
            "properties": props,
        }, timeout=5)
    except Exception:
        pass
"""
    content = content.replace(old_imports, new_imports, 1)

# Fire PostHog event on INTERESTED + all categories
old = "            save_response_db(sender, subject, category, campaign, name)"
new = """            _ph_event("campaign_response", {
                "email": sender, "campaign": campaign,
                "category": category, "inbox": name,
                "funnel_stage": "replied" if category == "INTERESTED" else category.lower(),
            })
            save_response_db(sender, subject, category, campaign, name)"""
content = content.replace(old, new, 1)

open("/opt/ACTIVE/INFRA/SKILLS/response_tracker.py", "w").write(content)
print("tracker patched")
