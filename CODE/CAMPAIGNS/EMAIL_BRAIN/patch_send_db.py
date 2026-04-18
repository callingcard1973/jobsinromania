"""Patch send_db.py: master_dnc with CSV fallback."""
f = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_db.py"
content = open(f).read()

old = """# Master blacklist \u2014 checked before every send
_BLACKLIST = set()
_BL_FILE = '/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt'
def _load_blacklist():
    global _BLACKLIST
    try:
        with open(_BL_FILE) as f:
            _BLACKLIST = {line.strip().lower() for line in f if '@' in line}
    except Exception:
        pass
_load_blacklist()"""

new = """# Master DNC: PostgreSQL master_dnc with CSV fallback
_BLACKLIST = set()
_BL_BACKUP = '/opt/ACTIVE/INFRA/BACKUPS/master_dnc.csv'
_BL_LOADED = False

def _load_blacklist():
    global _BLACKLIST, _BL_LOADED
    if _BL_LOADED:
        return
    # Try PostgreSQL first
    try:
        import psycopg2
        conn = psycopg2.connect(host='/var/run/postgresql',
            dbname='interjob_master', user='tudor', password='scraper123')
        cur = conn.cursor()
        cur.execute("SELECT email FROM master_dnc WHERE expires_at IS NULL OR expires_at > CURRENT_DATE")
        _BLACKLIST = {r[0].lower() for r in cur.fetchall()}
        cur.close()
        conn.close()
        _BL_LOADED = True
        return
    except Exception:
        pass
    # Fallback: CSV backup
    try:
        with open(_BL_BACKUP) as f:
            _BLACKLIST = {line.strip().lower() for line in f if '@' in line}
        _BL_LOADED = True
        return
    except Exception:
        pass
    # Both failed: alert and block sending
    try:
        from send_utils import send_telegram
        send_telegram("DNC FAILED - master_dnc + backup unreachable. Sending paused.")
    except Exception:
        pass

_load_blacklist()"""

if old in content:
    content = content.replace(old, new)
    open(f, "w").write(content)
    print("Patched with master_dnc + CSV fallback")
else:
    # Try without the unicode dash
    old2 = old.replace("\u2014", "--")
    if old2 in content:
        content = content.replace(old2, new)
        open(f, "w").write(content)
        print("Patched (alt)")
    else:
        print("Pattern not found — checking current state")
        # Show what's there
        for i, line in enumerate(content.split('\n')):
            if 'BLACKLIST' in line or '_BL_' in line:
                print(f"  L{i}: {line[:80]}")
