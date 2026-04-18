# CAP Federation Implementation Guide
**Phase 1: Foundation (Weeks 1-13 / Months 1-4)**
**Objective:** Legal entity established, 15 cooperatives recruited, first revenue

---

## Week-by-Week Implementation Plan

### Week 1: Foundation Setup

**Owner:** Board/Founding Team
**Key Events:**
- Kickoff meeting with founding team
- Define decision-making authority
- Approve initial budget (25K-50K EUR)

**Tasks:**

1. **Legal Foundation (Owner: Legal Counsel)**
   ```bash
   Tasks:
   - Draft CAP Federation Constitution
   - Draft Membership Agreement Template
   - Create Bylaws for Board of Directors
   - Define voting rights (one vote per member co-op)
   - Define profit distribution (90% to members, 10% to CAP)
   
   Deliverables:
   - cap_constitution_draft.pdf
   - membership_agreement_template.pdf
   - bylaws.pdf
   
   Resources:
   - Romanian cooperative law expert
   - Template: /opt/ACTIVE/IDEAS/NATO/OPENCODE/legal/cooperative_federation_law.md
   ```

2. **Market Intelligence (Owner: Business Development)**
   ```bash
   Tasks:
   - Create database of 50 prospective cooperatives
   - Prioritize by: wheat/grains, rice, potatoes, vegetables, dairy
   - Prioritize by: counties (Constanța, Brașov, Arad, Timiș, Dolj)
   - Research each co-op: CUI, production capacity, contact details
   
   Deliverables:
   - /opt/ACTIVE/IDEAS/NATO/OPENCODE/data/prospective_coops.csv
   
   CSV Format:
   CUI,Nume Cooperativă,Județ,Produse,Capacitate anuală (tone),Telefon,Email,Website,Status
   12345678,Cooperative Agricola X,Constanța,Grâu,Potatoes,1000,0xxx,xxx@gmail.com,www.xxx.com,Prospect
   ```

3. **Partnership Research (Owner: Business Development)**
   ```bash
   Tasks:
   - Research NISARA IMPEX S.R.L. (85M EUR military supplier)
   - Research MATRA S.R.L. (84M EUR supplier, 89% military)
   - Research EUROGRUP BOGDAN (20M EUR military)
   - Identify contact persons for subcontracting inquiries
   
   Deliverables:
   - /opt/ACTIVE/IDEAS/NATO/OPENCODE/data/military_suppliers_rsd.csv
   
   Fields:
   Supplier,CUI,Email,Phone,Address,Total Military EUR,Contracts,Contact Person
   NISARA IMPEX S.R.L.,XXXXXXX,contact@nisara.ro,0xxx...,Str. X,85M,150+,Ioan Popescu
   MATRA S.R.L.,XXXXXXX,contact@matra.ro,0xxx...,Str. Y,75M,200+,Maria Ionescu
   ```

**Week 1 Checklist:**
- [ ] Draft constitution completed
- [ ] Membership agreement template created
- [ ] 50 co-op database initialized (minimum)
- [ ] Military supplier research completed
- [ ] Initial budget approved

---

### Week 2: Registration & Recruitment Initiation

**Owner:** Executive Director (if hired) or Board Representative
**Investment:**
- Legal fees: 3K-5K EUR
- Initial operating: 5K EUR
- **Total Week 2: 8K-10K EUR**

**Tasks:**

1. **ORC Registration Initiation (Owner: Legal Counsel)**
   ```bash
   Required Documents:
   - Federation constitution (signed)
   - Founding agreement (5+ co-ops)
   - Articles of association
   - Identity documents of founding members
   - Proof of initial capital (5K-10K EUR)
   - CAEN code application: 0161 (crop production support) + 4621 (wholesale)
   
   Process:
   1. File: Registrul Comerțului (ORC) Office
   2. Timeline: 3-5 working days
   3. Cost: 500-800 RON
   4. Delivarable: ORC certificate + CUI assignment
   
   Output:
   - CAP Federation C allocated: [e.g., 4XXXXXXXXXX]
   ```

2. **Cooperative Outreach (Owner: Business Development)**
   ```bash
   Outreach Protocol:
   
   Contact Top 20 Prospects (Week 2)
   - Priority: High-capacity, multi-product co-ops
   - Method: Phone + Email introduction
   - Meeting: Schedule 30-min presentation (Week 3)
   
   Email Template:
   
   Subject: CAP Federation Invitation - Partnership Opportunity
   
   [Cooperative Name],
   
   We are establishing Gospodarii de Altadata CAP - a federation of agricultural cooperatives 
   to supply bulk products to institutional buyers (SEAP, NATO, UN).
   
   We invite [Cooperative Name] to become a founding member. Benefits:
   - Access to contracts 50K-500K EUR (unattainable individually)
   - 90% of contract value flows directly to members
   - Unified quality certification (ISO 22000)
   - Guaranteed volume commitments (we aggregate orders)
   
   We request a 30-min meeting to discuss membership terms.
   
   Executive Director: [Name]
   Phone: +40 xxx xxx xxx
   Email: executive@gospodariicapat.ro
   
   Required Documents for Meeting:
   - CAEN certificate
   - Last 2 financial statements
   - Production capacity by product
   - Current quality certifications
   ```

