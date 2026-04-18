#!/usr/bin/env python3
"""Mailrelay batch sender: reads contacts from PostgreSQL, imports to Mailrelay, sends campaign.
Called by send_campaign.py when sender_type=mailrelay.

Flow:
1. Get unsent contacts from DB (daily_limit)
2. Sync them as Mailrelay subscribers in a dedicated group
3. Create one campaign with the rendered template
4. Send to that group
5. Mark contacts as sent in DB
"""
import os, sys, json, time, psycopg2, requests
from datetime import datetime
from pathlib import Path

def get_api():
    key = os.environ.get("MAILRELAY_API_KEY", "")
    base = os.environ.get("MAILRELAY_API_URL", "https://expatsinromania.ipzmarketing.com")
    if not base.endswith("/api/v1"):
        base = base.rstrip("/") + "/api/v1"
    return key, base

def _h(key):
    return {"X-Auth-Token": key, "Content-Type": "application/json"}

def ensure_group(key, base, name):
    """Get or create a Mailrelay group by name."""
    h = _h(key)
    r = requests.get(base + "/groups", headers=h, timeout=10)
    if r.status_code == 200:
        for g in r.json():
            if g["name"] == name:
                return g["id"]
    r2 = requests.post(base + "/groups", headers=h, json={"name": name}, timeout=10)
    if r2.status_code == 201:
        return r2.json()["id"]
    return None

def sync_subscribers(key, base, group_id, contacts):
    """Add contacts as Mailrelay subscribers in the group. Returns {email: sub_id}."""
    h = _h(key)
    result = {}
    for c in contacts:
        email = c.get("email", "").strip().lower()
        name = c.get("beneficiar") or c.get("company_name") or c.get("name") or email
        if not email:
            continue
        # Check if exists
        r = requests.get(base + "/subscribers", headers=h,
                         params={"q[email_eq]": email}, timeout=10)
        if r.status_code == 200 and r.json():
            sid = r.json()[0]["id"]
            # Update group
            requests.patch(base + "/subscribers/" + str(sid), headers=h,
                           json={"group_ids": [group_id]}, timeout=10)
        else:
            # Create
            r2 = requests.post(base + "/subscribers", headers=h, json={
                "name": str(name)[:80], "email": email,
                "group_ids": [group_id], "status": "active"}, timeout=10)
            sid = r2.json().get("id") if r2.status_code == 201 else None
        if sid:
            result[email] = sid
        time.sleep(0.2)  # rate limit
    return result

def send_campaign(key, base, group_id, subject, html_body):
    """Create and send one Mailrelay campaign to a group."""
    h = _h(key)
    if "[unsubscribe_url]" not in html_body:
        html_body += '<p><a href="[unsubscribe_url]">Unsubscribe</a></p>'
    camp = {"subject": subject, "sender_id": 1, "html": html_body,
            "target": "groups", "group_ids": [group_id]}
    r = requests.post(base + "/campaigns", headers=h, json=camp, timeout=15)
    if r.status_code != 201:
        return False, "CAMP_CREATE_" + str(r.status_code) + ":" + r.text[:100]
    cid = r.json()["id"]
    r2 = requests.post(base + "/campaigns/" + str(cid) + "/send_all", headers=h,
                        json={"target": "groups", "group_ids": [group_id]}, timeout=15)
    if r2.status_code == 200:
        return True, str(cid)
    return False, "CAMP_SEND_" + str(r2.status_code) + ":" + r2.text[:100]

def run_mailrelay_batch(db_cfg, tables_cfg, contacts, subject_tpl, body_tpl,
                        daily_limit=100, campaign_name="mailrelay", logger=None):
    """Main entry: sync contacts, send campaign, return count sent."""
    log = logger.info if logger else print
    key, base = get_api()
    if not key:
        log("MAILRELAY: no API key")
        return 0

    # Create/get group for this campaign
    group_name = "campaign_" + campaign_name[:30]
    gid = ensure_group(key, base, group_name)
    if not gid:
        log("MAILRELAY: cannot create group")
        return 0

    # Limit contacts
    batch = contacts[:daily_limit]
    log(f"MAILRELAY: syncing {len(batch)} subscribers to group {group_name}")

    # Sync subscribers
    sub_map = sync_subscribers(key, base, gid, batch)
    log(f"MAILRELAY: {len(sub_map)} subscribers synced")
    if not sub_map:
        return 0

    # Build HTML from first contact (subject is campaign-level, same for all)
    # For personalization, Mailrelay supports [subscriber:name] but not custom fields
    # So we send one campaign per unique subject, or use generic subject
    html = "<div style='font-family:Arial,sans-serif;font-size:14px;line-height:1.6'>"
    html += body_tpl.replace("\n", "<br>") + "</div>"

    ok, msg = send_campaign(key, base, gid, subject_tpl, html)
    if ok:
        log(f"MAILRELAY: campaign {msg} sent to {len(sub_map)} recipients")
        return len(sub_map)
    else:
        log(f"MAILRELAY: FAILED {msg}")
        return 0
