import re
import html
import unicodedata

PERSONAL_DOMAINS = {
    'gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.fr', 'yahoo.ca',
    'yahoo.co.uk', 'yahoo.ro', 'yahoo.es', 'yahoo.de', 'hotmail.com',
    'hotmail.fr', 'msn.com', 'live.com', 'live.fr', 'mail.ru', 'aol.com',
    'icloud.com', 'me.com', 'outlook.com', 'sympatico.ca', 'rogers.com',
    'videotron.ca', 'web.de',
}

GARBLE_PATTERN = re.compile(r'^\s*[\(\*\%\"\'\`]+[^\w]*')
EMOJI_PATTERN = re.compile(
    r'[\U00010000-\U0010ffff]|[\U0001F300-\U0001F9FF]', flags=re.UNICODE
)

def clean_name(name: str) -> str:
    name = html.unescape(name or '')
    name = EMOJI_PATTERN.sub('', name)
    name = GARBLE_PATTERN.sub('', name)
    name = re.sub(r'[\(\*\%\"\'\`&]+', '', name)
    return name.strip()

def normalize_email(email: str) -> str:
    return (email or '').strip().lower()

def normalize_phone(phone: str) -> str:
    p = re.sub(r'[\s\-\(\)]', '', (phone or ''))
    return p

def is_personal_domain(domain: str) -> bool:
    domain = domain.lower().strip()
    if domain in PERSONAL_DOMAINS:
        return True
    if domain.startswith('yahoo.'):
        return True
    return False

def get_email_domain(email: str) -> str:
    email = normalize_email(email)
    if '@' in email:
        return email.split('@', 1)[1]
    return ''
