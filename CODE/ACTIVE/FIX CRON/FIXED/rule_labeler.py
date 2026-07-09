#!/usr/bin/env python3
"""Rule-based email pre-labeler: classify obvious emails, leave ambiguous for Claude."""

import json
import re
import sqlite3
import sys
import argparse
from datetime import datetime
from pathlib import Path

DATA_DIR = Path("/opt/ACTIVE/EMAIL/PROCESSORS/data/training_data")
RAW_FILE = DATA_DIR / "raw_emails.jsonl"
LABELS_DB = DATA_DIR / "labels.db"

# =============================================================================
# DETECTION PATTERNS (from email_sorter.py)
# =============================================================================

BOUNCE_SENDERS = ["mailer-daemon", "postmaster", "mail-daemon"]
BOUNCE_SUBJECT_RE = re.compile(
    r"delivery (status|failure|notification)|undeliverable|undelivered mail|"
    r"returned (to sender|mail)|mail delivery (failed|system)|"
    r"failure notice|non[\-\s]?delivery|could not be delivered|"
    r"delivery has failed",
    re.IGNORECASE
)

AUTOREPLY_SENDER_PATTERNS = [
    "noreply-autoreply@", "auto-reply@", "autoreply@", "vacation@",
    "ooo@", "out-of-office@", "autoresponder@", "do-not-reply@",
    "donotreply@", "noreply@", "no-reply@", "lis-noreply@",
]

AUTOREPLY_SUBJECT_RE = re.compile(
    r"autosvar|automatiskt svar|auto[\-\s]?reply|automatic reply|"
    r"out of office|abwesenheitsnotiz|automatische antwort|"
    r"r[ée]ponse automatique|risposta automatica|respuesta autom[aá]tica|"
    r"automatisch antwoord|automaattinen vastaus|automatisk svar|"
    r"fr[åa]nvaro|afwezigheidsbericht|vacation|away from .{0,20}(office|desk)|"
    r"automated response|auto response|ärendenummer",
    re.IGNORECASE
)

APPLICATION_SUBJECT_RE = re.compile(
    r"new submission|form submission|contact form|formspree|"
    r"new application|job application|cv attached|resume attached|"
    r"candidatura|aplicare pentru|looking for (a )?(job|work)|"
    r"caut lucru|seeking employment|application for|apply(ing)? for|"
    r"bewerbung|candidature|application as",
    re.IGNORECASE
)

APPLICATION_BODY_RE = re.compile(
    r"attached my cv|attached cv|my resume|job seeker|"
    r"available for work|available immediately|willing to relocate|"
    r"years of experience|work permit|looking for (a )?(job|work)|"
    r"please find (my |attached )|i am .{0,30}(looking|seeking|applying)|"
    r"i have experience|my name is .{2,30}(from|and i)|"
    r"i would like to apply|ready to relocate",
    re.IGNORECASE
)

APPLICATION_ATTACHMENT_RE = re.compile(
    r"(cv|resume|lebenslauf|curriculum)", re.IGNORECASE
)
APPLICATION_ATTACHMENT_EXTS = {".pdf", ".doc", ".docx"}

UNSUBSCRIBE_RE = re.compile(
    r"^(unsubscribe|dezabonare|désabonnement|abmelden|remove me)$",
    re.IGNORECASE
)

NEWSLETTER_SENDERS = [
    "meetup.com", "linkedin.com", "facebook.com", "indeed.com",
    "glassdoor.com", "mailchimp.com", "sendgrid.net", "constantcontact.com",
    "hubspot.com", "campaign-archive.com", "email.meetup.com",
    "t.brevo.com", "conferintemedicale.ro",
    "sethgodin.com", "cobratate.com", "infinitusmail.com",
    "howtogeek.com", "makeuseof.com", "declic.ro",
    "hambarulromanesc.ro", "americanroadpatch.com", "agricolumn.ro",
    "oipa.ro", "greenenergyexpo-romenvirotec.ro", "kdnuggets.com",
    "emailempire.org", "substack.com", "beehiiv.com",
    "convertkit.com", "getrevue.co", "buttondown.email",
    "medium.com", "quora.com", "digest-noreply",
    "morningbrew.com", "themorningbrew.com", "eepurl.com",
    "list-manage.com", "createsend.com", "cmail19.com",
    "cmail20.com", "activecampaign.com", "getresponse.com",
    "aweber.com", "drip.com", "infusionsoft.com",
]

