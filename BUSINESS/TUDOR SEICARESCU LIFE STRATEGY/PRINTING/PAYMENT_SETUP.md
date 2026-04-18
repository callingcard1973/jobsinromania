# Stripe Payment Setup for Tudor Printing House

**Cost:** Free (Stripe charges 2.9% + €0.30 per transaction)  
**Setup time:** 10 minutes  
**Revenue flow:** Customer → Stripe → Your account → Lulu payment

---

## Step 1: Create Stripe Account (2 min)

1. Go to https://dashboard.stripe.com/register
2. Sign up with email
3. Complete identity verification
4. Dashboard ready

---

## Step 2: Get API Keys (2 min)

1. Navigate to **Developers → API Keys**
2. Copy both keys:
   - **Publishable Key** (starts with `pk_`)
   - **Secret Key** (starts with `sk_`)

⚠️ **NEVER share secret key**

---

## Step 3: Update .env

Add to `D:\MEMORY\PRINTING\.env`:

```
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxx
```

For now, leave webhook secret blank (add after deployment).

---

## Step 4: Install Stripe

```bash
cd D:\MEMORY\PRINTING
pip install stripe
```

---

## Payment Flow

### Customer Creates Order

```
POST /api/orders
├─ Upload cover.pdf + interior.pdf
├─ Submit shipping address
└─ Order created (status: awaiting_payment)
```

**Response:**
```json
{
  "order_id": "a1b2c3d4",
  "status": "awaiting_payment",
  "total_cost": 150.00
}
```

### Customer Pays (Stripe Hosted Checkout)

```
POST /api/payment/create-intent
├─ order_id: "a1b2c3d4"
├─ amount: 150.00
└─ description: "Book: Title by Author"
```

**Response:**
```json
{
  "client_secret": "pi_xxxx_secret_xxxx",
  "publishable_key": "pk_test_xxxx",
  "amount": 150.00
}
```

Customer uses `client_secret` to open Stripe Checkout form.

### Stripe Notifies Backend (Webhook)

```
Stripe Event: payment_intent.succeeded
├─ Verify signature
├─ Update order status → "paid"
├─ Submit to Lulu print job
└─ Send confirmation email
```

---

## API Endpoints

### Create Payment Intent

```bash
POST /api/payment/create-intent
Content-Type: application/json

{
  "order_id": "a1b2c3d4",
  "amount": 150.00,
  "description": "Book: Two Exits, One Cooperative by Tudor"
}
```

**Response:** Payment intent with `client_secret`

### Confirm Payment

```bash
GET /api/payment/confirm/a1b2c3d4
```

**Response:**
```json
{
  "status": "succeeded",
  "order_id": "a1b2c3d4",
  "amount": 150.00,
  "currency": "eur",
  "succeeded": true
}
```

### Get Pricing

```bash
GET /api/payment/pricing?quantity=10&product_id=3x5_booklet
```

**Response:**
```json
{
  "quantity": 10,
  "price_per_book": 15.0,
  "customer_price": 150.00,
  "lulu_cost": 80.00,
  "margin_per_order": 70.00,
  "margin_percent": 46.67
}
```

---

## Frontend Integration (JavaScript)

```html
<!-- Load Stripe.js -->
<script src="https://js.stripe.com/v3/"></script>

<script>
  const stripe = Stripe('pk_test_xxxx'); // Your publishable key

  document.getElementById('payButton').addEventListener('click', async () => {
    // 1. Create payment intent
    const response = await fetch('/api/payment/create-intent', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        order_id: 'a1b2c3d4',
        amount: 150.00,
        description: 'Book: Title'
      })
    });

    const { client_secret } = await response.json();

    // 2. Redirect to Stripe Checkout
    const result = await stripe.redirectToCheckout({ sessionId: client_secret });

    if (result.error) {
      console.error(result.error.message);
    }
  });
</script>
```

---

## Testing (Stripe Test Mode)

Use test card: **4242 4242 4242 4242**

| Field | Value |
|-------|-------|
| Card | 4242 4242 4242 4242 |
| Expiry | Any future date (12/25) |
| CVC | Any 3 digits (123) |

**Result:** Payment succeeds in test mode

---

## Webhook Setup (Deployment Only)

After deploying to production:

1. Go to **Developers → Webhooks**
2. Add endpoint: `https://yourdomain.com/api/payment/webhook`
3. Select events:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `charge.refunded`
4. Copy webhook signing secret
5. Add to `.env`: `STRIPE_WEBHOOK_SECRET=whsec_xxxx`

---

## Revenue & Fees

**Per €150 Order:**
- Customer pays: €150.00
- Lulu cost: €80.00 (10 books × €8)
- Stripe fee: €4.44 (2.9% + €0.30)
- **Your profit: €65.56 (43.7%)**

**Monthly (100 orders):**
- Revenue: €15,000
- Costs: €8,000
- Stripe fees: €444
- **Profit: €6,556**

---

## Error Handling

```python
# Stripe will raise stripe.error.StripeError for:
- Invalid card
- Insufficient funds
- Lost connection
- Webhook signature mismatch
```

All handled in `stripe_handler.py` with logging.

---

## Deployment Checklist

- [ ] Stripe account created
- [ ] API keys in `.env`
- [ ] `stripe` installed (`pip install stripe`)
- [ ] Payment routes added to app
- [ ] Test payment with 4242 4242 4242 4242
- [ ] Confirm payment endpoint works
- [ ] Deploy to production
- [ ] Set up webhook in Stripe dashboard
- [ ] Test production webhook

---

## Troubleshooting

### "No Stripe keys configured"
- Check `.env` file
- Verify key names: `STRIPE_PUBLISHABLE_KEY`, `STRIPE_SECRET_KEY`

### "Invalid signature" on webhook
- Webhook secret must match Stripe dashboard
- Check `STRIPE_WEBHOOK_SECRET` in `.env`

### "Payment failed"
- Use test card 4242 4242 4242 4242
- Check Stripe dashboard logs for details

---

## Next Steps

1. ✓ Add payment routes
2. ✓ Create Stripe handler
3. Create HTML payment form (with Stripe.js)
4. Deploy to production
5. Update order status workflow:
   - Created → Awaiting Payment
   - Payment Confirmed → Submit to Lulu
   - Lulu Printing → In Transit
   - Delivered → Complete

---

**Status:** Payment integration ready to test  
**Time to payment flow:** 5 minutes  
**Cost:** 2.9% + €0.30 per transaction
