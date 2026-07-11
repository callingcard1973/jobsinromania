#!/usr/bin/env python3
"""Clasifica raspunsul la o oferta si pregateste un draft de raspuns (NU trimite)."""
import argparse
import os
import re
import sys

import offers_ledger as ledger

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
DRAFTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..",
                          "DATA", "00_SHARED_leads_si_dnc", "offer_drafts")

# WHY: clasificare deterministica pe cuvinte-cheie RO/EN; fara token LLM
RULES = [
    ("opt_out", r"\b(dezabon|unsubscribe|stop|nu mai|scoate|opt[- ]?out|nu doresc)\b"),
    ("interested", r"\b(interesat|interesati|da[,. ]|trimite|detalii|oferta|pret|colabor|interested|quote|send)\b"),
    ("question", r"\b(intreb|cum |cat |unde |cand |\?|how |what |when )\b"),
    ("bounce", r"\b(mailer-daemon|undeliverable|delivery failed|nu exista|mailbox full)\b"),
]


def classify_intent(text):
    """Returneaza: opt_out / interested / question / bounce / neutral."""
    t = (text or "").lower()
    for intent, pat in RULES:
        if re.search(pat, t):
            return intent
    return "neutral"


def _load_template(intent):
    path = os.path.join(TEMPLATES_DIR, intent + ".txt")
    if not os.path.exists(path):
        path = os.path.join(TEMPLATES_DIR, "neutral.txt")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def draft_response(email, text):
    """Tine minte replica, alege template, scrie draft ASCII. Returneaza (intent, draft_path)."""
    intent = classify_intent(text)
    ledger.record_reply(email, intent, text)

    if intent in ("opt_out", "bounce"):
        # WHY: nu raspundem la opt-out/bounce; doar marcam pentru DNC
        ledger.record_response(email, intent, draft_ref="(no-reply: -> DNC)")
        return intent, None

    offer = ledger.last_offer(email) or {}
    body = _load_template(intent)
    body = body.replace("{{CAMPAIGN}}", offer.get("campaign", "InterJob"))
    body = body.replace("{{SUBJECT}}", offer.get("subject", ""))
    # WHY: email ASCII-only obligatoriu
    body = body.encode("ascii", "ignore").decode("ascii")

    os.makedirs(DRAFTS_DIR, exist_ok=True)
    safe = re.sub(r"[^a-z0-9]+", "_", email.lower())
    draft_path = os.path.join(DRAFTS_DIR, safe + ".txt")
    with open(draft_path, "w", encoding="ascii") as fh:
        fh.write(body)
    ledger.record_response(email, intent, draft_ref=draft_path)
    return intent, draft_path


def _main():
    p = argparse.ArgumentParser(description="Raspunde la oferte (draft, NU trimite)")
    p.add_argument("--email", required=True)
    p.add_argument("--text", required=True, help="textul raspunsului primit")
    args = p.parse_args()
    intent, path = draft_response(args.email, args.text)
    print("intent=%s draft=%s" % (intent, path or "(none)"))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
