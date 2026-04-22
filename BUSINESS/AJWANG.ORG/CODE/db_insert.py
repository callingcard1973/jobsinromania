"""
Insert/upsert africa_countries data into interjob_master on raspibig.
Connects via SSH tunnel using subprocess + psql.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "DATA"
COUNTRIES_JSON = DATA_DIR / "countries.json"

SSH_HOST = "tudor@192.168.100.21"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS africa_countries (
    iso2 VARCHAR(2) PRIMARY KEY,
    iso3 VARCHAR(3),
    name TEXT,
    region TEXT,
    capital TEXT,
    currency TEXT,
    language TEXT,
    gdp_usd NUMERIC,
    gdp_per_capita NUMERIC,
    gdp_growth_pct NUMERIC,
    population BIGINT,
    ease_of_business NUMERIC,
    exports_usd NUMERIC,
    imports_usd NUMERIC,
    inflation_pct NUMERIC,
    unemployment_pct NUMERIC,
    cpi_score INTEGER,
    cpi_rank INTEGER,
    visa_free_count INTEGER,
    voa_count INTEGER,
    evisa_count INTEGER,
    visa_required_count INTEGER,
    schengen_access TEXT,
    treaty_count INTEGER,
    treaties JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);
"""


def val(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, str):
        escaped = v.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(v, (list, dict)):
        escaped = json.dumps(v, ensure_ascii=False).replace("'", "''")
        return f"'{escaped}'"
    return str(v)


def build_upsert_sql(profiles: list[dict]) -> str:
    lines = [CREATE_SQL, ""]
    for p in profiles:
        lines.append(f"""
INSERT INTO africa_countries (
    iso2, iso3, name, region, capital, currency, language,
    gdp_usd, gdp_per_capita, gdp_growth_pct, population,
    ease_of_business, exports_usd, imports_usd,
    inflation_pct, unemployment_pct,
    cpi_score, cpi_rank,
    visa_free_count, voa_count, evisa_count, visa_required_count, schengen_access,
    treaty_count, treaties, updated_at
) VALUES (
    {val(p.get('iso2'))}, {val(p.get('iso3'))}, {val(p.get('name'))},
    {val(p.get('region'))}, {val(p.get('capital'))}, {val(p.get('currency'))},
    {val(p.get('language'))},
    {val(p.get('gdp_usd'))}, {val(p.get('gdp_per_capita'))}, {val(p.get('gdp_growth_pct'))},
    {val(p.get('population'))},
    {val(p.get('ease_of_business'))}, {val(p.get('exports_usd'))}, {val(p.get('imports_usd'))},
    {val(p.get('inflation_pct'))}, {val(p.get('unemployment_pct'))},
    {val(p.get('cpi_score'))}, {val(p.get('cpi_rank'))},
    {val(p.get('visa_free_count'))}, {val(p.get('voa_count'))},
    {val(p.get('evisa_count'))}, {val(p.get('visa_required_count'))},
    {val(p.get('schengen_access'))},
    {val(p.get('treaty_count', 0))}, {val(p.get('treaties', []))},
    NOW()
)
ON CONFLICT (iso2) DO UPDATE SET
    iso3 = EXCLUDED.iso3,
    name = EXCLUDED.name,
    region = EXCLUDED.region,
    capital = EXCLUDED.capital,
    currency = EXCLUDED.currency,
    language = EXCLUDED.language,
    gdp_usd = EXCLUDED.gdp_usd,
    gdp_per_capita = EXCLUDED.gdp_per_capita,
    gdp_growth_pct = EXCLUDED.gdp_growth_pct,
    population = EXCLUDED.population,
    ease_of_business = EXCLUDED.ease_of_business,
    exports_usd = EXCLUDED.exports_usd,
    imports_usd = EXCLUDED.imports_usd,
    inflation_pct = EXCLUDED.inflation_pct,
    unemployment_pct = EXCLUDED.unemployment_pct,
    cpi_score = EXCLUDED.cpi_score,
    cpi_rank = EXCLUDED.cpi_rank,
    visa_free_count = EXCLUDED.visa_free_count,
    voa_count = EXCLUDED.voa_count,
    evisa_count = EXCLUDED.evisa_count,
    visa_required_count = EXCLUDED.visa_required_count,
    schengen_access = EXCLUDED.schengen_access,
    treaty_count = EXCLUDED.treaty_count,
    treaties = EXCLUDED.treaties,
    updated_at = NOW();
""")
    return "\n".join(lines)


def run_on_raspibig(sql: str) -> None:
    """Write SQL to temp file, SCP to raspibig, run via psql."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False, encoding="utf-8") as f:
        f.write(sql)
        tmp_path = f.name

    remote_path = "/tmp/africa_countries_import.sql"

    # SCP the SQL file
    print("Uploading SQL to raspibig...")
    scp_result = subprocess.run(
        ["scp", tmp_path, f"{SSH_HOST}:{remote_path}"],
        capture_output=True, text=True
    )
    if scp_result.returncode != 0:
        print(f"SCP failed: {scp_result.stderr}")
        sys.exit(1)

    # Run psql on raspibig — try 'postgres' user first, then 'tudor'
    output = ""
    for pg_user in ["postgres", "tudor"]:
        print(f"Running psql as {pg_user}...")
        ssh_cmd = f"psql -U {pg_user} -d interjob_master -f {remote_path} 2>&1"
        result = subprocess.run(
            ["ssh", SSH_HOST, ssh_cmd],
            capture_output=True, text=True
        )
        output = result.stdout + result.stderr
        if result.returncode == 0 or "INSERT" in output:
            print(output[-2000:])  # last 2000 chars
            break
        print(f"  {pg_user} failed, trying next...")
    else:
        print("All pg users failed. Output:")
        print(output)
        sys.exit(1)

    print("\nDB insert complete.")


def main() -> None:
    profiles = json.loads(COUNTRIES_JSON.read_text(encoding="utf-8"))
    print(f"Loaded {len(profiles)} profiles from {COUNTRIES_JSON}")

    sql = build_upsert_sql(profiles)
    run_on_raspibig(sql)

    # Verify count on raspibig
    verify_cmd = (
        "psql -U postgres -d interjob_master -c 'SELECT COUNT(*) FROM africa_countries;' 2>/dev/null"
        " || psql -U tudor -d interjob_master -c 'SELECT COUNT(*) FROM africa_countries;'"
    )
    result = subprocess.run(["ssh", SSH_HOST, verify_cmd], capture_output=True, text=True)
    print("Verify:", result.stdout.strip())


if __name__ == "__main__":
    main()
