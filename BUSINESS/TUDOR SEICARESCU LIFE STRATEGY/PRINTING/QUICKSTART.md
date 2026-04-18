# Tudor Printing House — MVP Quickstart

## What's Built

**Tier 1 - Ready Now:**
- ✓ Lulu API client (`lulu_api_client.py`) — Full auth, file upload, job creation, tracking
- ✓ FastAPI backend (`app.py`) — Web interface + order management
- ✓ HTML form — Customer upload interface

**Tier 2 - Next:**
- Database (SQLAlchemy + PostgreSQL)
- Stripe payment integration
- Email notifications
- Admin dashboard

---

## How to Run (5 minutes)

### 1. Install dependencies

```bash
cd D:\MEMORY\PRINTING
pip install -r requirements.txt
```

### 2. Verify .env is in place

```bash
cat D:\MEMORY\PRINTING\.env
```

Should contain:
```
LULU_CLIENT_KEY=473ca6f0-0430-4edb-8ce4-4ee58009100c
LULU_CLIENT_SECRET=5SqvbLxGYPFKgmba0ffmxYcjZwHwwqBR
```

### 3. Start FastAPI server

```bash
cd D:\MEMORY\PRINTING
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 4. Visit website

Open browser: **http://localhost:8000**

You'll see:
- Upload form for cover PDF + interior PDF
- Title, author, quantity, shipping fields
- "Create Order" button

### 5. Test order creation

1. Create test PDFs (or use any PDFs)
2. Fill form
3. Click "Create Order"
4. See order ID + Lulu job ID returned

---

## API Endpoints

### Public

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Homepage with upload form |
| POST | `/api/orders` | Create new print order |
| GET | `/api/orders/{order_id}` | Get order details + status |
| GET | `/api/orders` | List all orders (paginated) |
| GET | `/api/health` | Health check |

### Example: Create Order

```bash
curl -X POST http://localhost:8000/api/orders \
  -F "title=My Book" \
  -F "author=John Doe" \
  -F "cover=@cover.pdf" \
  -F "interior=@interior.pdf" \
  -F "quantity=10" \
  -F "product_id=3x5_booklet" \
  -F "shipping_name=John Doe" \
  -F "shipping_street=123 Main St" \
  -F "shipping_city=New York" \
  -F "shipping_state=NY" \
  -F "shipping_postcode=10001" \
  -F "shipping_country=US"
```

Response:
```json
{
  "order_id": "a1b2c3d4",
  "lulu_job_id": "job_12345",
  "status": "processing",
  "total_cost": "45.99",
  "message": "Order created successfully"
}
```

### Example: Check Order Status

```bash
curl http://localhost:8000/api/orders/a1b2c3d4
```

---

## File Structure

```
D:\MEMORY\PRINTING\
├── .env                     # Lulu credentials (secure)
├── CLAUDE.md               # Business model
├── LULU_API_SETUP.md       # API documentation
├── API_VALIDATION_REPORT.md # Test results
├── lulu_api_client.py      # Lulu API wrapper
├── app.py                  # FastAPI backend
├── requirements.txt        # Python dependencies
├── uploads/                # Uploaded PDFs (local temp storage)
└── QUICKSTART.md           # This file
```

---

## Next Steps

### Immediate (Week 1)

1. Test MVP locally with real PDFs
2. Verify order creation → Lulu → printing
3. Add Stripe payment integration
4. Deploy to production server

### Short-term (Week 2-3)

1. Add PostgreSQL database
2. Implement customer accounts
3. Add email notifications
4. Create admin dashboard

### Medium-term (Week 4+)

1. Cover design templates
2. ISBN integration
3. Distribution to Amazon KDP, IngramSpark
4. Multi-language support

---

## Testing Checklist

- [ ] Run `python lulu_api_client.py` — Test token generation
- [ ] Start FastAPI server — `python -m uvicorn app:app --reload`
- [ ] Visit http://localhost:8000 — See homepage
- [ ] Upload test PDFs — Check `/uploads/` for saved files
- [ ] Check order response — Contains order_id + lulu_job_id
- [ ] Query order status — `GET /api/orders/{order_id}`
- [ ] Check Lulu account — Verify print jobs created

---

## Revenue Model

**Price:** €15 per 200-page book
**Cost:** €8 per book (Lulu)
**Margin:** €7 per book (46%)

**Targets:**
- 10 books/day = €70/day = €2,100/month
- 100 books/day = €700/day = €21,000/month

---

## Deployment

When ready for production:

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Deploy to:
- Heroku (easiest, €7-50/month)
- DigitalOcean (€5-12/month)
- AWS EC2 (pay-as-you-go)

---

## Troubleshooting

### "Token error 404"
- Check Lulu endpoint: should be `https://api.lulu.com/auth/realms/glasstree/protocol/openid-connect/token`
- Verify .env file has correct credentials

### "File not found"
- Make sure test PDFs exist or upload real ones
- Check file path is correct

### "Order creation failed"
- Check Lulu API is responding: `curl https://api.lulu.com/print-jobs/`
- Verify shipping address format (all fields required)

---

## Support

- Lulu API Docs: https://api.lulu.com/docs/
- FastAPI Docs: https://fastapi.tiangolo.com/
- This project: D:\MEMORY\PRINTING\CLAUDE.md

---

**Status:** MVP ready for testing  
**Time to first order:** 5 minutes  
**Time to production:** 1-2 weeks
