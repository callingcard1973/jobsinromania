"""Pull fresh jobs from raspibig job_posts. Sources: eures_norway (Norway), anofm (Romania)."""
import subprocess
import json
import sys
import io

if __name__ == "__main__" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

RASPI = "tudor@192.168.100.21"
NORWAY_PATTERN = r"vi søker|vi soker|vil du|deltid|heltid|norsk|norge|oslo|bergen|stavanger|trondheim"


def _query(where, limit):
    sql = (
        "SELECT json_agg(row_to_json(t)) FROM ("
        "SELECT job_id, job_title, company, location, salary, positions, sector, posted_at::text "
        f"FROM job_posts WHERE {where} AND job_title IS NOT NULL "
        f"ORDER BY posted_at DESC NULLS LAST LIMIT {limit}) t;"
    )
    cmd = ["ssh", RASPI, f"sudo -u postgres psql -d interjob_master -t -A -c \"{sql}\""]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    raw = result.stdout.strip()
    return json.loads(raw) if raw else []


def fetch_norway_jobs(limit=3):
    return _query(f"source='eures' AND job_title ~* '{NORWAY_PATTERN}'", limit) or []


def fetch_anofm_jobs(limit=3, sector=None):
    where = "source='anofm'"
    if sector:
        where += f" AND sector ILIKE '%{sector}%'"
    return _query(where, limit) or []


def fetch(source="norway", limit=3, sector=None):
    if source == "norway":
        return fetch_norway_jobs(limit)
    if source == "anofm":
        return fetch_anofm_jobs(limit, sector)
    raise ValueError(f"Unknown source: {source}")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "norway"
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    sec = sys.argv[3] if len(sys.argv) > 3 else None
    print(json.dumps(fetch(src, lim, sec), indent=2, ensure_ascii=False))
