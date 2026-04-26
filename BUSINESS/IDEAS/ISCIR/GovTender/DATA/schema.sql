
CREATE TABLE govtender_tenders (
    tender_id VARCHAR(50) PRIMARY KEY,
    title TEXT,
    cpv_code VARCHAR(10),
    value NUMERIC,
    deadline DATE,
    country VARCHAR(2),
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE govtender_company_profiles (
    company_id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    cui VARCHAR(20),
    cpv_codes TEXT[],
    avg_contract_value NUMERIC,
    countries TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE govtender_matches (
    match_id SERIAL PRIMARY KEY,
    tender_id VARCHAR(50) REFERENCES govtender_tenders(tender_id),
    company_id INTEGER REFERENCES govtender_company_profiles(company_id),
    relevance_score INTEGER,
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tender_country ON govtender_tenders(country);
CREATE INDEX idx_matches_company ON govtender_matches(company_id);