3. **Hiring - Executive Director (Owner: Board)**
   ```bash
   Job Title: Executive Director, Gospodarii de Altadata CAP
   
   Key Requirements:
   - 5+ years experience: agricultural supply chain OR procurement
   - Understanding: cooperative business models
   - Language: Romanian (native), English (business level)
   - Location: Flexible (can be hybrid/remote)
   
   Key Responsibilities:
   - Cooperative recruitment (15 co-ops in 4 weeks)
   - Subcontracting partnerships with military suppliers
   - SEAP/NSPA/UNGM registration
   - Day-to-day operations coordination
   
   Compensation:
   - Base Salary: 2000-3000 EUR/month
   - Performance Bonus: 2-5% of Year 1 revenue (up to 65K EUR)
   - Equity Option: 0.5% of federation (after 2 years)
   
   Timeline:
   - Job posting: Week 2
   - Interviews: Week 3
   - Offer: Week 3
   - Start date: Week 4
   ```

4. **Quality Pre-Assessment (Owner: Quality Manager - if hired, or Executive Director)**
   ```bash
   Select Certification Bodies:
   
   For HACCP (Mandatory baseline):
   - Option A: Romanian Society for Quality Management (SRCQM)
   - Option B: SGS Romania
   - Option C: TÜV Romania
   
   Selection Criteria:
   - Agricultural experience: Required
   - Timeline: 8-12 weeks for certification
   - Cost: 5,000-8,000 RON (1,000-1,600 EUR) per member
   - Multi-member discount: Request quote for 15 members
   
   Action:
   - Request quotes from 3 bodies
   - Select body: Week 2 decision
   - Sign contracts with selected body (Week 3)
   
   For ISO 9001 (Optional, high priority):
   - Timeline: 12-16 weeks
   - Cost: 15,000-25,000 RON (3,000-5,000 EUR) for federation
   
   For ISO 22000 (Mandatory for NSPA):
   - Timeline: 12-20 weeks
   - Cost: 20,000-35,000 RON (4,000-7,000 EUR) for federation
   
   Recommendation:
   - Start HACCP: Week 3 (all 15 members)
   - Start ISO 9001: Week 4 (federation-level)
   - Start ISO 22000: Week 6 (for NSPA preparation)
   ```

**Week 2 Checklist:**
- [ ] ORC application filed (all documents ready)
- [ ] Executive Director job posted
- [ ] 20 co-op outreach emails sent
- [ ] Quality certification bodies researched (3 quotes requested)
- [ ] Budget: 8K-10K EUR allocated/expensed

---

### Week 3: SEAP Registration & Subcontracting Outreach

**Owner:** Executive Director
**Investment:**
- ORC registration fees: 500-800 RON
- Meeting costs: 1K-2K EUR
- **Total Week 3: 1.5K-2.5K EUR**

**Tasks:**

1. **SEAP/SICAP Registration (Owner: Executive Director)**
   ```bash
   Registration Steps:
   
   1. Create Account:
   - Portal: https://sicap.e-licitatie.ro
   - Required: CAP CUI (obtained Week 2-3)
   - Document: ORC certificate
   - Document: Tax certificate (ANAF)
   
   2. Complete Supplier Profile:
   - Company info: CAP Federation details
   - Product categories: 
     * 03: Cereals (15%)
     * 15: Food & agricultural products (60%)
     * 22: Animal feed (15%)
     * 032: Fruit & vegetables (10%)
   - Geographic coverage: Multi-county
   - Certifications: HACCP (pending), ISO 9001 (planned)
   
   3. Upload Documents:
   - ORC certificate
   - Fiscal certificate (ANAF)
   - Tax clearance certificate
   - Identity of legal representative
   
   Timeline:
   - Account creation: 1 day
   - Profile verification: 2-3 days
   - Total: 1 week (Week 3)
   
   Cost:
   - Registration fee: ~500 RON
   - Verification: Free
   
   Status Check:
   - Login at: sicap.e-licitatie.ro
   - Verify: "Supplier" status active
   ```

