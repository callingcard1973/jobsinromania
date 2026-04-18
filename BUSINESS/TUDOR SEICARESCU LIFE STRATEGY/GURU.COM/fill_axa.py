#!/usr/bin/env python3
"""Fill axa/domeniu/program on anunturi from proiecte via cod_smis JOIN."""
# --
import psycopg2

DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql"}

def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    # Add columns if missing
    for col in ['axa', 'domeniu_interventie', 'program_operational']:
        cur.execute(f"ALTER TABLE beneficiari_privati ADD COLUMN IF NOT EXISTS {col} TEXT DEFAULT ''")
    conn.commit()

    # Count what needs filling
    cur.execute("SELECT COUNT(*) FROM beneficiari_privati WHERE cod_smis <> '' AND (axa IS NULL OR axa = '')")
    need = cur.fetchone()[0]
    print(f"Anunturi needing axa fill: {need}")

    # Fill from proiecte JOIN
    cur.execute("""
        UPDATE beneficiari_privati a SET
            axa = p.axa,
            domeniu_interventie = p.domeniu_interventie,
            program_operational = p.program_operational
        FROM proiecte p
        WHERE a.cod_smis = p.cod_smis
        AND a.cod_smis <> ''
        AND p.axa <> ''
        AND (a.axa IS NULL OR a.axa = '')
    """)
    filled = cur.rowcount
    conn.commit()

    # Stats
    cur.execute("SELECT COUNT(*) FROM beneficiari_privati WHERE axa <> ''")
    total_axa = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM beneficiari_privati WHERE cod_smis <> ''")
    total_smis = cur.fetchone()[0]
    conn.close()

    print(f"Filled: {filled}")
    print(f"Total with axa: {total_axa} / {total_smis} with SMIS")

if __name__ == "__main__":
    main()