# SEO / marketing spam patterns
SEO_SPAM_SUBJECT_RE = re.compile(
    r"1st page|first page|seo proposal|seo service|seo offer|"
    r"website (on |to )?(the )?front page|rank(ing)? (on |in )?google|"
    r"i can show you sample|digital marketing proposal|"
    r"get (more |your )?traffic|boost your (website|ranking)|"
    r"web (design|development) (offer|proposal|quote)",
    re.IGNORECASE
)

SEO_SPAM_BODY_RE = re.compile(
    r"get your website on the front page|"
    r"rank.{0,20}(first|1st) page|"
    r"seo (service|proposal|package|offer)|"
    r"improve your (ranking|visibility|traffic)|"
    r"backlink|link.?building|keyword ranking|"
    r"did not respond to my last email.{0,50}(seo|website|rank)|"
    r"i can show you sample.{0,30}cost",
    re.IGNORECASE
)

# Internal system notification patterns
INTERNAL_NOTIFICATION_SENDERS = [
    "manpowerdristor@gmail.com", "manpower.dristor@gmail.com",
]

INTERNAL_SUBJECT_RE = re.compile(
    r"CQC Complete|scrape complete|cron |backup complete|"
    r"sync complete|report generated|daily report|weekly report",
    re.IGNORECASE
)

# Service notifications (Brevo, Google, platform alerts)
SERVICE_NOTIFICATION_RE = re.compile(
    r"new (SMTP|API) key.{0,20}created|"
    r"welcome to brevo|account.?alert|"
    r"your.{0,10}(password|account).{0,20}(changed|reset|created)|"
    r"verify your email|confirm your (email|account)",
    re.IGNORECASE
)

# Email change / inactive address notifications
EMAIL_CHANGE_RE = re.compile(
    r"nu mai este activ|adres[aă] .{0,20}(schimbat|nou)|"
    r"email.{0,10}(changed|no longer|inactive)|"
    r"this email.{0,20}(is no longer|has been|was) (active|disabled|deactivated)",
    re.IGNORECASE
)

# Empty email detection
EMPTY_BODY_SIGS = [
    "sent from my iphone", "sent from my samsung", "sent from yahoo",
    "sent from outlook", "trimis de pe", "envoyé de mon",
]

# Our own domains — campaign replies come TO these
OUR_DOMAINS = [
    "buildjobs.eu", "factoryjobs.eu", "warehouseworkers.eu", "interjob.ro",
    "mivromania.info", "mivromania.online", "careworkers.eu", "cifn.info",
    "nepalezi.com", "expatsinromania.org", "horecaworkers.eu", "meatworkers.eu",
    "electricjobs.eu", "mechanicjobs.eu", "farmworkers.eu",
    "horecaworkers2026.eu", "horecaworkers2026.com", "horecaworkers2026.online",
    "internaltransfers.eu", "aluminumrecyclehub.com", "agroevolution.com",
    "cumparlegume.com", "seicarescu.com",
]

# =============================================================================
# LANGUAGE DETECTION (simple heuristics)
# =============================================================================