2. **Subcontracting Meetings (Owner: Executive Director + Business Dev)**
   ```bash
   Target Suppliers (from Week 1 research):
   
   NISARA IMPEX S.R.L.
   - Contact: [Name] (from research)
   - Meeting Topic: Subcontracting 10-20% capacity
   - Value Proposition:
     * CAP can guarantee steady supply from 15 co-ops
     * Multi-county production = seasonal stability
     * 5-12% cost advantage (we take lower margin)
     * We handle quality control, you handle client relationships
   - Meeting Agenda:
     1. Current demand vs capacity (identify gaps)
     2. CAP production profile (15 co-ops, 5,000 tons/year)
     3. Proposed agreement: 10-20% subcontract
     4. Quality alignment: HACCP/ISO 22000
     5. Pricing: CAP takes 8% margin vs 15-20% industry
   - Expected Outcome: Letter of intent or conditional agreement
   
   MATRA S.R.L.
   - Contact: [Name]
   - Meeting: Similar structure to NISARA
   - Specific focus: Bread/wheat sector (MATRA strong in bread)
   
   EUROGRUP BOGDAN
   - Contact: [Name]
   - Meeting: Similar structure
   - Specific focus: Regional coverage (explore multi-county collaboration)
   
   Meeting Protocol:
   - Number of meetings: 1 primary, 1 follow-up per supplier
   - Duration: 45-60 minutes each
   - Preparation: CAP One-Pager (see below)
   
   One-Pager Content:
   CAP Federation - Partner Profile
   ================================
   Entity: Gospodarii de Altadata CAP (CUI: 4XXXXXXXXX)
   Established: [Month 2026]
   Members: 15 founding cooperatives (4,500 tons/year)
   Focus: Wheat, rice, potatoes, vegetables, dairy
   Quality: HACCP (in progress), ISO 9001 (planned), ISO 22000 (planned)
   Margin: 8% (industry average 15-25%)
   Geographic: Multi-county (Constanța, Brașov, Arad, Timiș, Dolj)
   
   Partnership Offer:
   - Subcontract capacity: 10-20% of your contracts
   - Commitments: On-time delivery, quality guaranteed
   - Price: Industry -7% (we pass on our cost advantage)
   - Track Record: Build with you through first 3 contracts
   
   Contacts:
   Executive Director: [Name], +40 xxx xxx xxx
   Board Chair: [Name]
   ```

3. **Recruitment Progress (Owner: Executive Director + Business Dev)**
   ```bash
   Week 3 Goal: 5-8 LOI (Letter of Intent) signed
   
   Meetings with Interested Co-ops (from Week 2 outreach):
   - Schedule: 10-12 meetings
   - Target conversion: 5-8 LOIs (50-60% conversion)
   
   LOI Template:
   
   LETTER OF INTENT - CAP MEMBERSHIP
   ==================================
   
   Date: [Date]
   To: Gospodarii de Altadata CAP
   From: [Cooperative Name], CUI [CUI]
   
   The undersigned, as legal representative of [Cooperative Name], hereby expresses 
   intent to join the Gospodarii de Altadata Cooperative Federation (CAP) as a 
   founding member.
   
   Commitments:
   1. [Cooperative] will supply agricultural products to CAP as per demand
   2. [Cooperative] will implement HACCP certification (timeline: 8 weeks)
   3. [Cooperative] will work toward ISO 22000 (timeline: 16-20 weeks)
   4. [Cooperative] agrees to 90/10 revenue split (90% to member, 10% to CAP)
   5. [Cooperative] commits to production capacity: [X] tons/year
   
   CAP Commitments (contingent):
   1. CAP will aggregate orders and distribute to members
   2. CAP will provide HACCP implementation support (cost-sharing)
   3. CAP will pay members within 30 days of delivery
   4. CAP will bid on contracts 50K-500K EUR range
   
   Next Steps:
   - Review: Legal review of full membership agreement (Week 4)
   - Signing: Full membership agreement (Week 4-5)
   
   Signed: _________________________
   Name: [Representative Name]
   Position: [Position]
   
   Date: _________________________
   ```
   
4. **Hiring Completion (Owner: Board)**
   ```bash
   Executive Director Role:
   
   Job Offer:
   - Role: Executive Director, CAP Federation
   - Reports to: Board of Directors
   - Start date: Week 4
   - Probation: 3 months
   
   Compensation Package:
   - Base: 2,500 EUR/month
   - Bonus: 5% of Year 1 revenue (up to 75K if year 1 is 1.5M EUR)
   - Expenses: Travel, phone (up to 500 EUR/month)
   - Benefits: Health insurance, 20 days vacation
   
   Key Performance Indicators (Year 1):
   - KPI 1: 15 cooperatives signed (Months 1-4)
   - KPI 2: First subcontract agreement (Month 4)
   - KPI 3: First direct SEAP award (Month 6-7)
   - KPI 4: Cumulative revenue: 650K-1.3M EUR (Year 1)
   
   Board Expectations:
   - Weekly status reports to Board
   - Monthly financial reviews
   - Strategic partnership development
   ```

