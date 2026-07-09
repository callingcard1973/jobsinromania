-- CAMPAIGNS 5-8

-- ============================================
-- CAMPAIGN 5: TED WINNERS NORWAY
-- ============================================
CREATE TABLE IF NOT EXISTS jf_ted_winners_no (
    id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
    company VARCHAR(255), contractor_city VARCHAR(255),
    contractor_address VARCHAR(255), contractor_website VARCHAR(255),
    authority VARCHAR(500), cpv VARCHAR(100), contract_value NUMERIC,
    notice_id VARCHAR(100), source_year INT,
    campaign_status VARCHAR(50) DEFAULT 'pending', last_contacted TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS jf_ted_winners_no_send_log (
    id SERIAL PRIMARY KEY, email VARCHAR(255), company VARCHAR(255),
    campaign VARCHAR(100), template INT, message_id VARCHAR(255),
    sender VARCHAR(255), status VARCHAR(50) DEFAULT 'sent',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS jf_ted_winners_no_dnc (
    id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
    reason VARCHAR(255), added_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO jf_ted_winners_no (email, company, contractor_city, contractor_address, contractor_website, authority, cpv, contract_value, notice_id, source_year)
SELECT DISTINCT ON (LOWER(tw.contractor_email))
  tw.contractor_email, tw.contractor, tw.contractor_city, tw.contractor_address,
  tw.contractor_website, tw.authority, tw.cpv, tw.contract_value, tw.notice_id, tw.source_year
FROM ted_winners tw
WHERE LOWER(tw.contractor_country) IN ('norway','no','nor')
  AND tw.contractor_email IS NOT NULL AND tw.contractor_email != ''
ON CONFLICT (email) DO NOTHING;

SELECT 'TED_WINNERS_NO' as campaign, COUNT(*) as total FROM jf_ted_winners_no;

-- ============================================
-- CAMPAIGN 6: HR MANAGERS (Norway-linked)
-- ============================================
CREATE TABLE IF NOT EXISTS jf_hr_managers_no (
    id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
    contact_name VARCHAR(255), job_title VARCHAR(255),
    company VARCHAR(255), phone VARCHAR(100), source VARCHAR(100),
    campaign_status VARCHAR(50) DEFAULT 'pending', last_contacted TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS jf_hr_managers_no_send_log (
    id SERIAL PRIMARY KEY, email VARCHAR(255), company VARCHAR(255),
    campaign VARCHAR(100), template INT, message_id VARCHAR(255),
    sender VARCHAR(255), status VARCHAR(50) DEFAULT 'sent',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS jf_hr_managers_no_dnc (
    id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
    reason VARCHAR(255), added_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO jf_hr_managers_no (email, company, source)
SELECT DISTINCT e.email, e.company, 'master_emails_hr'
FROM master_emails e
WHERE e.is_bounced IS NOT TRUE AND LOWER(e.email) LIKE '%.no'
  AND (LOWER(e.email) LIKE 'hr@%' OR LOWER(e.email) LIKE 'hr.%@%'
    OR LOWER(e.email) LIKE 'recruit%@%' OR LOWER(e.email) LIKE 'talent%@%'
    OR LOWER(e.email) LIKE 'personal%@%' OR LOWER(e.email) LIKE 'people%@%'
    OR LOWER(e.email) LIKE 'staffing%@%' OR LOWER(e.email) LIKE 'human%@%')
ON CONFLICT (email) DO NOTHING;

INSERT INTO jf_hr_managers_no (email, contact_name, job_title, phone, source)
SELECT DISTINCT c.email, c.name, c.position, c.phone, 'contacts_hr'
FROM contacts c
WHERE LOWER(c.email) LIKE '%.no'
  AND (LOWER(c.position) LIKE '%hr%' OR LOWER(c.position) LIKE '%recruit%'
    OR LOWER(c.position) LIKE '%talent%' OR LOWER(c.position) LIKE '%personal%'
    OR LOWER(c.position) LIKE '%people%' OR LOWER(c.position) LIKE '%human%')
ON CONFLICT (email) DO NOTHING;

INSERT INTO jf_hr_managers_no (email, company, source)
SELECT DISTINCT nc.hr_email, nc.name, 'no_contacts_hr'
FROM no_contacts nc
WHERE nc.hr_email IS NOT NULL AND nc.hr_email != ''
  AND nc.hr_email != nc.email
ON CONFLICT (email) DO NOTHING;

SELECT 'HR_MANAGERS_NO' as campaign, COUNT(*) as total FROM jf_hr_managers_no;

-- ============================================
-- CAMPAIGN 7: EURES NORWAY
-- ============================================
CREATE TABLE IF NOT EXISTS jf_eures_no (
    id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
    company VARCHAR(255), contact_person VARCHAR(255),
    country VARCHAR(50), phone VARCHAR(100), alt_email VARCHAR(255),
    positions_count INT, job_count INT, quality_score INT,
    source VARCHAR(100),
    campaign_status VARCHAR(50) DEFAULT 'pending', last_contacted TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS jf_eures_no_send_log (
    id SERIAL PRIMARY KEY, email VARCHAR(255), company VARCHAR(255),
    campaign VARCHAR(100), template INT, message_id VARCHAR(255),
    sender VARCHAR(255), status VARCHAR(50) DEFAULT 'sent',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS jf_eures_no_dnc (
    id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
    reason VARCHAR(255), added_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO jf_eures_no (email, company, contact_person, country, phone, alt_email, positions_count, job_count, quality_score, source)
SELECT DISTINCT ec.email1, ec.employer, ec.contact_person, ec.country, ec.phone1, ec.email2,
  ec.positions_count, ec.job_count, ec.quality_score, 'eures_contacts'
FROM eures_contacts ec
WHERE ec.email1 IS NOT NULL AND ec.email1 != '' AND ec.country = 'Norway'
ON CONFLICT (email) DO NOTHING;

INSERT INTO jf_eures_no (email, company, country, source)
SELECT DISTINCT ag.email, ag.name, ag.country, 'agencies_eures'
FROM agencies ag
WHERE ag.email IS NOT NULL AND ag.email != '' AND ag.country = 'NO'
ON CONFLICT (email) DO NOTHING;

SELECT 'EURES_NO' as campaign, COUNT(*) as total FROM jf_eures_no;

-- ============================================
-- CAMPAIGN 8: NORWAY OIL & OFFSHORE
-- ============================================
CREATE TABLE IF NOT EXISTS jf_norway_oil (
    id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
    company VARCHAR(255), org_number VARCHAR(50), sector_name VARCHAR(255),
    city VARCHAR(255), address VARCHAR(255), phone VARCHAR(100),
    hr_email VARCHAR(255), website VARCHAR(255), linkedin_url VARCHAR(500),
    employees_count INT, tier VARCHAR(10),
    campaign_status VARCHAR(50) DEFAULT 'pending', last_contacted TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS jf_norway_oil_send_log (
    id SERIAL PRIMARY KEY, email VARCHAR(255), company VARCHAR(255),
    campaign VARCHAR(100), template INT, message_id VARCHAR(255),
    sender VARCHAR(255), status VARCHAR(50) DEFAULT 'sent',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS jf_norway_oil_dnc (
    id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL UNIQUE,
    reason VARCHAR(255), added_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO jf_norway_oil (email, company, org_number, sector_name, city, address, phone, hr_email, website, linkedin_url, employees_count, tier)
SELECT nc.email, nc.name, nc.org_number, nc.sector_name, nc.city, nc.address, nc.phone, nc.hr_email, nc.website, nc.linkedin_url, nc.employees_count, nc.tier
FROM norway_campaign nc
WHERE nc.email IS NOT NULL AND nc.email != ''
  AND (nc.sector LIKE '06.%' OR nc.sector LIKE '09.%'
    OR nc.sector LIKE '50.%' OR nc.sector LIKE '78.%'
    OR nc.sector LIKE '30.1%' OR nc.sector LIKE '33.1%')
ON CONFLICT (email) DO NOTHING;

SELECT 'NORWAY_OIL' as campaign, COUNT(*) as total FROM jf_norway_oil;

-- ============================================
-- GRAND SUMMARY
-- ============================================
SELECT 'jf_tier1_construction' as campaign, COUNT(*) as contacts FROM jf_tier1_construction
UNION ALL SELECT 'jf_tier1_horeca', COUNT(*) FROM jf_tier1_horeca
UNION ALL SELECT 'jf_tier1_transport', COUNT(*) FROM jf_tier1_transport
UNION ALL SELECT 'jf_tier1_industrial', COUNT(*) FROM jf_tier1_industrial
UNION ALL SELECT 'jf_ted_winners_no', COUNT(*) FROM jf_ted_winners_no
UNION ALL SELECT 'jf_hr_managers_no', COUNT(*) FROM jf_hr_managers_no
UNION ALL SELECT 'jf_eures_no', COUNT(*) FROM jf_eures_no
UNION ALL SELECT 'jf_norway_oil', COUNT(*) FROM jf_norway_oil
ORDER BY contacts DESC;