LANG_PATTERNS = {
    "ro": re.compile(r"buna ziua|va multumim|cu stima|va rog|foarte|dumneavoastra|servicii|recrutare|colaborare", re.IGNORECASE),
    "de": re.compile(r"bewerbung|sehr geehrte|mit freundlichen|arbeit|erfahrung|stelle|lebenslauf", re.IGNORECASE),
    "fr": re.compile(r"bonjour|merci|cordialement|cher|absent|réponse|automatique", re.IGNORECASE),
    "sv": re.compile(r"tack|kontaktar|ärende|välkommen|automatiskt|svar", re.IGNORECASE),
    "es": re.compile(r"hola|gracias|estimado|saludos|respuesta", re.IGNORECASE),
    "it": re.compile(r"buongiorno|grazie|cordiali saluti|risposta", re.IGNORECASE),
    "ne": re.compile(r"नमस्ते|नेपाल|काम", re.IGNORECASE),
    "ar": re.compile(r"مرحبا|شكرا|السلام", re.IGNORECASE),
    "bn": re.compile(r"বাংলাদেশ|ধন্যবাদ|নাম", re.IGNORECASE),
}

def detect_language(text):
    scores = {}
    for lang, pattern in LANG_PATTERNS.items():
        matches = len(pattern.findall(text))
        if matches > 0:
            scores[lang] = matches
    if scores:
        return max(scores, key=scores.get)
    return "en"  # default

# =============================================================================
# CLASSIFICATION
# =============================================================================