**Week 3 Checklist:**
- [ ] SEAP/SICAP account created and verified
- [ ] Subcontracting meetings held with 3 suppliers (NISARA, MATRA, EUROGRUP)
- [ ] LOIs signed with 5-8 cooperatives
- [ ] Executive Director hired (start Week 4)
- [ ] ORC registration approved (if filed Week 2)

---

## Implementation Summary Dashboard

### Phase 1 Progress Tracker

| Week | Milestone | Status | Owner | Revenue |
|------|-----------|--------|-------|---------|
| 1 | Founding kickoff | ✅ Complete | Board | 0 EUR |
| 1 | 50 co-op database | ✅ Complete | Business Dev | 0 EUR |
| 1 | Military supplier research | ✅ Complete | Business Dev | 0 EUR |
| 2 | ORC registration filed | 🟡 In Progress | Legal Counsel | 0 EUR |
| 2 | 20 co-op outreach | ✅ Complete | Business Dev | 0 EUR |
| 2 | Executive Director hiring started | 🟡 In Progress | Board | 0 EUR |
| 3 | SEAP registration | 🟡 Planned | Exec Director | 0 EUR |
| 3 | Supplier meetings | 🟡 Planned | Exec Director | 0 EUR |
| 4 | First subcontract agreement | 🟢 Planned | Exec Director | 0 EUR |
| 5 | 15 co-ops signed | 🟢 Planned | Exec Director | 0 EUR |
| 6-7 | First delivery | 🟢 Planned | Operations | **50K-100K EUR** |

### Investment Tracker

| Category | Week 1 | Week 2 | Week 3 | Week 4 | Phase 1 Total |
|----------|--------|--------|--------|--------|--------------|
| Legal setup | 2K | 5K | 1K | 2K | 10K |
| Quality (HACCP start) | 0 | 2K | 5K | 10K | 17K |
| Personnel (Exec Director) | 0 | 0 | 0 | 2.5K x 4 | 10K |
| Operations | 0 | 3K | 1.5K | 5K | 9.5K |
| Capital reserve | 10K | 10K | 10K | 10K | 40K |
| **Total** | **12K** | **20K** | **17.5K** | **29.5K** | **79K EUR** |

### Team Structure

| Role | When Hired | Responsibility | Reporting To |
|------|------------|-----------------|--------------|
| Board Chair | Week 1 | Strategic governance | Members (voting) |
| Executive Director | Week 4 start | Day-to-day operations | Board |
| Business Development Manager | Week 6 start | Co-op recruitment, supplier partnerships | Exec Director |
| Quality Manager | Week 7 start | HACCP/ISO implementation | Exec Director |
| Operations Coordinator | Week 8 start | Logistics, delivery coordination | Exec Director |

### Immediate Next Actions (Weeks 4-5)

1. **Week 4 Priority:**
   - [ ] ORC registration complete (if not finished Week 3)
   - [ ] First subcontract agreement signed (NISARA or MATRA)
   - [ ] Executive Director starts (Monday Week 4)
   - [ ] HACCP contracts signed with 10 co-ops (remaining 5 Week 5)
   - [ ] SEAP supplier profile complete & active

2. **Week 5 Priority:**
   - [ ] All 15 membership agreements signed
   - [ ] Bank account fully operational (CAP CUI active)
   - [ ] First subcontract order received
   - [ ] Quality control framework operational
   - [ ] Member portal/CMS setup (if selected)

---

## Risk Mitigation Plan

### Phase 1 Risks & Contingencies

| Risk | Likelihood | Impact | Mitigation | Contingency |
|------|------------|--------|------------|-------------|
| ORC registration delayed | LOW | HIGH | Use expedited service (+24h for +500 RON) | Start subcontracting as partnership agreement, finalize ORC later |
| Co-op recruitment insufficient | MEDIUM | HIGH | Expand to 25 prospect list | Reduce founding members to 10-12 (minimum viable) |
| Supplier subcontracting rejected | MEDIUM | MEDIUM | Contact all 3 researched suppliers | Bid directly on SEAP (lower value contracts) |
| Executive Director not hired by Week 4 | LOW | HIGH | Extend search by 2 weeks | Interim: Board member acts as ED (part-time) |
| HACCP cost over budget | MEDIUM | LOW | Negotiate multi-member bulk discount | Implement basic HACCP in-house (3K EUR) vs external (8K EUR) |

---

## Document Templates Repository

All templates referenced in this guide are available at:

`/opt/ACTIVE/IDEAS/NATO/OPENCODE/templates/`

- `constitution_template.md`
- `membership_agreement_template.md`
- `loi_template.md`
- `subcontract_agreement_template.md`
- `seap_registration_guide.md`
- `quality_checklist_haccp.md`
- `email_templates/` (outreach emails)

**Next Section:** See `week_4_delivery.md` for Week 4-13 detailed plan
