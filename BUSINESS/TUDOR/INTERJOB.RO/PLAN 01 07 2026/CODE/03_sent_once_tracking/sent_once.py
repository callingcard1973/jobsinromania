#!/usr/bin/env python3
"""Sent-once ledger: cross-campaign email suppression (group + cooldown)."""
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

DEFAULT_DB = os.environ.get(
    "SENT_ONCE_DB", "/opt/ACTIVE/EMAIL/CAMPAIGNS/global_sent_ledger.sqlite"
)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def normalize_email(value):
    """Lowercase/trim; return None when not a valid single address."""
    if not isinstance(value, str):
        return None
    e = value.strip().lower()
    return e if _EMAIL_RE.match(e) else None


def _parse_ts(ts):
    """Accept ISO datetime, YYYY-MM-DD, or None -> now (UTC, tz-aware)."""
    if ts is None:
        return datetime.now(timezone.utc)
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    s = str(ts).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s, fmt)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # Last resort: fromisoformat (handles many variants)
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


class SentOnceLedger:
    """SQLite-backed record of (email, campaign, group, ts) sends.

    Suppression is intentionally soft and scoped, NOT "one email ever":
    - group scope: a lead is contacted once per topic group.
    - cooldown: regardless of group, not re-contacted within N days.
    DNC stays a separate hard-suppression layer.
    """

    def __init__(self, db_path=DEFAULT_DB):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sent (
                email    TEXT NOT NULL,
                campaign TEXT NOT NULL,
                grp      TEXT NOT NULL,
                ts       TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sent_email ON sent(email);
            CREATE INDEX IF NOT EXISTS idx_sent_grp   ON sent(email, grp);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sent_uniq
                ON sent(email, campaign, ts);
            """
        )
        self.conn.commit()

    def record(self, email, campaign, group, ts=None):
        """Record one send. Returns True if inserted, False if duplicate."""
        e = normalize_email(email)
        if e is None:
            return False
        ts_iso = _parse_ts(ts).isoformat()
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO sent(email,campaign,grp,ts) VALUES (?,?,?,?)",
            (e, str(campaign), str(group), ts_iso),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def record_many(self, rows):
        """rows: iterable of (email, campaign, group, ts). Returns inserted count."""
        n = 0
        payload = []
        for email, campaign, group, ts in rows:
            e = normalize_email(email)
            if e is None:
                continue
            payload.append((e, str(campaign), str(group), _parse_ts(ts).isoformat()))
        if not payload:
            return 0
        cur = self.conn.executemany(
            "INSERT OR IGNORE INTO sent(email,campaign,grp,ts) VALUES (?,?,?,?)",
            payload,
        )
        self.conn.commit()
        n = cur.rowcount if cur.rowcount is not None else 0
        return n

    def already_sent(self, email, group=None, cooldown_days=None, now=None):
        """True if email was contacted in `group`, or within `cooldown_days`."""
        e = normalize_email(email)
        if e is None:
            return False
        if group is not None:
            row = self.conn.execute(
                "SELECT 1 FROM sent WHERE email=? AND grp=? LIMIT 1", (e, str(group))
            ).fetchone()
            if row:
                return True
        if cooldown_days is not None:
            ref = _parse_ts(now) if now is not None else datetime.now(timezone.utc)
            cutoff = (ref - timedelta(days=int(cooldown_days))).isoformat()
            row = self.conn.execute(
                "SELECT 1 FROM sent WHERE email=? AND ts>=? LIMIT 1", (e, cutoff)
            ).fetchone()
            if row:
                return True
        return False

    def filter_new(self, emails, campaign, group, cooldown_days=None, now=None):
        """Split emails into (allowed, skipped) without recording them."""
        allowed, skipped = [], []
        seen = set()
        for raw in emails:
            e = normalize_email(raw)
            if e is None or e in seen:
                skipped.append(raw)
                continue
            seen.add(e)
            if self.already_sent(e, group=group, cooldown_days=cooldown_days, now=now):
                skipped.append(raw)
            else:
                allowed.append(raw)
        return allowed, skipped

    def stats(self):
        total = self.conn.execute("SELECT COUNT(*) FROM sent").fetchone()[0]
        uniq = self.conn.execute(
            "SELECT COUNT(DISTINCT email) FROM sent"
        ).fetchone()[0]
        groups = self.conn.execute(
            "SELECT COUNT(DISTINCT grp) FROM sent"
        ).fetchone()[0]
        return {"rows": total, "unique_emails": uniq, "groups": groups}

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
