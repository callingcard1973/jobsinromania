CREATE TEMP TABLE _tmp_hotel_emails (email text, source_table text, country text);
\copy _tmp_hotel_emails FROM '/tmp/scraped_hotel_emails.csv' CSV HEADER
INSERT INTO master_emails (email, source_table, country, first_seen)
SELECT DISTINCT email, source_table, country, NOW() FROM _tmp_hotel_emails
WHERE email LIKE '%@%'
ON CONFLICT (email) DO NOTHING;
SELECT count(*) as total_master_emails FROM master_emails;
DROP TABLE _tmp_hotel_emails;
