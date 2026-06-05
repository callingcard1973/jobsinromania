-- Read current enriched CSV via foreign table (or COPY from raspibig)
-- Strategy: build the join in PG, output CSV to raspibig /tmp/, copy local

\set ON_ERROR_STOP on

-- Pool of RO/ANOFM emails (deduped by normalized company name)
DROP TABLE IF EXISTS tmp_ro_email_pool;
CREATE TEMP TABLE tmp_ro_email_pool AS
SELECT DISTINCT ON (LOWER(REGEXP_REPLACE(company, '[^A-Za-z0-9]', '', 'g')))
  LOWER(REGEXP_REPLACE(company, '[^A-Za-z0-9]', '', 'g')) AS norm_name,
  email,
  company AS source_company,
  phone,
  source_table
FROM master_emails
WHERE company IS NOT NULL
  AND email IS NOT NULL
  AND email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
  AND (source_table ILIKE '%anofm%' OR source_table ILIKE '%romania%' OR source_table ILIKE '%ro_%')
ORDER BY LOWER(REGEXP_REPLACE(company, '[^A-Za-z0-9]', '', 'g')),
         CASE WHEN source_table ILIKE '%anofm%' THEN 1
              WHEN source_table = 'master_romania_companies' THEN 2
              ELSE 3 END;

-- Show pool size
\echo === Pool size ===
SELECT COUNT(*) FROM tmp_ro_email_pool;

-- Target factories (CAEN 10-33, 50+ emp) — rebuild from bilant_years + onrc_status
DROP TABLE IF EXISTS tmp_targets;
CREATE TEMP TABLE tmp_targets AS
SELECT
  os.denumire AS company_name,
  os.cui,
  LEFT(by_.caen, 2)::int AS caen_code,
  by_.cifra_afaceri AS turnover_ron,
  by_.nr_angajati AS employees,
  LOWER(REGEXP_REPLACE(os.denumire, '[^A-Za-z0-9]', '', 'g')) AS norm_name
FROM bilant_years by_
JOIN onrc_status os ON os.cui = by_.cui
WHERE by_.year = 2024
  AND LEFT(by_.caen, 2) ~ '^(1[0-9]|2[0-9]|3[0-3])$'
  AND by_.nr_angajati >= 50;

\echo === Target factories ===
SELECT COUNT(*) FROM tmp_targets;

-- JOIN: how many match
\echo === Match count ===
SELECT COUNT(DISTINCT t.cui)
FROM tmp_targets t
JOIN tmp_ro_email_pool p ON p.norm_name = t.norm_name;

-- Export enriched join to CSV
\echo === Exporting ===
\COPY (
  SELECT
    t.company_name,
    t.cui,
    t.caen_code,
    t.employees,
    t.turnover_ron,
    p.email,
    p.phone,
    p.source_table AS email_source
  FROM tmp_targets t
  LEFT JOIN tmp_ro_email_pool p ON p.norm_name = t.norm_name
  ORDER BY t.employees DESC NULLS LAST
) TO '/tmp/employers_ro_anofm_enriched.csv' WITH (FORMAT CSV, HEADER true);

\echo === DONE ===
