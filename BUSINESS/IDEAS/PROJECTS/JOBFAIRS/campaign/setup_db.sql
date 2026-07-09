-- JOBFAIRS Campaign Tables
-- Run on raspibig: psql -d interjob_master -f setup_db.sql

-- Main contact list (HR managers, EURES, Norway oil)
CREATE TABLE IF NOT EXISTS jobfairs_campaign (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255),
    company VARCHAR(255),
    country VARCHAR(10),
    city VARCHAR(255),
    sector VARCHAR(100),
    source VARCHAR(100),
    hr_email VARCHAR(255),
    campaign_status VARCHAR(50) DEFAULT 'pending',
    last_contacted TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(email, sector)
);
CREATE INDEX IF NOT EXISTS idx_jf_email ON jobfairs_campaign(LOWER(email));
CREATE INDEX IF NOT EXISTS idx_jf_status ON jobfairs_campaign(campaign_status);
CREATE INDEX IF NOT EXISTS idx_jf_sector ON jobfairs_campaign(sector);
CREATE INDEX IF NOT EXISTS idx_jf_country ON jobfairs_campaign(country);

-- Send log
CREATE TABLE IF NOT EXISTS jobfairs_send_log (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    campaign VARCHAR(100),
    template INT,
    message_id VARCHAR(255),
    sender VARCHAR(255),
    status VARCHAR(50) DEFAULT 'sent',
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_jf_log_email ON jobfairs_send_log(LOWER(email));

-- Do-not-contact
CREATE TABLE IF NOT EXISTS jobfairs_dnc (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    reason VARCHAR(255),
    added_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_jf_dnc_email ON jobfairs_dnc(LOWER(email));

-- Populate from existing data sources
-- 1. HR-pattern emails from master_emails
INSERT INTO jobfairs_campaign (email, company, country, sector, source)
SELECT DISTINCT e.email, e.company, e.country, 'HR_MANAGERS', 'master_emails_hr_pattern'
FROM master_emails e
WHERE e.bounced IS NOT TRUE
  AND (LOWER(e.email) LIKE 'hr@%'
    OR LOWER(e.email) LIKE 'hr.%@%'
    OR LOWER(e.email) LIKE 'recruit%@%'
    OR LOWER(e.email) LIKE 'talent%@%'
    OR LOWER(e.email) LIKE 'personal%@%'
    OR LOWER(e.email) LIKE 'people%@%'
    OR LOWER(e.email) LIKE 'staffing%@%'
    OR LOWER(e.email) LIKE 'hiring%@%'
    OR LOWER(e.email) LIKE 'workforce%@%'
    OR LOWER(e.email) LIKE 'human%@%')
ON CONFLICT (email, sector) DO NOTHING;

-- 2. Named HR contacts from contacts table
INSERT INTO jobfairs_campaign (email, contact_name, company, country, sector, source)
SELECT DISTINCT c.email1, c.name, c.company, c.country, 'HR_MANAGERS', 'contacts_hr_title'
FROM contacts c
WHERE c.email1 IS NOT NULL
  AND c.email1 != ''
  AND (LOWER(c.position) LIKE '%hr %' OR LOWER(c.position) LIKE '%human%'
    OR LOWER(c.position) LIKE '%recruit%' OR LOWER(c.position) LIKE '%talent%'
    OR LOWER(c.position) LIKE '%personal%' OR LOWER(c.position) LIKE '%people%'
    OR LOWER(c.name) LIKE '%hr manager%' OR LOWER(c.name) LIKE '%hr director%'
    OR LOWER(c.name) LIKE '%recruitment%' OR LOWER(c.name) LIKE '%talent%')
ON CONFLICT (email, sector) DO NOTHING;

-- 3. Norwegian HR emails
INSERT INTO jobfairs_campaign (email, company, country, city, sector, source)
SELECT DISTINCT hr_email, name, 'NO', city, 'NORWAY_OIL', 'no_contacts_hr_email'
FROM no_contacts
WHERE hr_email IS NOT NULL AND hr_email != ''
ON CONFLICT (email, sector) DO NOTHING;

-- 4. Norway oil/offshore/staffing companies
INSERT INTO jobfairs_campaign (email, company, country, city, sector, source)
SELECT DISTINCT email, name, 'NO', city, 'NORWAY_OIL', 'norway_campaign_oil'
FROM norway_campaign
WHERE email IS NOT NULL AND email != ''
  AND campaign_status = 'pending'
  AND (LOWER(nace_desc) LIKE '%oil%'
    OR LOWER(nace_desc) LIKE '%gas%'
    OR LOWER(nace_desc) LIKE '%offshore%'
    OR LOWER(nace_desc) LIKE '%maritime%'
    OR LOWER(nace_desc) LIKE '%shipping%'
    OR LOWER(nace_desc) LIKE '%staffing%'
    OR LOWER(nace_desc) LIKE '%recruitment%'
    OR LOWER(nace_desc) LIKE '%temporary%'
    OR nace_code LIKE '06%' OR nace_code LIKE '09%'
    OR nace_code LIKE '50%' OR nace_code LIKE '78%')
ON CONFLICT (email, sector) DO NOTHING;

-- 5. EURES contacts
INSERT INTO jobfairs_campaign (email, contact_name, company, country, sector, source)
SELECT DISTINCT email1, contact_person, employer, country, 'EURES_CONTACTS', 'eures_contacts'
FROM eures_contacts
WHERE email1 IS NOT NULL AND email1 != ''
ON CONFLICT (email, sector) DO NOTHING;

-- 6. EURES-sourced agencies (Norway)
INSERT INTO jobfairs_campaign (email, company, country, sector, source)
SELECT DISTINCT email, name, country, 'EURES_CONTACTS', 'agencies_eures'
FROM agencies
WHERE email IS NOT NULL AND email != ''
  AND LOWER(type) LIKE '%eures%'
  AND country IN ('NO', 'SE', 'DK', 'FI', 'DE', 'NL', 'BE', 'AT')
ON CONFLICT (email, sector) DO NOTHING;

-- Summary
SELECT sector, source, COUNT(*) as cnt
FROM jobfairs_campaign
GROUP BY sector, source
ORDER BY sector, cnt DESC;

SELECT sector, COUNT(*) as total
FROM jobfairs_campaign
GROUP BY sector
ORDER BY total DESC;
