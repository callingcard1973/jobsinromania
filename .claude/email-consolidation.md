# email-consolidation.md — Phase 2 Code Refactor Plan

Consolidate 100+ laptop scripts → clean raspibig config, add type hints + health check.

## Wave 1: Identify Duplicates (1 day)

**Laptop code audit:**

| File | Loc | Status | Action |
|------|-----|--------|--------|
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\email_accounts.py` | ~150 | Reference only | Keep (local config builder) |
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\email_accounts_prod.py` | ~150 | DUPLICATE | Delete (superseded by send_config.py) |
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\send_mailrelay.py` | ~200 | Unique | Keep (Mailrelay SDK only) |
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\email_pipeline.py` | ~300 | DUPLICATE | Delete (old, replaced by unified sender) |
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\email_pipeline_prod.py` | ~300 | DUPLICATE | Delete (old prod code) |
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\patch_*.py` | ×20 | Config patchers | Archive to `_archive/` (keep for reference, don't use) |
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\verify_*.py` | ×5 | Test utilities | Keep (local testing only) |
| `D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\*_accounts*.py` | ×3 | Config mgmt | Merge → `send_config_builder.py` (single file) |

**Proposed cleanup:**
```
EMAIL/CODE/
├── send_config_builder.py         # merged from *_accounts.py, email_accounts.py
├── send_mailrelay.py              # keep (unique)
├── verify_mailrelay.py            # keep (local test)
├── test_send_sandbox.py           # NEW (Phase 3)
└── _archive/
    ├── email_pipeline.py          # OLD
    ├── email_pipeline_prod.py     # OLD
    ├── email_accounts_prod.py     # OLD (dup)
    └── patch_*.py                 # CONFIG PATCHES (ref only)
```

**Execution:**
```bash
# On laptop
cd D:\MEMORY\CODE\CAMPAIGNS\EMAIL\CODE\
mkdir _archive
mv email_pipeline*.py patch_*.py email_accounts_prod.py _archive/
# Rename email_accounts.py → send_config_builder.py (and add any missing logic from deleted files)
```

---

## Wave 2: Modularize Raspibig send_config.py (2 days)

**Current problem:** SECTORS dict is 2,000+ lines, one giant dict. Hard to diff, easy to miss configs.

**Target:** Break into `config/{sector_name}.json` files, load dynamically.

### Step 1: Create config/ folder structure

```bash
ssh tudor@192.168.100.21
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/
mkdir -p config/{active,archived,templates}
```

### Step 2: Export current sectors → individual JSON files

```python
# Script: export_sectors_to_json.py (run once on raspibig)
import json
from send_config import init, SECTORS

init('/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_config.py')

for sector_name, cfg in SECTORS.items():
    with open(f'config/active/{sector_name}.json', 'w') as f:
        json.dump(cfg, f, indent=2)
    print(f"✓ {sector_name}.json")
```

### Step 3: Refactor send_config.py

**Before (monolithic):**
```python
SECTORS = {
    "DELIVERY_RO_2026": {...},
    "HARGHITA_PHASE_1": {...},
    ... # 30+ more
}
```

**After (modular):**
```python
def load_sectors(config_dir='config'):
    """Load all sector configs from config/*.json"""
    sectors = {}
    for sector_file in Path(config_dir / 'active').glob('*.json'):
        with open(sector_file) as f:
            sector_name = sector_file.stem
            sectors[sector_name] = json.load(f)
    return sectors

# In init():
SECTORS = load_sectors()
```

### Step 4: Add type hints to send_config.py

```python
from typing import Dict, Any, Optional
from pathlib import Path

SectorConfig = Dict[str, Any]
GlobalConfig = Dict[str, Any]

def load_sectors(config_dir: Path = Path('config')) -> Dict[str, SectorConfig]:
    """Load all sector configs from config/*.json"""
    ...

def init(config_path: str) -> None:
    """Initialize globals from config file."""
    global CFG, SECTORS
    CFG: GlobalConfig = load_config(config_path)
    SECTORS: Dict[str, SectorConfig] = load_sectors()
```

---

## Wave 3: Refactor send_providers.py (1.5 days)

**Current:** All providers in one file (450 lines), inconsistent signatures.

**Target:** Consistent interface, type hints, docstrings.

### Step 1: Define provider interface

```python
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any

class EmailProvider(ABC):
    """Abstract email provider interface."""
    
    def __init__(self, config: Dict[str, Any], logger):
        self.config = config
        self.logger = logger
    
    @abstractmethod
    def check_quota(self) -> Tuple[int, int]:
        """Returns (used, limit) for today."""
        pass
    
    @abstractmethod
    def send(self, to_email: str, subject: str, body_html: str, from_email: str) -> Tuple[bool, str]:
        """Send email. Returns (success, message_id or error)."""
        pass
    
    @abstractmethod
    def check_bounce_rate(self) -> float:
        """Return bounce % (0.0-1.0)."""
        pass


class BrevoProvider(EmailProvider):
    """Brevo API provider."""
    
    def check_quota(self) -> Tuple[int, int]:
        """Get used + limit for today."""
        api_key = os.environ.get(self.config.get('sender_key'))
        # ... existing brevo_mid_check() logic
        ...
    
    def send(self, to_email: str, subject: str, body_html: str, from_email: str) -> Tuple[bool, str]:
        """Send via Brevo API."""
        # ... existing send_brevo() logic
        ...
```

### Step 2: Update send_campaign.py dispatch

```python
# Before (long if-elif chain)
if cfg.get('sender_type') == 'mailrelay':
    run_mailrelay_batch(...)
elif cfg.get('sender_type') == 'gmail_only':
    send_gmail(...)
else:
    send_brevo(...)

# After (provider factory)
from send_providers import PROVIDER_CLASSES

provider_class = PROVIDER_CLASSES[cfg.get('sender_type', 'brevo')]
provider = provider_class(cfg, logger)

quota_used, quota_limit = provider.check_quota()
provider.send(to_email, subject, body_html, from_email)
```

---

## Wave 4: Add send_health.py (1 day)

**New file:** Unified health check. Run daily, alert on failures.

```python
#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Email system health check.
Monitors: Brevo quotas, bounce rates, Postfix status, Raspi validation lag.
"""
from typing import Dict, List, Tuple
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

class EmailHealthCheck:
    """Unified email health monitor."""
    
    def __init__(self, config_path: str = 'send_config.py'):
        from send_config import init, SECTORS, BASE_DIR
        init(config_path)
        self.sectors = SECTORS
        self.base_dir = Path(BASE_DIR)
    
    def check_brevo_quota(self) -> Dict[str, Tuple[int, int]]:
        """Check Brevo API usage per sender account."""
        quotas = {}
        for sector, cfg in self.sectors.items():
            if cfg.get('sender_type') != 'brevo':
                continue
            api_key = os.environ.get(cfg.get('sender_key'))
            # curl -s https://api.brevo.com/v3/account -H "api-key: $api_key"
            # Extract: credits, remaining
            ...
        return quotas
    
    def check_bounce_rate(self, hours: int = 24) -> Dict[str, float]:
        """Check bounce % per sector (last N hours)."""
        # SELECT sector, COUNT(*), SUM(bounced) FROM send_log
        # WHERE date >= NOW() - interval '{hours} hours'
        # GROUP BY sector
        ...
        return bounce_rates
    
    def check_postfix_status(self) -> Tuple[bool, str]:
        """Check Postfix is running."""
        result = subprocess.run(['postfix', 'status'], capture_output=True)
        return (result.returncode == 0, result.stdout.decode())
    
    def check_dkim_records(self) -> Dict[str, bool]:
        """Verify DKIM DNS records exist for all domains."""
        # dig +short mail2026._domainkey.{domain} TXT
        # Should return public key
        ...
        return dkim_status
    
    def report(self, format: str = 'text') -> str:
        """Generate health report."""
        checks = {
            'brevo_quota': self.check_brevo_quota(),
            'bounce_rate': self.check_bounce_rate(),
            'postfix': self.check_postfix_status(),
            'dkim': self.check_dkim_records(),
        }
        
        if format == 'json':
            return json.dumps(checks, indent=2, default=str)
        
        # Text format
        lines = ['=== Email Health ===', f'Generated: {datetime.now()}']
        if checks['brevo_quota']:
            lines.append('✓ Brevo quotas OK')
        if max(checks['bounce_rate'].values()) < 0.30:
            lines.append('✓ Bounce rates OK')
        if checks['postfix'][0]:
            lines.append('✓ Postfix running')
        if all(checks['dkim'].values()):
            lines.append('✓ DKIM records live')
        return '\n'.join(lines)

if __name__ == '__main__':
    import sys
    checker = EmailHealthCheck()
    print(checker.report(format=sys.argv[1] if len(sys.argv) > 1 else 'text'))
```

**Cron job (daily check):**
```bash
0 8 * * * /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_health.py json >> /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/health.log
```

---

## Wave 5: Type Hints + Docstrings (1 day)

**Apply to:** send_db.py, send_utils.py (send_providers.py done in Wave 3).

**Example (send_db.py):**

```python
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

def get_contacts(
    db_cfg: Dict[str, str],
    sector: str,
    limit: int = 100,
    exclude_dnc: bool = True,
) -> List[Dict[str, str]]:
    """
    Fetch contacts for campaign.
    
    Args:
        db_cfg: Database config (host, port, dbname, user, password)
        sector: Sector name (e.g., 'HARGHITA_PHASE_3')
        limit: Max contacts to fetch
        exclude_dnc: Skip DNC list
    
    Returns:
        List of contact dicts with keys: email, name, company_name, sector, etc.
    
    Raises:
        psycopg2.Error: If DB query fails
    """
    conn = psycopg2.connect(**db_cfg)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    query = f"""
        SELECT email, name, company_name, sector
        FROM {TABLE_NAME}
        WHERE sector = %s
        {('AND email NOT IN (SELECT email FROM dnc)' if exclude_dnc else '')}
        LIMIT %s
    """
    cur.execute(query, (sector, limit))
    return cur.fetchall()
```

---

## Deliverables (Phase 2)

| Task | Files | Lines | Effort | Owner |
|------|-------|-------|--------|-------|
| Wave 1: Audit + archive duplicates | EMAIL/CODE/_archive/ | — | 0.5d | You |
| Wave 2: Modularize send_config.py | config/*.json, send_config.py | +50, -2000 | 2d | Claude |
| Wave 3: Refactor send_providers.py | send_providers.py | +100 (types+docs) | 1.5d | Claude |
| Wave 4: add send_health.py | send_health.py | ~300 | 1d | Claude |
| Wave 5: Type hints (send_db, send_utils) | send_db.py, send_utils.py | +50 | 1d | Claude |
| **TOTAL** | — | — | **6 days** | — |

---

## Execution Order

1. **Wave 1** (you) — Delete laptop duplicates, archive old configs
2. **Deploy** (you) — SCP cleaned laptop code to raspibig
3. **Wave 2** (Claude) — Modularize send_config.py, test load_sectors()
4. **Wave 3** (Claude) — Provider interface, update dispatch
5. **Wave 4** (Claude) — send_health.py, integrate cron
6. **Wave 5** (Claude) — Type hints, docstrings, mypy check
7. **Verify** (you) — Run send_campaign.py on test sector, confirm health check works

---

## Testing Checklist (per wave)

**Wave 2:**
- [ ] load_sectors() loads all config/*.json files
- [ ] SECTORS dict unchanged (same keys, same values as before)
- [ ] send_campaign.py runs without error

**Wave 3:**
- [ ] BrevoProvider.send() matches old send_brevo()
- [ ] GmailProvider.send() matches old send_gmail()
- [ ] All 6 providers dispatch correctly

**Wave 4:**
- [ ] send_health.py runs without error
- [ ] Reports accurate bounce rates
- [ ] Detects missing DKIM records (cifn.info)

**Wave 5:**
- [ ] `mypy send_config.py send_db.py send_utils.py` → 0 errors
- [ ] `black .` → no reformatting needed
- [ ] `ruff check .` → no violations

---

## Rollback Plan

If any wave breaks send_campaign.py:

```bash
cd /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/
git checkout send_config.py send_providers.py send_db.py send_utils.py
python3 send_campaign.py TEST_SECTOR --limit 5 --dry-run
```

All changes committed per-wave with clear messages:
- `feat: modularize send_config.py into config/*.json`
- `refactor: add EmailProvider interface to send_providers.py`
- `feat: add send_health.py unified health monitor`
- `refactor: add type hints to send_db.py, send_utils.py`