def classify_email(email_data):
    """Try to classify email using rules. Returns label dict or None if ambiguous."""
    from_addr = email_data.get("from", "").lower()
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")
    attachments = email_data.get("attachments", [])
    full_text = f"{subject} {body}"

    # Extract sender email
    sender_email = ""
    m = re.search(r'<([^>]+)>', from_addr)
    if m:
        sender_email = m.group(1).lower()
    elif "@" in from_addr:
        sender_email = from_addr.strip().lower()

    sender_domain = sender_email.split("@")[-1] if "@" in sender_email else ""

    lang = detect_language(full_text)

    # --- SELF-SENT EMAILS (bookmarks/notes to self) ---
    if sender_email and sender_email == email_data.get("account", "").lower():
        return {
            "intent": "other",
            "spam_score": 0,
            "language": lang,
            "priority": "low",
            "folder": "INBOX",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [], "email_addresses": []},
            "summary": f"Self-sent email (bookmark/note): {subject[:60]}",
        }

    # --- OUR OWN OUTGOING EMAILS (campaign copies in Gmail sent/inbox) ---
    if sender_domain in [d for d in OUR_DOMAINS]:
        our_campaign_text = re.compile(
            r"bp&p partners|interjob solutions|lucian.{0,30}bp&p|"
            r"ma numesc lucian|sunt lucian|tudor seicarescu|"
            r"va contactam din partea|furnizare personal|"
            r"colaborare servicii|personal pentru pensiunea|"
            r"bucatari si ospatari|solutii de personal|"
            r"test email from",
            re.IGNORECASE
        )
        if our_campaign_text.search(body[:500]) or our_campaign_text.search(subject):
            return {
                "intent": "other",
                "spam_score": 0,
                "language": "ro",
                "priority": "low",
                "folder": "INBOX",
                "entities": {"person_names": [], "companies": [], "job_roles": [],
                            "locations": [], "phone_numbers": [], "email_addresses": []},
                "summary": f"Our own outgoing campaign email from {sender_email}",
            }

    # --- BOUNCE ---
    is_bounce = False
    for bs in BOUNCE_SENDERS:
        if bs in sender_email:
            is_bounce = True
            break
    if BOUNCE_SUBJECT_RE.search(subject):
        is_bounce = True
    if is_bounce:
        # Extract bounced address from body
        bounced = re.findall(r'<([^>]+@[^>]+)>', body)
        return {
            "intent": "bounce",
            "spam_score": 0,
            "language": "en",
            "priority": "low",
            "folder": "AUTOREPLY",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [],
                        "email_addresses": bounced[:3]},
            "summary": f"Bounce notification: {bounced[0] if bounced else 'unknown recipient'}",
        }

    # --- AUTO-REPLY ---
    is_autoreply = False
    for pattern in AUTOREPLY_SENDER_PATTERNS:
        if pattern in sender_email:
            is_autoreply = True
            break
    if AUTOREPLY_SUBJECT_RE.search(subject):
        is_autoreply = True
    if is_autoreply:
        return {
            "intent": "auto_reply",
            "spam_score": 5,
            "language": lang,
            "priority": "low",
            "folder": "AUTOREPLY",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [], "email_addresses": []},
            "summary": f"Auto-reply from {sender_email}",
        }

    # --- UNSUBSCRIBE ---
    body_stripped = body.strip()
    if UNSUBSCRIBE_RE.match(body_stripped) or body_stripped.lower() in ("unsubscribe", "dezabonare", "stop"):
        return {
            "intent": "unsubscribe",
            "spam_score": 3,
            "language": lang,
            "priority": "normal",
            "folder": "INBOX",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [],
                        "email_addresses": [sender_email] if sender_email else []},
            "summary": f"Unsubscribe request from {sender_email}",
        }

    # --- SEO SPAM ---
    is_seo_spam = False
    if SEO_SPAM_SUBJECT_RE.search(subject):
        is_seo_spam = True
    if SEO_SPAM_BODY_RE.search(body):
        is_seo_spam = True
    # Outlook.com senders with SEO keywords are almost always spam
    if "outlook.com" in sender_domain and any(w in full_text.lower() for w in ["seo", "1st page", "front page", "ranking", "website"]):
        is_seo_spam = True
    if is_seo_spam:
        return {
            "intent": "spam",
            "spam_score": 85,
            "language": lang,
            "priority": "low",
            "folder": "SPAM",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [],
                        "email_addresses": [sender_email] if sender_email else []},
            "summary": f"SEO/marketing spam from {sender_email}",
        }

    # --- INTERNAL SYSTEM NOTIFICATIONS ---
    if sender_email in INTERNAL_NOTIFICATION_SENDERS and INTERNAL_SUBJECT_RE.search(subject):
        return {
            "intent": "other",
            "spam_score": 0,
            "language": "en",
            "priority": "low",
            "folder": "INBOX",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [], "email_addresses": []},
            "summary": f"Internal system notification: {subject[:60]}",
        }

    # --- SERVICE NOTIFICATIONS (Brevo, platform alerts) ---
    if SERVICE_NOTIFICATION_RE.search(subject) or SERVICE_NOTIFICATION_RE.search(body[:500]):
        return {
            "intent": "other",
            "spam_score": 10,
            "language": lang,
            "priority": "low",
            "folder": "INBOX",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [], "email_addresses": []},
            "summary": f"Service notification from {sender_domain}",
        }

    # --- EMAIL CHANGE / INACTIVE ADDRESS ---
    if EMAIL_CHANGE_RE.search(full_text):
        return {
            "intent": "auto_reply",
            "spam_score": 5,
            "language": lang,
            "priority": "low",
            "folder": "AUTOREPLY",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [],
                        "email_addresses": [sender_email] if sender_email else []},
            "summary": f"Email address changed/inactive notification from {sender_email}",
        }

    # --- NEWSLETTER / MARKETING ---
    for nl_domain in NEWSLETTER_SENDERS:
        if nl_domain in sender_domain or nl_domain in sender_email:
            return {
                "intent": "newsletter",
                "spam_score": 55,
                "language": lang,
                "priority": "low",
                "folder": "SPAM",
                "entities": {"person_names": [], "companies": [], "job_roles": [],
                            "locations": [], "phone_numbers": [], "email_addresses": []},
                "summary": f"Newsletter/marketing from {sender_domain}",
            }

    # --- EMPTY / NEAR-EMPTY EMAILS ---
    body_clean = body.strip().lower()
    is_empty = len(body_clean) < 5
    if not is_empty:
        for sig in EMPTY_BODY_SIGS:
            if body_clean.replace("\r", "").replace("\n", "").strip() == sig or \
               len(body_clean) < 50 and sig in body_clean:
                is_empty = True
                break
    if is_empty and not subject.strip():
        return {
            "intent": "other",
            "spam_score": 20,
            "language": "en",
            "priority": "low",
            "folder": "INBOX",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [],
                        "email_addresses": [sender_email] if sender_email else []},
            "summary": f"Empty/near-empty email from {sender_email}",
        }

    # --- AUTO-REPLY: recruitment HR confirmations ---
    hr_auto_re = re.compile(
        r"multumim pentru aplicatie|thank you for (your |the )?application|"
        r"cv.{0,20}(inregistrat|primit|received)|"
        r"candidatura.{0,20}(inregistrat|primit)|"
        r"we.{0,20}received your (cv|application|resume)",
        re.IGNORECASE
    )
    if hr_auto_re.search(full_text) and not APPLICATION_BODY_RE.search(body):
        return {
            "intent": "auto_reply",
            "spam_score": 5,
            "language": lang,
            "priority": "low",
            "folder": "AUTOREPLY",
            "entities": {"person_names": [], "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [],
                        "email_addresses": [sender_email] if sender_email else []},
            "summary": f"HR auto-confirmation from {sender_email}",
        }

    # --- APPLICATION ---
    is_application = False

    # Check subject
    if APPLICATION_SUBJECT_RE.search(subject):
        is_application = True

    # Check body
    if APPLICATION_BODY_RE.search(body):
        is_application = True

    # Check attachments for CV
    has_cv = False
    for att in attachments:
        if APPLICATION_ATTACHMENT_RE.search(att):
            has_cv = True
            break
        ext = "." + att.rsplit(".", 1)[-1].lower() if "." in att else ""
        if ext in APPLICATION_ATTACHMENT_EXTS:
            has_cv = True
            break

    if has_cv and not is_application:
        # PDF/DOC attachment likely means application
        is_application = True

    if is_application:
        # Extract person name from "From" header
        name = from_addr.split("<")[0].strip().strip('"').strip("'")
        names = [name] if name and "@" not in name else []
        return {
            "intent": "application",
            "spam_score": 2,
            "language": lang,
            "priority": "normal",
            "folder": "APPLICATIONS_RECEIVED",
            "entities": {"person_names": names, "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [],
                        "email_addresses": [sender_email] if sender_email else []},
            "summary": f"Job application from {name or sender_email}",
        }

    # --- CAMPAIGN REPLY (reply to our outgoing email) ---
    our_sigs = ["interjob solutions", "bp&p partners", "tudor seicarescu",
                 "echipa bp&p", "mivromania", "interjob.ro",
                 "pentru dezabonare", "pentru a nu mai primi",
                 "bp&p ltd", "whatsapp : +33", "+40 771 028 948",
                 "personal pentru pensiunea", "colaborare furnizare personal",
                 "colaborare servicii forta de munca",
                 "recrutare si plasare forta de munca"]
    body_lower = body.lower()
    is_campaign_reply = False

    # Check "Re:" subject + our signature in body
    if "re:" in subject.lower():
        for sig in our_sigs:
            if sig in body_lower:
                is_campaign_reply = True
                break

    # Check even without Re: if body quotes our exact campaign text
    if not is_campaign_reply:
        campaign_quotes = ["va contactam din partea interjob",
                          "am vazut anuntul dumneavoastra",
                          "oferim servicii de recrutare",
                          "avem candidati disponibili"]
        for cq in campaign_quotes:
            if cq in body_lower:
                is_campaign_reply = True
                break

    if is_campaign_reply:
        name = from_addr.split("<")[0].strip().strip('"').strip("'")
        names = [name] if name and "@" not in name else []
        # Check if they're expressing interest (upgrade to inquiry)
        interest_re = re.compile(
            r"interesat|interested|da, (as )?dori|yes.{0,20}(interest|like)|"
            r"am nevoie de|we need|avem nevoie|cautam|ne intereseaza|"
            r"bucatar|muncitor|electrician|instalator|barman|"
            r"lucr[aă]tori|personal|worker|employee",
            re.IGNORECASE
        )
        if interest_re.search(body[:500]):
            return {
                "intent": "inquiry",
                "spam_score": 0,
                "language": lang,
                "priority": "urgent",
                "folder": "INBOX",
                "entities": {"person_names": names, "companies": [], "job_roles": [],
                            "locations": [], "phone_numbers": [],
                            "email_addresses": [sender_email] if sender_email else []},
                "summary": f"Interested campaign reply from {name or sender_email} — HOT LEAD",
            }
        return {
            "intent": "campaign_reply",
            "spam_score": 0,
            "language": lang,
            "priority": "normal",
            "folder": "INBOX",
            "entities": {"person_names": names, "companies": [], "job_roles": [],
                        "locations": [], "phone_numbers": [],
                        "email_addresses": [sender_email] if sender_email else []},
            "summary": f"Reply to our campaign from {name or sender_email}",
        }

    # --- AMBIGUOUS — return None, needs Claude ---
    return None


