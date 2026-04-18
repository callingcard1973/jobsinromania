-- Run this in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/srgfzelqcehzidkzkjyx/sql/new

CREATE TABLE anunturi (
    id INTEGER PRIMARY KEY,
    cod_smis TEXT, titlu_achizitie TEXT, beneficiar TEXT,
    email TEXT, telefon TEXT, judet TEXT, tip_contract TEXT,
    buget TEXT, data_publicare TEXT, data_limita TEXT,
    descriere TEXT, contractors TEXT, spec_url TEXT, url TEXT
);

CREATE TABLE proiecte_eu (
    id INTEGER PRIMARY KEY,
    cod_smis TEXT, titlu_proiect TEXT, beneficiar TEXT,
    email TEXT, telefon TEXT, program_operational TEXT,
    axa TEXT, domeniu_interventie TEXT, data_contract TEXT,
    judet TEXT, contact TEXT, adresa TEXT, localitate TEXT,
    proceduri TEXT, url TEXT
);

ALTER TABLE anunturi ENABLE ROW LEVEL SECURITY;
ALTER TABLE proiecte_eu ENABLE ROW LEVEL SECURITY;
CREATE POLICY "anon_read_anunturi" ON anunturi FOR SELECT USING (true);
CREATE POLICY "anon_read_proiecte" ON proiecte_eu FOR SELECT USING (true);
CREATE POLICY "service_write_anunturi" ON anunturi FOR ALL USING (true);
CREATE POLICY "service_write_proiecte" ON proiecte_eu FOR ALL USING (true);
