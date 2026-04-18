-- CAP Federation Database Schema
-- Add to interjob_master PostgreSQL database
-- Run: psql -h localhost -U tudor -d interjob_master < cap_schema.sql

-- 1. Cooperatives Table
CREATE TABLE IF NOT EXISTS cap_cooperatives (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    cui VARCHAR(20) UNIQUE,
    registration_number VARCHAR(100),
    county VARCHAR(50),
    city VARCHAR(100),
    address TEXT,
    products TEXT[],  -- Array of products: ['wheat', 'rice', 'potatoes']
    capacity_annual_tons DECIMAL(10,2),
    capacity_monthly_tons DECIMAL(10,2),
    certification_status VARCHAR(50) DEFAULT 'NONE',  -- NONE, HACCP, ISO_9001, ISO_22000
    certification_date DATE,
    email VARCHAR(255),
    phone VARCHAR(50),
    website VARCHAR(255),
 
    contact_person VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    status VARCHAR(50) DEFAULT 'PROSPECT',  -- PROSPECT, CONTACTED, MEETING_SCHEDULED, LOI_SIGNED, MEMBER
    added_on TIMESTAMP DEFAULT NOW(),
    last_contacted_on TIMESTAMP,
    membership_level VARCHAR(50),  -- FOUNDING, REGULAR, OBSERVER
    commission_rate DECIMAL(5,2) DEFAULT 0.08,  -- 8% CAP margin
    payment_status VARCHAR(50),
    notes TEXT,
    metadata JSONB,  -- Flexible storage for additional data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 2. Contracts Table
CREATE TABLE IF NOT EXISTS cap_contracts (
    id SERIAL PRIMARY KEY,
    contract_name VARCHAR(255),
    contract_id VARCHAR(100) UNIQUE,  -- SEAP/APEX contract ID
    buyer_name VARCHAR(255),
    buyer_type VARCHAR(50),  -- SEAP, NATO, UN, MILITARY, PRIVATE
    buyer_county VARCHAR(50),
    buyer_country VARCHAR(50),
    value_eur DECIMAL(15,2),
    value_ron DECIMAL(15,2),
    currency VARCHAR(10) DEFAULT 'EUR',
    cpv_code VARCHAR(20),
    cpv_description TEXT,
    products_required TEXT[],
    estimated_volume_tons DECIMAL(10,2),
    delivery_date_start TIMESTAMP,
    delivery_date_end TIMESTAMP,
    delivery_location TEXT,
    status VARCHAR(50) DEFAULT 'OPPORTUNITY',  -- OPPORTUNITY, BIDDING, AWARDED, DELIVERY, COMPLETE, LOST
    bid_submitted BOOLEAN DEFAULT FALSE,
    bid_submitted_on TIMESTAMP,
    bid_value_eur DECIMAL(15,2),
    award_date TIMESTAMP,
    winner_name VARCHAR(255),
    winner_cui VARCHAR(20),
    subcontracting_partner VARCHAR(255),  -- NISARA, MATRA, EUROGRUP, etc.
    subcontract_percentage DECIMAL(5,2),
    source VARCHAR(50),  -- SEAP, TED, NATO, MANUAL
    source_url TEXT,
    notes TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. Contract-to-Cooperative Matches Table
CREATE TABLE IF NOT EXISTS cap_contract_matches (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER REFERENCES cap_contracts(id) ON DELETE CASCADE,
    cooperative_id INTEGER REFERENCES cap_cooperatives(id) ON DELETE CASCADE,
    match_score DECIMAL(5,4),  -- 0.0-1.0 confidence score
    match_reasons TEXT[],  -- Reasons for match: ['product:wheat', 'county:constanta', 'capacity:sufficient']
    assigned_volume_tons DECIMAL(10,2),
    assigned_eur DECIMAL(15,2),  # Value allocated to this co-op
    status VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, ASSIGNED, CONFIRMED, DELIVERED
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. Outreach/Campaign Logs Table
CREATE TABLE IF NOT EXISTS cap_outreach_logs (
    id SERIAL PRIMARY KEY,
    cooperative_id INTEGER REFERENCES cap_cooperatives(id) ON DELETE CASCADE,
    campaign_id VARCHAR(100),  -- CAP_FEDERATION_Q2_2026, etc.
    email_id VARCHAR(255),
    subject VARCHAR(500),
    sent_on TIMESTAMP,
    opened BOOLEAN DEFAULT FALSE,
    opened_on TIMESTAMP,
    clicked BOOLEAN DEFAULT FALSE,
    clicked_on TIMESTAMP,
    replied BOOLEAN DEFAULT FALSE,
    replied_on TIMESTAMP,
    response_text TEXT,
    next_action VARCHAR(50),
    next_action_date TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 5. Payments Table
CREATE TABLE IF NOT EXISTS cap_payments (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER REFERENCES cap_contracts(id),
    cooperative_id INTEGER REFERENCES cap_cooperatives(id),
    contract_value_eur DECIMAL(15,2),
    allocated_eur DECIMAL(15,2),
    commission_rate DECIMAL(5,2),
    commission_eur DECIMAL(15,2),
    payment_status VARCHAR(50) DEFAULT 'PENDING',  -- PENDING, PARTIAL, PAID
    invoice_number VARCHAR(100),
    invoice_date DATE,
    payment_date DATE,
    payment_method VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 6. Campaign Stats Table
CREATE TABLE IF NOT EXISTS cap_campaign_stats (
    id SERIAL PRIMARY KEY,
    date DATE DEFAULT CURRENT_DATE,
    campaign_id VARCHAR(100),
    emails_sent INTEGER DEFAULT 0,
    emails_opened INTEGER DEFAULT 0,
    emails_clicked INTEGER DEFAULT 0,
    emails_replied INTEGER DEFAULT 0,
    lois_signed INTEGER DEFAULT 0,
    new_members INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cap_cooperatives_status ON cap_cooperatives(status);
CREATE INDEX IF NOT EXISTS idx_cap_cooperatives_county ON cap_cooperatives(county);
CREATE INDEX IF NOT EXISTS idx_cap_cooperatives_cui ON cap_cooperatives(cui);
CREATE INDEX IF NOT EXISTS idx_cap_cooperatives_products ON cap_cooperatives USING GIN(products);
CREATE INDEX IF NOT EXISTS idx_cap_contracts_status ON cap_contracts(status);
CREATE INDEX IF NOT EXISTS idx_cap_contracts_cpv ON cap_contracts(cpv_code);
CREATE INDEX IF NOT EXISTS idx_cap_contracts_value ON cap_contracts(value_eur);
CREATE INDEX IF NOT EXISTS idx_cap_contract_matches_contract ON cap_contract_matches(contract_id);
CREATE INDEX IF NOT EXISTS idx_cap_contract_matches_cooperative ON cap_contract_matches(cooperative_id);
CREATE INDEX IF NOT EXISTS idx_cap_outreach_logs_cooperative ON cap_outreach_logs(cooperative_id);
CREATE INDEX IF NOT EXISTS idx_cap_outreach_logs_campaign ON cap_outreach_logs(campaign_id);
CREATE INDEX IF NOT EXISTS idx_cap_payments_contract ON cap_payments(contract_id);
CREATE INDEX IF NOT EXISTS idx_cap_payments_cooperative ON cap_payments(cooperative_id);

-- Insert test data (sample cooperatives)
INSERT INTO cap_cooperatives (name, county, capacity_annual_tons, products, email, status) VALUES
('Cooperativa Agricola X', 'Constanța', 1000, ARRAY['wheat', 'barley'], 'contact@coope-x.ro', 'PROSPECT'),
('Cooperativa Agricola Y', 'Brașov', 800, ARRAY['potatoes', 'vegetables'], 'info@coope-y.ro', 'PROSPECT'),
('Cooperativa Agricola Z', 'Arad', 1500, ARRAY['wheat', 'maize'], 'office@coope-z.ro', 'PROSPECT')
ON CONFLICT (name) DO NOTHING;

-- Insert test contract
INSERT INTO cap_contracts (contract_name, buyer_name, buyer_type, value_eur, cpv_code, cpv_description, status) VALUES
('SEAP Food Contract 2026', 'Direcția Generală de Asistență Socială', 'SEAP', 75000.00, '03112000-1', 'Cereale', 'OPPORTUNITY')
ON CONFLICT (contract_id) DO NOTHING;

-- Grant permissions (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO tudor;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO tudor;

COMMENT ON TABLE cap_cooperatives IS 'CAP agricultural cooperative members';
COMMENT ON TABLE cap_contracts IS 'CAP institutional procurement contracts (SEAP, NATO, UN)';
COMMENT ON TABLE cap_contract_matches IS 'Matches between contracts and cooperatives'；
COMMENT ON TABLE cap_outreach_logs IS 'Email campaign outreach logs';
COMMENT ON TABLE cap_payments IS 'Payment tracking for contracts and cooperatives';
COMMENT ON TABLE cap_campaign_stats IS 'Daily campaign statistics';
