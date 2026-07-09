"""Response Tracker Inbox Config — all monitored inboxes."""

# A2 Hosting IMAP (all office@ addresses)
A2_HOST = "nl1-cl8-ats1.a2hosting.com"
A2_PORT = 993

INBOXES = [
    # Zoho
    {"name": "seicarescu", "host": "imap.zoho.eu", "port": 993,
     "user": "tudor@seicarescu.com", "password_env": "ZOHO_SEICARESCU_PASSWORD"},
    {"name": "zoho_transport", "host": "smtp.zoho.com", "port": 993,
     "user": "transport.work@zohomail.com", "password_env": "ZOHO_PASSWORD"},
    {"name": "zoho_workers", "host": "smtp.zoho.eu", "port": 993,
     "user": "workers.europe@zohomail.eu", "password_env": "ZOHO_PASSWORD_2"},
    # Gmail (with app passwords)
    {"name": "manpower_dristor", "host": "imap.gmail.com", "port": 993,
     "user": "manpower.dristor@gmail.com", "password_env": "GMAIL_MANPOWERDRISTOR_APP_PASSWORD"},
    {"name": "manpower_search", "host": "imap.gmail.com", "port": 993,
     "user": "manpowersearchromania@gmail.com", "password_env": "GMAIL_MANPOWER_APP_PASSWORD"},
    {"name": "elena", "host": "imap.gmail.com", "port": 993,
     "user": "elena.manpower.dristor@gmail.com", "password_env": "GMAIL_ELENA_APP_PASSWORD"},
    {"name": "lucian", "host": "imap.gmail.com", "port": 993,
     "user": "lucian.bpandp@gmail.com", "password_env": "GMAIL_LUCIAN_APP_PASSWORD"},
    # A2 Hosting (office@ addresses — top volume inboxes)
    {"name": "buildjobs", "host": A2_HOST, "port": A2_PORT,
     "user": "office@buildjobs.eu", "password_env": "A2_EMAIL_PASSWORD"},
    {"name": "careworkers", "host": A2_HOST, "port": A2_PORT,
     "user": "office@careworkers.eu", "password_env": "A2_EMAIL_PASSWORD"},
    {"name": "interjob", "host": A2_HOST, "port": A2_PORT,
     "user": "office@interjob.ro", "password_env": "A2_EMAIL_PASSWORD"},
    {"name": "factoryjobs", "host": A2_HOST, "port": A2_PORT,
     "user": "office@factoryjobs.eu", "password_env": "A2_FACTORYJOBS_EU_PASSWORD"},
    {"name": "warehouseworkers", "host": A2_HOST, "port": A2_PORT,
     "user": "office@warehouseworkers.eu", "password_env": "A2_WAREHOUSEWORKERS_EU_PASSWORD"},
    {"name": "mivromania", "host": A2_HOST, "port": A2_PORT,
     "user": "office@mivromania.info", "password_env": "A2_EMAIL_PASSWORD"},
    {"name": "expatsinromania", "host": A2_HOST, "port": A2_PORT,
     "user": "office@expatsinromania.org", "password_env": "A2_EMAIL_PASSWORD"},
    {"name": "horecaworkers2026", "host": A2_HOST, "port": A2_PORT,
     "user": "office@horecaworkers2026.eu", "password_env": "A2_HORECAWORKERS2026_EU_PASSWORD"},
    {"name": "electricjobs", "host": A2_HOST, "port": A2_PORT,
     "user": "office@electricjobs.eu", "password_env": "A2_ELECTRICJOBS_EU_PASSWORD"},
    {"name": "meatworkers", "host": A2_HOST, "port": A2_PORT,
     "user": "office@meatworkers.eu", "password_env": "A2_MEATWORKERS_EU_PASSWORD"},
    {"name": "agroevolution", "host": A2_HOST, "port": A2_PORT,
     "user": "office@agroevolution.com", "password_env": "A2_EMAIL_PASSWORD"},
    {"name": "cifn", "host": A2_HOST, "port": A2_PORT,
     "user": "office@cifn.eu", "password_env": "A2_EMAIL_PASSWORD"},
    # Solonet tracking — captures all conversation with Adrian
    {"name": "solonet_tracker", "host": A2_HOST, "port": A2_PORT,
     "user": "adrian.craciunescu@buildjobs.eu", "password_env": "A2_SOLONET_PASSWORD"},
]

# Own addresses to filter out (don't count as responses)
OWN_EMAILS = {inbox["user"].lower() for inbox in INBOXES}
OWN_EMAILS.update({
    "noreply@interjob.ro", "noreply@buildjobs.eu",
    "office@bppltd.co.uk", "office@horecaworkers.com",
    "campaigns@m.brevo.com", "info@mailrelay.com",
    "community@learn.mailjet.com", "no-reply@brevo.com",
})
