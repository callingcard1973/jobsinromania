from __future__ import annotations

import csv
import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

import psycopg2
import psycopg2.extras


REMOTE_DIR = Path('/opt/ACTIVE/DB/ASOCIATII/ASOC_PROP')
REGISTRY_FILE = REMOTE_DIR / 'ONG_REGISTRU_NATIONAL.tsv'
SHORTLIST_FILE = REMOTE_DIR / 'ONG_SHORTLIST_5000.tsv'

REGISTRY_TABLE = 'ong_registry_mj'
SHORTLIST_TABLE = 'ong_shortlist_5000_mj'

SHORTLIST_FIELDS = [
    'priority_rank',
    'priority_score',
    'priority_reason',
    'judet_rank_active',
    'localitate_total_active',
    'judet_cheie',
    'localitate_cheie',
]

REGISTRY_FIELDS = [
    'categorie',
    'denumire',
    'numar_registru_national',
    'stare_actuala',
    'status_normalizat',
    'activ',
    'sediu_schimbat',
    'instanta_transfer',
    'tara',
    'judet',
    'localitate',
    'adresa',
    'scop_initial',
    'scop_modificari',
    'hg_utilitate_publica',
    'data_hg_utilitate_publica',
    'sursa_fisier',
    'sursa_url',
    'sursa_data_actualizare',
]

ENRICHMENT_FIELDS = [
    'denumire_key',
    'denumire_core_key',
    'judet_key',
    'localitate_key',
    'matched_company_id',
    'matched_match_type',
    'matched_match_score',
    'matched_cui',
    'matched_company_name',
    'matched_county',
    'matched_city',
    'matched_address',
    'matched_email',
    'matched_phone',
    'matched_website',
    'matched_caen',
    'matched_sector',
    'matched_sector_name',
    'matched_employees',
    'matched_revenue',
    'matched_status_anaf',
    'matched_is_active',
    'matched_is_vat_payer',
    'matched_lead_score',
    'matched_data_completeness',
    'matched_source',
    'imported_at',
]

ENTITY_STOPWORDS = {
    'ASOCIATIA', 'ASOCIATIE', 'ASOCIATII', 'ASOCIATIILOR',
    'FUNDATIA', 'FUNDATIE', 'FUNDATII', 'FUNDATIILOR', 'FUNDATIEI',
    'FEDERATIA', 'FEDERATIE', 'FEDERATII', 'FEDERATIILOR', 'FEDERATIEI',
    'UNIUNEA', 'UNIUNE', 'UNIUNII', 'UNIUNILE',
    'ORGANIZATIA', 'ORGANIZATIE', 'ORGANIZATII', 'ORGANIZATIILOR',
    'ONG', 'O', 'N', 'G',
}


def normalize_ascii(value: str) -> str:
    text = (value or '').upper()
    return (
        text.replace('Ă', 'A')
        .replace('Â', 'A')
        .replace('Î', 'I')
        .replace('Ș', 'S')
        .replace('Ş', 'S')
        .replace('Ț', 'T')
        .replace('Ţ', 'T')
    )


def words(value: str) -> list[str]:
    text = normalize_ascii(value)
    text = re.sub(r'[^A-Z0-9]+', ' ', text)
    return [token for token in text.split() if token]


def full_key(value: str) -> str:
    return ''.join(words(value))


def core_key(value: str) -> str:
    tokens = [token for token in words(value) if token not in ENTITY_STOPWORDS]
    return ''.join(tokens) or ''.join(words(value))


def parse_bool(value: str) -> bool | None:
    text = str(value or '').strip().lower()
    if text in {'1', 'true', 't', 'yes'}:
        return True
    if text in {'0', 'false', 'f', 'no'}:
        return False
    return None


