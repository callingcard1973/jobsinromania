"""Shared config: all IMAP accounts, skip lists, patterns. Used by email_pipeline.py."""
import os, re

A2_PW = os.getenv('A2_EMAIL_PASSWORD', 'pADVouA01bYUkfpE')

ACCOUNTS = [
    # (email, password, imap_server, label)
    # A2 Hosting
    ('office@buildjobs.eu', A2_PW, 'mail.buildjobs.eu', 'buildjobs'),
    ('office@factoryjobs.eu', os.getenv('A2_FACTORYJOBS_EU_PASSWORD', A2_PW), 'mail.factoryjobs.eu', 'factoryjobs'),
    ('office@warehouseworkers.eu', os.getenv('A2_WAREHOUSEWORKERS_EU_PASSWORD', 'WwR6rJnezQV0Y2026'), 'mail.warehouseworkers.eu', 'warehouse'),
    ('office@interjob.ro', A2_PW, 'mail.interjob.ro', 'interjob'),
    ('office@mivromania.info', A2_PW, 'mail.mivromania.info', 'mivromania'),
    ('office@mivromania.online', A2_PW, 'mail.mivromania.online', 'mivromania-online'),
    ('office@careworkers.eu', A2_PW, 'mail.careworkers.eu', 'careworkers'),
    # cifn.info has no office@ email account

    ('office@nepalezi.com', A2_PW, 'mail.nepalezi.com', 'nepalezi'),
    ('office@expatsinromania.org', A2_PW, 'mail.expatsinromania.org', 'expats'),
    ('office@horecaworkers.eu', os.getenv('A2_HORECAWORKERS_EU_PASSWORD', 'z5b3VcHeskXckckl'), 'mail.horecaworkers.eu', 'horeca'),
    ('office@meatworkers.eu', os.getenv('A2_MEATWORKERS_EU_PASSWORD', '2FTkWzljss%YbJ4H'), 'mail.meatworkers.eu', 'meatworkers'),
    ('office@electricjobs.eu', os.getenv('A2_ELECTRICJOBS_EU_PASSWORD', 'vdYXx4wUByxJx@Sp'), 'mail.electricjobs.eu', 'electricjobs'),
    ('office@mechanicjobs.eu', os.getenv('A2_MECHANICJOBS_EU_PASSWORD', 'ZdL%QH@n6k2SHHGX'), 'mail.mechanicjobs.eu', 'mechanicjobs'),
    ('office@farmworkers.eu', os.getenv('A2_FARMWORKERS_EU_PASSWORD', 'ySIEf5TrffFGXjR1'), 'mail.farmworkers.eu', 'farmworkers'),
    # Gmail (all 9)
    ('manpowerdristor@gmail.com', os.getenv('GMAIL_APP_PASSWORD', 'dmrsuqiudvqtrpzu'), 'imap.gmail.com', 'gmail-mpd'),
    ('manpower.dristor@gmail.com', os.getenv('GMAIL_MANPOWER_APP_PASSWORD', 'tbdh pycf vbxo eung'), 'imap.gmail.com', 'gmail-mp.d'),
    ('elena.manpower.dristor@gmail.com', os.getenv('GMAIL_ELENA_PASSWORD', 'wmfnpikkcierkmrq'), 'imap.gmail.com', 'gmail-elena'),
    ('expatsinromania@gmail.com', os.getenv('GMAIL_EXPATS_PASSWORD', 'hxdn mukn jloe shkk'), 'imap.gmail.com', 'gmail-expats'),
    ('cumparlegume@gmail.com', os.getenv('GMAIL_CUMPARLEGUME_PASSWORD', 'iggy urti wmze znqo'), 'imap.gmail.com', 'gmail-cumparlegume'),
    ('casafaurbucuresti@gmail.com', os.getenv('GMAIL_CASAFAUR_PASSWORD', 'zlfb mbqf xiki mcbw'), 'imap.gmail.com', 'gmail-casafaur'),
    ('fruitnature4@gmail.com', os.getenv('GMAIL_FRUITNATURE_PASSWORD', 'mosv ghia ptwc xasr'), 'imap.gmail.com', 'gmail-fruitnature'),
    ('vegetablesbucharest@gmail.com', os.getenv('GMAIL_VEGETABLES_PASSWORD', 'filr iqdc rklp cbyu'), 'imap.gmail.com', 'gmail-vegetables'),
    ('fructexportromania@gmail.com', os.getenv('GMAIL_FRUCTEXPORT_PASSWORD', 'wqkp hejw nooo ztpv'), 'imap.gmail.com', 'gmail-fructexport'),
    ('icralbucuresti@gmail.com', os.getenv('GMAIL_ICRALBUCURESTI_PASSWORD', 'lqni pfzf ovyv otdu'), 'imap.gmail.com', 'gmail-icral'),
    ('carteledeapel@gmail.com', os.getenv('GMAIL_CARTELEDEAPEL_PASSWORD', 'dqzw ensj tmlb jrgj'), 'imap.gmail.com', 'gmail-cartele'),
    # Yahoo
    ('secretariatagentieasia@yahoo.com', os.getenv('YAHOO_APP_PASSWORD', 'tjchtpebagichoxz'), 'imap.mail.yahoo.com', 'yahoo-asia'),
    ('apaminerala@yahoo.com', os.getenv('YAHOO_APAMINERALA_APP_PASSWORD', 'fmlytelcixsizgeh'), 'imap.mail.yahoo.com', 'yahoo-apa'),
    # Zoho
    ('transport.work@zohomail.com', os.getenv('ZOHO_PASSWORD', 'JKkdxGS3szvC'), 'imap.zoho.com', 'zoho-transport'),
    ('workers.europe@zohomail.eu', os.getenv('ZOHO_PASSWORD_2', 'Mu59U3Lfa3Dw'), 'imap.zoho.eu', 'zoho-workers'),
]

