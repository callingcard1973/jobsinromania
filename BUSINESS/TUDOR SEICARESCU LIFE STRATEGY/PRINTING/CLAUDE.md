# TUDOR PRINTING HOUSE

## What This Is

Print-on-demand business using Lulu API. Self-publishing platform for books, guides, and printed content. Zero inventory. Direct fulfillment.

---

## Core Business Model

**Customers:** Self-published authors, small businesses, coaches, consultants  
**Product:** Print books on-demand via Lulu API  
**Margin:** 20-40% (Lulu takes 40-50%, we keep difference)  
**Cost to start:** €0 (Lulu handles printing + shipping)  
**Revenue model:** Per-book commission OR white-label storefront  

---

## Lulu API Infrastructure

### API Endpoints
- **Print Job Creation:** POST `/print-jobs/` (create print orders)
- **Print Job Status:** GET `/print-jobs/{id}` (track orders)
- **Product Data:** GET `/products/` (available book sizes, formats)
- **File Upload:** POST `/files/` (upload PDF covers + interiors)

### Authentication
- API Key + Secret (production + sandbox)
- Bearer token generation
- Per-request authentication

### Supported Formats
- PDF interior (book pages)
- PDF cover (front + back + spine)
- Multiple product packages (paperback, hardcover, ebook, etc.)
- Shipping address management

### Capabilities
- Batch print jobs (multiple books in one order)
- Automatic shipping to customer addresses
- Order tracking via webhooks
- Worldwide delivery (170+ countries)

---

## "Tudor Printing House" Concept

### Phase 1: White-Label Storefront (MVP)

**What:** Website where customers upload their book PDF + cover  
**Process:**
1. Customer fills form: title, author, ISBN (optional)
2. Uploads interior PDF + cover files
3. Previews book on website
4. Places order (pays via Stripe)
5. We submit print job to Lulu API
6. Lulu prints + ships to customer

**Technology Stack:**
- Backend: FastAPI (Python)
- Database: PostgreSQL (book metadata)
- File storage: S3 or local
- Payment: Stripe
- Printing: Lulu API

**Revenue:**
- Customer pays €15 for 200-page book
- Lulu costs €8 (varies by format/pages)
- We keep €7 per book (46% margin)

**Scalability:**
- 10 books/day = €70/day = €2,100/month
- 50 books/day = €350/day = €10,500/month
- 100 books/day = €700/day = €21,000/month

---

### Phase 2: Self-Publishing Network

Add these features:
- Author dashboard (track sales, downloads, analytics)
- Cover design templates
- ISBN integration
- Distribution to other platforms (Amazon KDP, IngramSpark)
- Royalties tracking

---

### Phase 3: B2B Bulk Printing

Partner with:
- Corporate training programs (print training manuals)
- Educational publishers (textbooks on demand)
- Agencies (client deliverables)

Bulk pricing:
- 100+ units: 10-15% discount
- 1000+ units: 25-40% discount

---

## Implementation Roadmap

### Week 1-2: Setup
- [ ] Register Lulu API account (sandbox + production)
- [ ] Document API endpoints
- [ ] Create Python Lulu client library
- [ ] Test file upload + print job creation

### Week 3-4: MVP Website
- [ ] FastAPI backend
- [ ] Database schema (books, orders, users)
- [ ] File upload handler
- [ ] Stripe payment integration

### Week 5-6: Testing
- [ ] Upload test PDFs to Lulu
- [ ] Create test print jobs
- [ ] Verify shipping addresses
- [ ] Track order status via API

### Week 7-8: Launch
- [ ] Deploy website
- [ ] Marketing (target self-published authors)
- [ ] First 10 customers (soft launch)
- [ ] Feedback + iterations

---

## Files & Scripts

```
D:\MEMORY\PRINTING\
├── CLAUDE.md (this file)
├── lulu_api_client.py (Lulu API wrapper)
├── tudor_printing_house.py (main app)
├── stripe_integration.py (payment handling)
├── database.py (PostgreSQL models)
├── tests/ (unit tests)
└── templates/ (HTML for web interface)
```

---

## Revenue Potential

| Scenario | Books/Month | Revenue/Month | Annual |
|----------|-------------|---------------|--------|
| Hobby | 10 | €700 | €8,400 |
| Side hustle | 100 | €7,000 | €84,000 |
| Small business | 500 | €35,000 | €420,000 |
| Enterprise | 2,000+ | €140,000+ | €1.68M+ |

**Key:** Low customer acquisition cost (self-publishing community is active)

---

## Competitive Landscape

| Platform | Model | Margin | Ease |
|----------|-------|--------|------|
| Lulu direct | Self-serve | 20-30% | Easy |
| Amazon KDP | Distribution | 10-20% | Medium |
| IngramSpark | Wholesale | 5-15% | Hard |
| **Tudor Printing** | **White-label** | **40-50%** | **Easy** |

Our advantage: white-label takes friction out of self-publishing.

---

## Next Steps

1. Create Lulu API client library (lulu_api_client.py)
2. Test sandbox account (file upload + print job)
3. Build FastAPI backend
4. Deploy MVP website
5. Target first 100 self-published authors

---

## Credentials & Setup

**Lulu API:**
- Sandbox: (to be created)
- Production: (to be created)
- API Key: (store in .env)
- API Secret: (store in .env)

**Stripe:**
- Testing: (standard test keys)
- Production: (live keys after launch)

**Domain:**
- tudorprintinghouse.com (or variant)
- tudorprintinghouse.eu

---

## Resources

- [Lulu API Docs](https://api.lulu.com/docs/)
- [Lulu Developer Portal](https://developers.lulu.com/)
- [Lulu Getting Started Guide](https://help.api.lulu.com/en/support/solutions/articles/64000294079-how-do-i-get-started-)
- [Lulu API GitHub](https://github.com/luluapi)

---

**Status:** Concept phase  
**Time to MVP:** 6-8 weeks  
**Cost to launch:** €0 (free tools)  
**Time commitment:** 10-15 hours/week for launch  
**Expected first revenue:** 4-8 weeks after launch
