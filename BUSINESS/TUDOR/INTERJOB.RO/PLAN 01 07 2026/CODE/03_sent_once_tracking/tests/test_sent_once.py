#!/usr/bin/env python3
"""Unit tests for the sent-once tracking system (stdlib unittest, no network)."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sent_once import SentOnceLedger, normalize_email, _parse_ts  # noqa: E402
from groups import group_for, load_group_index  # noqa: E402
import backfill_from_sentjson as bf  # noqa: E402


class NormalizeTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(normalize_email("  Office@Example.RO "), "office@example.ro")

    def test_invalid(self):
        for bad in ["", "not-an-email", "a@b", None, 42, "x@y.z w@v.z"]:
            self.assertIsNone(normalize_email(bad))


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "l.sqlite")
        self.ledger = SentOnceLedger(self.db)

    def tearDown(self):
        self.ledger.close()

    def test_record_and_group_scope(self):
        self.assertTrue(self.ledger.record("a@x.ro", "SILOZURI", "CEREALE", "2026-07-01"))
        # Same group -> suppressed
        self.assertTrue(self.ledger.already_sent("a@x.ro", group="CEREALE"))
        # Different group -> allowed
        self.assertFalse(self.ledger.already_sent("a@x.ro", group="DEFICIT_JOBS"))

    def test_dedup_insert(self):
        self.assertTrue(self.ledger.record("a@x.ro", "C1", "G", "2026-07-01"))
        self.assertFalse(self.ledger.record("a@x.ro", "C1", "G", "2026-07-01"))

    def test_cooldown(self):
        recent = datetime.now(timezone.utc) - timedelta(days=3)
        self.ledger.record("b@x.ro", "C1", "G1", recent)
        now = datetime.now(timezone.utc)
        self.assertTrue(self.ledger.already_sent("b@x.ro", cooldown_days=14, now=now))
        self.assertFalse(self.ledger.already_sent("b@x.ro", cooldown_days=1, now=now))

    def test_filter_new_dedups_and_scopes(self):
        self.ledger.record("dup@x.ro", "SILOZURI", "CEREALE", "2026-07-01")
        emails = ["dup@x.ro", "new@x.ro", "new@x.ro", "bad", "OTHER@X.RO"]
        allowed, skipped = self.ledger.filter_new(emails, "SILOZURI_CEREALE_11JUD", "CEREALE")
        self.assertIn("new@x.ro", allowed)
        self.assertIn("OTHER@X.RO", allowed)
        self.assertIn("dup@x.ro", skipped)  # same group
        self.assertEqual(allowed.count("new@x.ro"), 1)  # in-batch dedup

    def test_stats(self):
        self.ledger.record("a@x.ro", "C1", "G1", "2026-07-01")
        self.ledger.record("a@x.ro", "C2", "G2", "2026-07-02")
        s = self.ledger.stats()
        self.assertEqual(s["unique_emails"], 1)
        self.assertEqual(s["rows"], 2)


class GroupsTest(unittest.TestCase):
    def test_known_and_unknown(self):
        idx = load_group_index()
        self.assertEqual(group_for("SILOZURI", idx), "CEREALE")
        self.assertEqual(group_for("SILOZURI_CEREALE_11JUD", idx), "CEREALE")
        # Unknown campaign dedups only against itself
        self.assertEqual(group_for("BRAND_NEW_CAMP", idx), "BRAND_NEW_CAMP")


class BackfillTest(unittest.TestCase):
    def test_backfill_formats(self):
        tmp = tempfile.mkdtemp()
        base = os.path.join(tmp, "CAMPAIGNS")
        # by_date format
        d1 = os.path.join(base, "SILOZURI", "DATA")
        os.makedirs(d1)
        with open(os.path.join(d1, "sent.json"), "w") as fh:
            json.dump({"total": 2, "by_date": {"2026-06-30": ["a@x.ro", "b@x.ro"]}}, fh)
        # sent/by_email format
        d2 = os.path.join(base, "SUPERMARKETURI", "WORKSPACE")
        os.makedirs(d2)
        with open(os.path.join(d2, "sent_index.json"), "w") as fh:
            json.dump({"sent": ["c@x.ro"], "by_email": {"d@x.ro": {"date": "2026-07-02"}}}, fh)
        db = os.path.join(tmp, "l.sqlite")
        res = bf.backfill(base, db, dry_run=False)
        self.assertEqual(res["records_inserted"], 4)
        led = SentOnceLedger(db)
        self.assertTrue(led.already_sent("a@x.ro", group="CEREALE"))
        self.assertTrue(led.already_sent("d@x.ro", group="COOP_FV"))
        led.close()

    def test_archive_count_by_date_with_emails_list(self):
        # Archived files store by_date as per-day counts (int) plus an emails list.
        tmp = tempfile.mkdtemp()
        d = os.path.join(tmp, "CAMPAIGNS", "DEFICIT_OCUPATII", "DATA")
        os.makedirs(d)
        with open(os.path.join(d, "sent_7ocupatii_brevo.json"), "w") as fh:
            json.dump({"total": 2, "by_date": {"2026-07-11": 2},
                       "emails": ["z@x.ro", "y@x.ro"]}, fh)
        db = os.path.join(tmp, "l.sqlite")
        res = bf.backfill(os.path.join(tmp, "CAMPAIGNS"), db, dry_run=False)
        self.assertEqual(res["records_inserted"], 2)
        led = SentOnceLedger(db)
        self.assertTrue(led.already_sent("z@x.ro", group="DEFICIT_JOBS"))
        led.close()

    def test_dry_run_writes_nothing(self):
        tmp = tempfile.mkdtemp()
        base = os.path.join(tmp, "CAMPAIGNS", "C", "DATA")
        os.makedirs(base)
        with open(os.path.join(base, "sent.json"), "w") as fh:
            json.dump({"by_date": {"2026-06-30": ["a@x.ro"]}}, fh)
        db = os.path.join(tmp, "l.sqlite")
        res = bf.backfill(os.path.join(tmp, "CAMPAIGNS"), db, dry_run=True)
        self.assertTrue(res["dry_run"])
        self.assertFalse(os.path.exists(db))


class ParseTsTest(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(_parse_ts("2026-07-01").year, 2026)
        self.assertEqual(_parse_ts("2026-07-01 10:11:12").hour, 10)
        self.assertIsNotNone(_parse_ts(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