# Internal senders to always skip
SKIP_SENDERS = {
    "elena.manpower.dristor@gmail.com","manpower.dristor@gmail.com","manpowerdristor@gmail.com",
    "noreply@interjob.ro","elena@interjob.ro","office@interjob.ro","tudor@interjob.ro",
    "office@seicarescu.com","tudor@seicarescu.com","office@mivromania.info",
    "mailer-daemon@","noreply@","no-reply@","notifications@","newsletter@",
    "@brevosend.com","@t.brevo.com","account-alerts@","@supabase.com",
    "@zohocorp.com",
    "@jobteam.dk","support@contactsplus.com","@5099400.brevosend.com",
}

# Subject patterns: system/auto
SKIP_SUBJ = re.compile(r"(out of office|autoreply|automatic reply|automatische antwort|auto response|"
    r"delivery.*(fail|status)|undeliver|vacation|campaign alert|stalled campaign|smtp test|"
    r"security alert|verify a new ip|welcome to brevo|new smtp key|getting started|"
    r"has been paused|going to be paused|thank you for your message)", re.I)

# Subject patterns: job applicant
APPLICANT_SUBJ = re.compile(r"(job application|application for|job search|farm worker position|"
    r"hotel job|seeking.*employment|ans.gning|looking for.*work|looking for.*job|"
    r"candidature|bewerbung|candidatura|disponible pour|dispo.*saison|"
    r"i am.*looking|my name is.*from|je me permets|cherche.*emploi|"
    r"apply.*position|request for.*job|interested in.*working)", re.I)

# Body patterns: job applicant
APPLICANT_BODY = re.compile(r"(attached my cv|my resume|i am looking for.{0,30}(job|work|employ)|"
    r"je suis.*motivé.*poste|available for work.*immediately|ready to start immediately|"
    r"zájem o.*práci|chtěla bych se.*zeptat|"
    r"i am \d+ years old.{0,50}(looking|work|job)|"
    r"i want to work|seasonal.*farm.*work|saisonnier.{0,30}logement|"
    r"please.*find my.*cv|cv.*attached|resume.*enclosed|"
    r"je me permets de vous adresser ma candidature)", re.I)