def run_rule_labeler(dry_run=False):
    """Label all unlabeled emails using rules."""
    conn = sqlite3.connect(str(LABELS_DB))

    # Init DB
    conn.execute("""
        CREATE TABLE IF NOT EXISTS labels (
            dedup_key TEXT PRIMARY KEY,
            message_id TEXT, account TEXT, from_addr TEXT, subject TEXT,
            intent TEXT, spam_score INTEGER, language TEXT, priority TEXT, folder TEXT,
            entities_json TEXT, raw_email_json TEXT, claude_response TEXT,
            model TEXT, tokens_in INTEGER, tokens_out INTEGER, labeled_at TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_intent ON labels(intent)")
    conn.commit()

    # Load labeled keys
    labeled = set(r[0] for r in conn.execute("SELECT dedup_key FROM labels").fetchall())

    # Load raw emails
    emails = []
    with open(RAW_FILE, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line.strip())
            if e["dedup_key"] not in labeled:
                emails.append(e)

    print(f"Unlabeled emails: {len(emails)}")

    rule_labeled = 0
    ambiguous = 0
    intent_counts = {}

    for e in emails:
        label = classify_email(e)
        if label:
            intent_counts[label["intent"]] = intent_counts.get(label["intent"], 0) + 1
            rule_labeled += 1

            if not dry_run:
                conn.execute("""
                    INSERT OR REPLACE INTO labels
                    (dedup_key, message_id, account, from_addr, subject,
                     intent, spam_score, language, priority, folder,
                     entities_json, raw_email_json, claude_response,
                     model, tokens_in, tokens_out, labeled_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    e["dedup_key"],
                    e.get("message_id", ""),
                    e.get("account", ""),
                    e.get("from", ""),
                    e.get("subject", ""),
                    label["intent"],
                    label["spam_score"],
                    label["language"],
                    label["priority"],
                    label["folder"],
                    json.dumps(label.get("entities", {}), ensure_ascii=False),
                    json.dumps(e, ensure_ascii=False),
                    json.dumps(label, ensure_ascii=False),
                    "rule-based-v1",
                    0, 0,
                    datetime.now().isoformat(),
                ))
        else:
            ambiguous += 1

    if not dry_run:
        conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0] if not dry_run else "N/A"
    conn.close()

    print(f"\nRule-labeled: {rule_labeled}")
    print(f"Ambiguous (need Claude): {ambiguous}")
    print(f"Total in DB: {total}")
    print(f"\nRule breakdown:")
    for intent, count in sorted(intent_counts.items(), key=lambda x: -x[1]):
        print(f"  {intent:20s}  {count:5d}")


def main():
    parser = argparse.ArgumentParser(description="Rule-based email pre-labeler")
    parser.add_argument("--dry-run", action="store_true", help="Preview without saving")
    parser.add_argument("--stats", action="store_true", help="Show current stats")
    args = parser.parse_args()

    if args.stats:
        conn = sqlite3.connect(str(LABELS_DB))
        total = conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
        print(f"Total labeled: {total}")
        for row in conn.execute("SELECT model, COUNT(*) FROM labels GROUP BY model ORDER BY COUNT(*) DESC"):
            print(f"  {row[0]:30s}  {row[1]:5d}")
        conn.close()
    else:
        run_rule_labeler(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