def parse_int(value: str) -> int | None:
    text = str(value or '').strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_numeric(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    return text or None


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def connect(dbname: str):
    return psycopg2.connect(dbname=dbname, user='tudor')


def create_table(conn, table_name: str, include_shortlist_fields: bool) -> None:
    source_columns = []
    if include_shortlist_fields:
        source_columns.extend([
            'priority_rank integer',
            'priority_score integer',
            'priority_reason text',
            'judet_rank_active integer',
            'localitate_total_active integer',
            'judet_cheie text',
            'localitate_cheie text',
        ])
    source_columns.extend([
        'categorie text',
        'denumire text',
        'numar_registru_national text',
        'stare_actuala text',
        'status_normalizat text',
        'activ boolean',
        'sediu_schimbat text',
        'instanta_transfer text',
        'tara text',
        'judet text',
        'localitate text',
        'adresa text',
        'scop_initial text',
        'scop_modificari text',
        'hg_utilitate_publica text',
        'data_hg_utilitate_publica text',
        'sursa_fisier text',
        'sursa_url text',
        'sursa_data_actualizare text',
    ])
    enrichment_columns = [
        'denumire_key text',
        'denumire_core_key text',
        'judet_key text',
        'localitate_key text',
        'matched_company_id integer',
        'matched_match_type text',
        'matched_match_score integer',
        'matched_cui text',
        'matched_company_name text',
        'matched_county text',
        'matched_city text',
        'matched_address text',
        'matched_email text',
        'matched_phone text',
        'matched_website text',
        'matched_caen text',
        'matched_sector text',
        'matched_sector_name text',
        'matched_employees integer',
        'matched_revenue numeric',
        'matched_status_anaf text',
        'matched_is_active boolean',
        'matched_is_vat_payer boolean',
        'matched_lead_score integer',
        'matched_data_completeness integer',
        'matched_source text',
        'imported_at timestamp without time zone default now()'
    ]
    sql = f"""
    drop table if exists {table_name};
    create table {table_name} (
        id bigserial primary key,
        {', '.join(source_columns + enrichment_columns)}
    );
    create index {table_name}_den_key_idx on {table_name}(denumire_key);
    create index {table_name}_core_key_idx on {table_name}(denumire_core_key);
    create index {table_name}_company_idx on {table_name}(matched_company_id);
    create index {table_name}_email_idx on {table_name}(matched_email);
    """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def base_candidate(row: dict[str, object], db_kind: str) -> dict[str, object]:
    return {
        'matched_company_id': row['id'],
        'matched_cui': row['cui'],
        'matched_company_name': row['company_name'],
        'matched_county': row['county'],
        'matched_city': row['city'],
        'matched_address': row['address'],
        'matched_email': row['email'],
        'matched_phone': row['phone'],
        'matched_website': row['website'],
        'matched_caen': row['caen'],
        'matched_sector': row['sector'],
        'matched_sector_name': row['sector_name'],
        'matched_employees': row['employees'],
        'matched_revenue': row['revenue_ron'],
        'matched_status_anaf': row['status_anaf'],
        'matched_is_active': row['is_active'],
        'matched_is_vat_payer': row['is_vat_payer'],
        'matched_lead_score': row['lead_score'],
        'matched_data_completeness': row['data_completeness'],
        'matched_source': f'{db_kind}.companies',
        'county_key': full_key(row['county']),
        'city_key': full_key(row['city']),
        'company_full_key': full_key(row['company_name']),
        'company_core_key': core_key(row['company_name']),
    }


def fetch_company_indexes(conn, db_kind: str, wanted_full: set[str], wanted_core: set[str], wanted_prefixes: set[str]):
    indexes = {
        'full': defaultdict(list),
        'core': defaultdict(list),
        'prefix': defaultdict(list),
    }

    if db_kind == 'romania':
        sql = """
            select id, cui::text as cui, company_name, county, city, address,
                   coalesce(email, email_2) as email,
                   coalesce(phone, phone_2) as phone,
                   website, caen, sector, null::text as sector_name,
                   employees, revenue_ron, status_anaf, is_active,
                   is_vat_payer, lead_score, data_completeness
            from companies
        """
    else:
        sql = """
            select id, cui, name as company_name, null::text as county, city, address,
                   email, phone, website, null::text as caen, sector,
                   sector_name, employees_count as employees, revenue as revenue_ron,
                   null::text as status_anaf, null::boolean as is_active,
                   null::boolean as is_vat_payer, lead_score,
                   null::integer as data_completeness
            from companies
            where country = 'RO'
        """

    with conn.cursor(name=f'{db_kind}_companies', cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.itersize = 10000
        cur.execute(sql)
        for row in cur:
            candidate = base_candidate(row, db_kind)
            full = candidate['company_full_key']
            core = candidate['company_core_key']
            prefix = (core or full)[:8]
            if not full:
                continue
            if full in wanted_full:
                indexes['full'][full].append(candidate)
            if core in wanted_core:
                indexes['core'][core].append(candidate)
            if prefix and prefix in wanted_prefixes:
                indexes['prefix'][prefix].append(candidate)
    return indexes


def rank_candidate(candidate: dict[str, object], county_key: str, city_key: str) -> tuple[int, int, int, int, int]:
    county_match = int(bool(county_key) and candidate['county_key'] == county_key)
    city_match = int(bool(city_key) and candidate['city_key'] == city_key)
    contact_score = int(bool(candidate['matched_email'])) + int(bool(candidate['matched_phone'])) + int(bool(candidate['matched_website']))
    completeness = int(candidate['matched_data_completeness'] or 0)
    lead_score = int(candidate['matched_lead_score'] or 0)
    return (county_match, city_match, contact_score, completeness, lead_score)


def choose_best(candidates: list[dict[str, object]], county_key: str, city_key: str, match_type: str, base_score: int) -> dict[str, object]:
    best = max(candidates, key=lambda cand: rank_candidate(cand, county_key, city_key))
    county_match = int(bool(county_key) and best['county_key'] == county_key)
    city_match = int(bool(city_key) and best['city_key'] == city_key)
    return {
        **best,
        'matched_match_type': match_type,
        'matched_match_score': base_score + county_match * 3 + city_match * 2,
    }


def fuzzy_candidate(query_core: str, candidates: list[dict[str, object]], county_key: str, city_key: str) -> dict[str, object] | None:
    best = None
    best_score = 0.0
    seen_ids = set()

    for candidate in candidates:
        company_id = candidate['matched_company_id']
        if company_id in seen_ids:
            continue
        seen_ids.add(company_id)
        target = candidate['company_core_key'] or candidate['company_full_key']
        if not target:
            continue
        ratio = SequenceMatcher(None, query_core, target).ratio()
        if candidate['county_key'] and county_key and candidate['county_key'] == county_key:
            ratio += 0.03
        if candidate['city_key'] and city_key and candidate['city_key'] == city_key:
            ratio += 0.03
        if ratio > best_score:
            best_score = ratio
            best = candidate

    if not best:
        return None

    threshold = 0.93
    if best['county_key'] == county_key or best['city_key'] == city_key:
        threshold = 0.88
    if len(query_core) >= 14:
        threshold -= 0.02
    if best_score < threshold:
        return None

    return {
        **best,
        'matched_match_type': 'fuzzy_core',
        'matched_match_score': int(best_score * 100),
    }


def find_match(row: dict[str, str], indexes):
    den_key = full_key(row.get('denumire', ''))
    core = core_key(row.get('denumire', ''))
    county_key = full_key(row.get('judet_cheie') or row.get('judet', ''))
    city_key = full_key(row.get('localitate_cheie') or row.get('localitate', ''))

    if den_key in indexes['full']:
        return den_key, core, county_key, city_key, choose_best(indexes['full'][den_key], county_key, city_key, 'exact_full', 100)

    if core in indexes['core']:
        return den_key, core, county_key, city_key, choose_best(indexes['core'][core], county_key, city_key, 'exact_core', 94)

    prefix = (core or den_key)[:8]
    candidates = indexes['prefix'].get(prefix, [])
    if candidates and len(core) >= 8:
        fuzzy = fuzzy_candidate(core, candidates, county_key, city_key)
        if fuzzy:
            return den_key, core, county_key, city_key, fuzzy

    return den_key, core, county_key, city_key, None


def enrich_rows(rows: list[dict[str, str]], indexes, include_shortlist_fields: bool) -> list[tuple[object, ...]]:
    payload_rows = []
    for row in rows:
        den_key, core, county_key, city_key, match = find_match(row, indexes)

        values = []
        if include_shortlist_fields:
            values.extend([
                parse_int(row.get('priority_rank', '')),
                parse_int(row.get('priority_score', '')),
                row.get('priority_reason', ''),
                parse_int(row.get('judet_rank_active', '')),
                parse_int(row.get('localitate_total_active', '')),
                row.get('judet_cheie', ''),
                row.get('localitate_cheie', ''),
            ])

        values.extend([
            row.get('categorie', ''),
            row.get('denumire', ''),
            row.get('numar_registru_national', ''),
            row.get('stare_actuala', ''),
            row.get('status_normalizat', ''),
            parse_bool(row.get('activ', '')),
            row.get('sediu_schimbat', ''),
            row.get('instanta_transfer', ''),
            row.get('tara', ''),
            row.get('judet', ''),
            row.get('localitate', ''),
            row.get('adresa', ''),
            row.get('scop_initial', ''),
            row.get('scop_modificari', ''),
            row.get('hg_utilitate_publica', ''),
            row.get('data_hg_utilitate_publica', ''),
            row.get('sursa_fisier', ''),
            row.get('sursa_url', ''),
            row.get('sursa_data_actualizare', ''),
            den_key,
            core,
            county_key,
            city_key,
            match.get('matched_company_id') if match else None,
            match.get('matched_match_type') if match else None,
            match.get('matched_match_score') if match else None,
            match.get('matched_cui') if match else None,
            match.get('matched_company_name') if match else None,
            match.get('matched_county') if match else None,
            match.get('matched_city') if match else None,
            match.get('matched_address') if match else None,
            match.get('matched_email') if match else None,
            match.get('matched_phone') if match else None,
            match.get('matched_website') if match else None,
            match.get('matched_caen') if match else None,
            match.get('matched_sector') if match else None,
            match.get('matched_sector_name') if match else None,
            match.get('matched_employees') if match else None,
            parse_numeric(match.get('matched_revenue')) if match else None,
            match.get('matched_status_anaf') if match else None,
            match.get('matched_is_active') if match else None,
            match.get('matched_is_vat_payer') if match else None,
            match.get('matched_lead_score') if match else None,
            match.get('matched_data_completeness') if match else None,
            match.get('matched_source') if match else None,
            None,
        ])
        payload_rows.append(tuple(values))
    return payload_rows


def insert_rows(conn, table_name: str, rows: list[tuple[object, ...]], include_shortlist_fields: bool) -> None:
    columns = []
    if include_shortlist_fields:
        columns.extend(SHORTLIST_FIELDS)
    columns.extend(REGISTRY_FIELDS)
    columns.extend(ENRICHMENT_FIELDS)
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            f"insert into {table_name} ({', '.join(columns)}) values %s",
            rows,
            page_size=2000,
        )
    conn.commit()


def apply_contact_enrichment(conn, db_kind: str, table_name: str) -> None:
    if db_kind == 'romania':
        sql = f"""
        with contact_agg as (
            select
                company_id,
                max(case when contact_value like '%@%' then contact_value end) as email,
                max(case when contact_value ilike 'http%%' or contact_value ilike 'www.%%' then contact_value end) as website,
                max(case when contact_value not like '%@%' and contact_value not ilike 'http%%' and contact_value not ilike 'www.%%' and regexp_replace(contact_value, '[^0-9]', '', 'g') <> '' then contact_value end) as phone
            from contacts
            where company_id is not null and contact_value is not null and contact_value <> ''
            group by company_id
        )
        update {table_name} t
        set matched_email = coalesce(nullif(t.matched_email, ''), ca.email),
            matched_phone = coalesce(nullif(t.matched_phone, ''), ca.phone),
            matched_website = coalesce(nullif(t.matched_website, ''), ca.website),
            matched_source = case
                when (ca.email is not null or ca.phone is not null or ca.website is not null)
                then coalesce(t.matched_source, '') || '+contacts'
                else t.matched_source
            end
        from contact_agg ca
        where t.matched_company_id = ca.company_id;
        """
    else:
        sql = f"""
        with contact_agg as (
            select company_id,
                   max(nullif(email, '')) as email,
                   max(nullif(phone, '')) as phone
            from contacts
            where company_id is not null
            group by company_id
        )
        update {table_name} t
        set matched_email = coalesce(nullif(t.matched_email, ''), ca.email),
            matched_phone = coalesce(nullif(t.matched_phone, ''), ca.phone),
            matched_source = case
                when (ca.email is not null or ca.phone is not null)
                then coalesce(t.matched_source, '') || '+contacts'
                else t.matched_source
            end
        from contact_agg ca
        where t.matched_company_id = ca.company_id;
        """
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def print_stats(conn, table_name: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            select
                count(*) as total_rows,
                count(*) filter (where matched_company_id is not null) as matched_rows,
                count(*) filter (where matched_email is not null and matched_email <> '') as matched_email_rows,
                count(*) filter (where matched_website is not null and matched_website <> '') as matched_website_rows,
                count(*) filter (where matched_cui is not null and matched_cui <> '') as matched_cui_rows
            from {table_name}
            """
        )
        result = cur.fetchone()
    print(table_name, dict(zip(['total_rows', 'matched_rows', 'matched_email_rows', 'matched_website_rows', 'matched_cui_rows'], result)))


def process_database(dbname: str, db_kind: str, registry_rows: list[dict[str, str]], shortlist_rows: list[dict[str, str]]) -> None:
    wanted_full = {full_key(row.get('denumire', '')) for row in registry_rows if full_key(row.get('denumire', ''))}
    wanted_core = {core_key(row.get('denumire', '')) for row in registry_rows if core_key(row.get('denumire', ''))}
    wanted_prefixes = {(core_key(row.get('denumire', '')) or full_key(row.get('denumire', '')))[:8] for row in registry_rows if (core_key(row.get('denumire', '')) or full_key(row.get('denumire', '')))}

    conn = connect(dbname)
    try:
        indexes = fetch_company_indexes(conn, db_kind, wanted_full, wanted_core, wanted_prefixes)

        create_table(conn, REGISTRY_TABLE, include_shortlist_fields=False)
        registry_payload = enrich_rows(registry_rows, indexes, include_shortlist_fields=False)
        insert_rows(conn, REGISTRY_TABLE, registry_payload, include_shortlist_fields=False)
        apply_contact_enrichment(conn, db_kind, REGISTRY_TABLE)

        create_table(conn, SHORTLIST_TABLE, include_shortlist_fields=True)
        shortlist_payload = enrich_rows(shortlist_rows, indexes, include_shortlist_fields=True)
        insert_rows(conn, SHORTLIST_TABLE, shortlist_payload, include_shortlist_fields=True)
        apply_contact_enrichment(conn, db_kind, SHORTLIST_TABLE)

        print(dbname)
        print_stats(conn, REGISTRY_TABLE)
        print_stats(conn, SHORTLIST_TABLE)
    finally:
        conn.close()


def main() -> None:
    registry_rows = load_tsv(REGISTRY_FILE)
    shortlist_rows = load_tsv(SHORTLIST_FILE)
    process_database('romania', 'romania', registry_rows, shortlist_rows)
    process_database('interjob_master', 'master', registry_rows, shortlist_rows)


if __name__ == '__main__':
    main()