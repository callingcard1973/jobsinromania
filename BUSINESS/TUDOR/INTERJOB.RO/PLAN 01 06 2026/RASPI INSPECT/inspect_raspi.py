#!/usr/bin/env python3
"""Inspect raspi (192.168.100.20) — the Romania ops hub. Read-only by default.

Codifies the 2026-06-26 audit: crontab dup + syntax validation, ANOFM pipeline
freshness, failed units, DB row counts, /tmp pressure. ASCII-only output.
Run: python inspect_raspi.py   (laptop, via plink). --raw dumps each section.
"""
import subprocess, sys, re

HOST = "tudor@192.168.100.20"
PLINK = r"C:\Program Files\PuTTY\plink.exe"
PW = "RASPI_PW_REDACTED"  # raspi shares raspibig password; do not commit a different secret

# (label, remote command) — all read-only
PROBES = [
    ("HOST", "hostname; uptime"),
    ("CRON", "crontab -l"),
    ("FAILED_UNITS", "systemctl --failed --no-pager --plain | grep -E 'failed' || echo none"),
    ("ANOFM_JOBS", "PGHOST=localhost psql -U tudor -d anofm_db -tAc 'select count(*) from ij_jobs'"),
    ("ANOFM_SENDLOG", "PGHOST=localhost psql -U tudor -d anofm -tAc \"select count(*) from send_log\""),
    ("ANOFM_DNC", "PGHOST=localhost psql -U tudor -d anofm -tAc \"select count(*) from dnc\""),
    ("ANOFM_LASTSEND", "grep -hE 'sent=' /opt/ACTIVE/INFRA/LOGS/anofm_orchestrator.log 2>/dev/null | tail -3 || echo none"),
    ("ANOFM_REJECTS_TODAY", "grep -F \"$(date +%F)\" /opt/ACTIVE/INFRA/LOGS/anofm_orchestrator.log 2>/dev/null | grep -c 'not valid in to'"),
    ("ANOFM_PARKED_LAST", "p=$(grep -hE 'parked [0-9]+ malformed' /opt/ACTIVE/INFRA/LOGS/anofm_orchestrator.log 2>/dev/null | tail -1); echo \"${p:-none}\""),
    ("TMP_PRESSURE", "ls /tmp | wc -l; df -h /tmp | tail -1"),
]


def ssh(cmd):
    """Run one remote command over plink, return (stdout, rc)."""
    p = subprocess.run([PLINK, "-batch", "-pw", PW, HOST, cmd],
                       capture_output=True, text=True, timeout=90)
    return p.stdout.strip(), p.returncode


def validate_cron(raw):
    """Flag duplicate active lines and malformed schedules (HH:MM in minute field)."""
    active = [ln for ln in raw.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    dups = sorted({ln for ln in active if active.count(ln) > 1})
    malformed = [ln for ln in active if re.match(r"^\s*\d{1,2}:\d{2}\s", ln)]
    return active, dups, malformed


def main():
    raw = "--raw" in sys.argv
    findings = []
    sections = {}
    for label, cmd in PROBES:
        out, rc = ssh(cmd)
        sections[label] = out
        if raw:
            print(f"\n===== {label} (rc={rc}) =====\n{out}")

    print("\n================ RASPI ROMANIA HEALTH ================")
    print(sections.get("HOST", "?").splitlines()[0] if sections.get("HOST") else "UNREACHABLE")

    active, dups, malformed = validate_cron(sections.get("CRON", ""))
    print(f"\nCRON: {len(active)} active lines")
    if dups:
        findings.append(f"{len(dups)} DUPLICATE cron line(s) -> double execution")
        for d in dups[:5]:
            print(f"  DUP: {d[:90]}")
    if malformed:
        findings.append(f"{len(malformed)} MALFORMED cron schedule(s) (HH:MM in minute field -> never runs)")
        for m in malformed[:5]:
            print(f"  BAD SCHED: {m[:90]}")
    if not dups and not malformed:
        print("  OK - no duplicates, no malformed schedules")

    fu = sections.get("FAILED_UNITS", "")
    if fu and fu != "none":
        findings.append(f"failed systemd units: {fu.splitlines()[0][:60]}")
    print(f"\nFAILED UNITS: {fu or 'none'}")

    print("\nANOFM PIPELINE (Romania):")
    print(f"  ij_jobs   : {sections.get('ANOFM_JOBS', '?')}")
    print(f"  send_log  : {sections.get('ANOFM_SENDLOG', '?')}")
    print(f"  dnc       : {sections.get('ANOFM_DNC', '?')}")
    print("  last sends:\n    " + (sections.get("ANOFM_LASTSEND", "none").replace("\n", "\n    ")))

    rej = (sections.get("ANOFM_REJECTS_TODAY", "0") or "0").strip()
    try:
        rej_n = int(rej.splitlines()[0])
    except (ValueError, IndexError):
        rej_n = 0
    if rej_n > 0:
        findings.append(f"{rej_n} malformed-email rejection(s) today (HTTP_400 'not valid in to') -> validator not applied / regressed")
    print(f"  rejects today: {rej_n} (malformed 'not valid in to')")
    print(f"  parked (last): {sections.get('ANOFM_PARKED_LAST', 'none')}")

    print(f"\nTMP: {sections.get('TMP_PRESSURE', '?')}")

    print("\n---------------- SUMMARY ----------------")
    if findings:
        for i, f in enumerate(findings, 1):
            print(f"  {i}. {f}")
        sys.exit(1)
    print("  ALL CLEAR")
    sys.exit(0)


if __name__ == "__main__":
    main()