# Bounce sender/subject patterns
BOUNCE_SENDERS = re.compile(r"(mailer-daemon|postmaster|mail-daemon|mailerdaemon)", re.I)
BOUNCE_SUBJ = re.compile(r"(address not found|delivery.*fail|undeliverable|returned mail|"
    r"mail delivery.*failed|couldn.t be delivered|message not delivered|"
    r"message blocked|has been blocked|could not be delivered)", re.I)

# Unsubscribe / handover / not-interested patterns
UNSUB_BODY = re.compile(r"(dezabonare|unsubscribe|remove.*list|stergeti.*adresa|"
    r"nu mai.*trimite|stop.*email|opriti|nu doresc)", re.I)
# Skip but don't DNC - handover, not interested, already found
SKIP_BODY = re.compile(r"(am gasit deja|nu mai este valabil|nu avem nevoie|nu este cazul|"
    r"nu suntem interesati|not interested|keine interesse|"
    r"pas intéressé|ne pas donner suite|gestionam intern)", re.I)
# Partnership replies should NOT be classified as applicants
PARTNER_SUBJ = re.compile(r"(partnership proposal|recruitment partnership|business partnership|"
    r"collaboration|cooperation|propunere.*colaborare|parteneriat)", re.I)
# Handover: person changed, extract new contact
HANDOVER_BODY = re.compile(r"(atribuțiile mele vor fi gestionate|atributiile mele vor fi|"
    r"va fi preluat de|nu mai lucrez|am parasit compania|nu mai sunt in cadrul|"
    r"contactati.*pe|va rog.*contactati|persoana de contact.*devine|"
    r"has left the company|no longer with|please contact.*instead|"
    r"n'est plus en charge|veuillez contacter)", re.I)
# Extract new contact email + name from handover body
HANDOVER_EMAIL = re.compile(r"(?:gestionate de(?: catre)?|preluat de|contactati.*?pe|please contact|contacter)\s+([A-Z][a-zăâîșț]+(?:\s+[A-Z][a-zăâîșț]+){0,3})\s*\(?([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z.]+)", re.I)

# Personal email domains (for applicant detection + bounce cleanup)
PERSONAL_DOMAINS = ("@gmail.com","@yahoo.com","@yahoo.ro","@yahoo.de","@yahoo.fr",
    "@hotmail.com","@hotmail.de","@hotmail.fr","@outlook.com","@outlook.de",
    "@email.cz","@mail.ru","@live.com","@icloud.com","@ymail.com",
    "@t-online.de","@web.de","@gmx.de","@gmx.net","@aol.com","@protonmail.com",
    "@orange.fr","@free.fr","@laposte.net","@wp.pl","@o2.pl","@interia.pl")

# Patterns to extract bounced email from bounce message body
BOUNCE_EMAIL_PATTERNS = [
    r"wasn't delivered to ([^\s<>]+@[^\s<>]+)",
    r"delivery to ([^\s<>]+@[^\s<>]+) (?:has )?failed",
    r"couldn't be delivered to ([^\s<>]+@[^\s<>]+)",
    r"The email account.*?reach.*?([^\s<>()]+@[^\s<>()]+)",
    r"550[- ].*?<([^>]+@[^>]+)>",
    r"Final-Recipient:.*?([^\s<>;]+@[^\s<>;]+)",
    r"Recipient address rejected:.*?([^\s<>]+@[^\s<>]+)",
    r"User unknown.*?<([^>]+@[^>]+)>",
    r"mailbox unavailable.*?<([^>]+@[^>]+)>",
    r"does not exist.*?<([^>]+@[^>]+)>",
    r"address not found.*?([^\s<>]+@[^\s<>]+)",
    r"message to ([^\s<>]+@[^\s<>]+) has been blocked",
    r"blocked.*?([^\s<>]+@[^\s<>]+)",
]
