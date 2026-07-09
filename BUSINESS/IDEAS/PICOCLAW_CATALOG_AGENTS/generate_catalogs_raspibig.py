#!/usr/bin/env python3
"""
Ruleaza pe raspibig. Interogheaza PostgreSQL, genereaza HTML cataloage.
Importa configuratia din generate_catalogs.py.

Folosire:
  scp generate_catalogs.py generate_catalogs_raspibig.py tudor@192.168.100.21:/tmp/
  ssh tudor@192.168.100.21 'cd /tmp && python3 generate_catalogs_raspibig.py'
"""
import os, sys, json
from pathlib import Path

# Adauga directorul curent in path
sys.path.insert(0, str(Path(__file__).parent))
from generate_catalogs import (
    DOMAINS, COUNTRIES, TED_COUNTRIES, ISO3_TO_ISO2,
    save_domain, OUTPUT_DIR
)

try:
    import psycopg2
except ImportError:
    print("EROARE: pip install psycopg2-binary")
    sys.exit(1)

DB = {"host": "localhost", "dbname": "interjob_master", "user": "tudor", "password": "tudor"}


def query_norway(conn, nace_prefixes, limit=500):
    """Interogheaza no_companies_full pe NACE prefix."""
    if not nace_prefixes:
        return []
    conditions = " OR ".join(f"naeringskode1_kode LIKE '{p}%'" for p in nace_prefixes)
    sql = f"""
        SELECT DISTINCT ON (navn) navn as name, forretningsadresse_poststed as city
        FROM no_companies_full
        WHERE ({conditions})
        AND navn IS NOT NULL AND length(navn) > 2
        ORDER BY navn, antallansatte DESC NULLS LAST
        LIMIT {limit}
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [{"name": r[0], "city": r[1] or ""} for r in cur.fetchall()]


def query_romania(conn, caen_prefixes, limit=500):
    """Interogheaza master_romania_companies pe CAEN prefix."""
    if not caen_prefixes:
        return []
    conditions = " OR ".join(f"caen LIKE '{p}%'" for p in caen_prefixes)
    sql = f"""
        SELECT DISTINCT ON (name) name, city
        FROM master_romania_companies
        WHERE ({conditions})
        AND name IS NOT NULL AND length(name) > 2
        AND status IS NULL OR status != 'RADIAT'
        ORDER BY name, employees_count DESC NULLS LAST
        LIMIT {limit}
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [{"name": r[0], "city": r[1] or ""} for r in cur.fetchall()]


def query_ted(conn, cpv_prefixes, country_iso3, limit=500):
    """Interogheaza ted_winners pe CPV prefix + tara."""
    if not cpv_prefixes:
        return []
    conditions = " OR ".join(f"cpv LIKE '{p}%%'" for p in cpv_prefixes)
    sql = f"""
        SELECT DISTINCT ON (contractor) contractor as name, contractor_city as city
        FROM ted_winners
        WHERE ({conditions})
        AND contractor_country = '{country_iso3}'
        AND contractor IS NOT NULL AND length(contractor) > 2
        ORDER BY contractor, contract_value DESC NULLS LAST
        LIMIT {limit}
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [{"name": r[0], "city": r[1] or ""} for r in cur.fetchall()]


def main():
    print("Conectare PostgreSQL...")
    conn = psycopg2.connect(**DB)
    print("OK\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for domain_key, domain_cfg in DOMAINS.items():
        print(f"\n{'='*60}")
        print(f"Generez {domain_cfg['icon']} {domain_key}")
        print(f"{'='*60}")

        country_pages = {}
        employers_by_country = {}

        # Norvegia
        print("  Interoghez Norvegia...")
        no_data = query_norway(conn, domain_cfg.get("no_nace_prefix", []))
        if no_data:
            country_pages["NO"] = {"name": "Norway", "count": len(no_data)}
            employers_by_country["NO"] = no_data
            print(f"    -> {len(no_data)} angajatori")

        # Romania
        print("  Interoghez Romania...")
        ro_data = query_romania(conn, domain_cfg.get("ro_caen_prefix", []))
        if ro_data:
            country_pages["RO"] = {"name": "Romania", "count": len(ro_data)}
            employers_by_country["RO"] = ro_data
            print(f"    -> {len(ro_data)} angajatori")

        # TED winners — per tara
        iso2_to_iso3 = {v: k for k, v in ISO3_TO_ISO2.items() if len(k) == 3}
        for iso2, country_name in TED_COUNTRIES.items():
            iso3 = iso2_to_iso3.get(iso2)
            if not iso3:
                continue
            print(f"  Interoghez TED {country_name}...")
            ted_data = query_ted(conn, domain_cfg.get("ted_cpv_prefix", []), iso3)
            # Adauga si varianta ISO2 (unele tari au RO nu ROU)
            if not ted_data and iso2 != iso3:
                ted_data = query_ted(conn, domain_cfg.get("ted_cpv_prefix", []), iso2)
            if ted_data:
                # Daca tara exista deja (RO din romania + TED), combina
                if iso2 in employers_by_country:
                    existing = {e["name"] for e in employers_by_country[iso2]}
                    new = [e for e in ted_data if e["name"] not in existing]
                    employers_by_country[iso2].extend(new[:200])
                    country_pages[iso2]["count"] = len(employers_by_country[iso2])
                else:
                    country_pages[iso2] = {"name": country_name, "count": len(ted_data)}
                    employers_by_country[iso2] = ted_data
                print(f"    -> {len(ted_data)} angajatori TED")

        # Salveaza HTML
        if country_pages:
            save_domain(domain_key, domain_cfg, country_pages, employers_by_country)
        else:
            print(f"  SKIP {domain_key} — zero date")

    conn.close()

    # Sumar
    print(f"\n{'='*60}")
    print("SUMAR GENERARE")
    print(f"{'='*60}")
    total_pages = 0
    for d in OUTPUT_DIR.iterdir():
        if d.is_dir():
            pages = len([p for p in d.iterdir() if p.is_dir()])
            total_pages += pages
            print(f"  {d.name}: {pages} pagini tari")
    print(f"\nTotal: {total_pages} pagini generate in {OUTPUT_DIR}")
    print(f"Urmatorul pas: deploy pe A2 Hosting cu cPanel API")


if __name__ == "__main__":
    main()
