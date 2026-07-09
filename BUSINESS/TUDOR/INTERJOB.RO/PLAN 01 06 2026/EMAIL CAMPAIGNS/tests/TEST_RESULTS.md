# Test Run — 2026-06-20

Email campaign reply/suppression test suite. Run on raspibig (production hub, `interjob_master` DB).

## Results

| Test | Result | Exit | Notes |
|------|--------|------|-------|
| `test_classifier.py` | **16/16 passed** | 0 | Reply classifier regression — guards the opt-out/bounce false-positive bug class |
| `test_suppression.py` | **PASS** | 0 | Opt-out (norway_dnc) + sent/bounce (norway_send_log) actually exclude a contact via the real `send_norway.get_contacts()` path |

### Raw output
```
===== CLASSIFIER REGRESSION =====
classifier regression: 16/16 passed
exit=0

===== SUPPRESSION INTEGRATION =====
baseline eligible : True  (expect True)
after norway_dnc  : False   (expect False)
after send_log    : False   (expect False)
SUPPRESSION: PASS
exit=0
```

## Cross-machine (classifier)
| Machine | Result |
|---------|--------|
| laptop | 16/16 |
| raspibig (.21) | 16/16 |
| raspi (.20) | 16/16 |

`test_suppression.py` is raspibig-only by design (integration test against the live DB + `send_norway`).

## How to re-run
- Classifier (anywhere): `python3 tests/test_classifier.py`
- Suppression (raspibig): `cd NORWAY && python3 ../tests/test_suppression.py`
