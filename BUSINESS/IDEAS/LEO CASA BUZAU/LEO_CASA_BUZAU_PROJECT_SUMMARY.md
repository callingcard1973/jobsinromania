# LEO CASA BUZAU - Commercial Space Rental Project

**Date:** March 8, 2026

---

## 📍 Property Details

- **Location:** Buzău, Crîng neighborhood
- **Type:** Commercial space (office/call center/IT services)
- **Status:** Ready for rental announcement
- **Target Tenants:** IT services, call centers, consulting firms, design agencies

---

## 📋 Excluded Contacts

**DO NOT CONTACT:**
- Mirel
- Aurelia

---

## 📊 Company Database - Buzău Region

### File Location
**Path:** `/home/tudor/buzau_potrivite_companies_FINAL.csv`

**Size:** 5.8 MB  
**Total Companies:** 34,303  
**Counties Included:**
- Buzău (primary)
- Ialomita
- Prahova
- Vrancea

### File Structure (Columns)
```
cui, company_name, j_number, founding_date, age_years, legal_form, county, city, address, postal_code, sector, website, status_code, status_name, is_active
```

### Data Available
- ✅ Company names
- ✅ Registration numbers (CUI, J-number)
- ✅ Locations (city, county, address, postal code)
- ✅ Legal form (SRL, PFA, II, AF, etc.)
- ✅ Founding date & company age
- ✅ Status (active/inactive)
- ✅ Website (partial)
- ❌ Email addresses (not in base CSV)
- ❌ Phone numbers (not in base CSV)
- ❌ CAEN codes/industry (in separate database, access issues noted)
- ❌ Turnover/financial data (not available in ANAF system)

---

## 🎯 Suitable Business Types (CAEN Codes)

### IT Services (CAEN 62*)
- 6201: Computer programming
- 6202: IT consulting
- 6203: Computer facilities management
- 6209: Other IT services

### Call Centers
- 8220: Call centre activities

### Business Services
- 8219: Business administration support
- 7010: Architectural services
- 7021: Engineering design & planning
- 7022: Engineering consulting
- 7410: Specialised design activities

---

## 📈 How to Use the Data

### Step 1: Extract Suitable Companies
Filter the CSV for companies with:
- Legal form = **"SRL"** (most likely to have resources)
- Company name containing keywords:
  - "SOFTWARE"
  - "SOFT"
  - "IT"
  - "TECH"
  - "DESIGN"
  - "CONSULTING"
  - "CALL"
  - "SERVICE"

### Step 2: Enrich with Contact Info
Once you identify specific companies, can enrich with:
- **Phone numbers** via ANAF API (lookup by CUI)
- **Email addresses** via fuzzy matching against internal databases

### Step 3: Prepare Outreach
- Create rental announcement (template provided in this project)
- Prepare pitch highlighting:
  - Affordable commercial space
  - Buzău location advantages
  - Modern facilities
  - Availability for immediate lease

---

## 🔍 Data Quality & Limitations

### Known Issues
1. **CAEN Codes Not Included:** Industry classification is in SQLite database, but queries experienced timeouts. CAEN data requires separate lookup.
2. **No Contact Info:** Email/phone not in base CSV; enrichment required
3. **No Financial Data:** Turnover information not available in ANAF database (system limitation)
4. **Website Field Sparse:** Many entries have null values

### Data Sources
- **Primary:** All Romania Companies CSV (516 MB, ~4.1M companies)
- **Secondary:** ANAF enriched datasets
- **Alternative:** SQLite CAEN index database with contact fields

---

## 💡 Recommended Workflow

1. **Download CSV** from `/home/tudor/buzau_potrivite_companies_FINAL.csv`
2. **Open in Excel/Calc** and filter by:
   - County = "Buzau" (for Buzău city focus)
   - Legal form = "SRL" or "PFA"
   - Company name contains relevant keywords
3. **Extract 100-200 target companies**
4. **Enrich with phone** via ANAF API script:
   ```bash
   python3 /opt/ACTIVE/INFRA/SKILLS/anaf_api.py enrich output.csv --cui-col cui
   ```
5. **Send rental announcement** to qualified contacts

---

## 📧 Rental Announcement Template

**Subject:** Spatiu comercial de inchirere - Buzau, Crîng

**Body:**
```
Buna ziua,

Va ofertez spatiu comercial in zona Crîng, Buzau, perfect pentru:
- Servicii IT
- Call center
- Consulting
- Design
- Services administrative

Caracteristici:
- Locatie convenabila
- Facilitati moderne
- Disponibil imediat
- Pret accesibil
- Parcare

Contact:
[Your Phone]
[Your Email]

Cu placere,
[Your Name]
```

---

## 📍 File Locations

| Item | Location |
|------|----------|
| Company CSV | `/home/tudor/buzau_potrivite_companies_FINAL.csv` |
| CAEN Search Tool | `/opt/ACTIVE/INFRA/SKILLS/csv_caen_search.py` |
| ANAF API (enrichment) | `/opt/ACTIVE/INFRA/SKILLS/anaf_api.py` |
| All Companies Master CSV | `/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/all_romania_companies.csv` |
| CAEN Database | `/opt/ACTIVE/OPENDATA/DATA/CAEN_INDEX/caen_search.db` |

---

## ✅ Next Steps

- [ ] Download buzau_potrivite_companies_FINAL.csv
- [ ] Filter for SRL companies with relevant keywords
- [ ] Enrich filtered list with phone numbers
- [ ] Create contact list (100-200 companies)
- [ ] Send rental announcement
- [ ] Track responses & follow-ups

---

**Project Status:** ✅ Ready for Outreach  
**Data Updated:** March 8, 2026  
**Companies Available:** 34,303 (regional)  
**Estimated Quality Companies:** 500-1000 (after filtering by type)
