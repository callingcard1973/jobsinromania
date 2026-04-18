#!/usr/bin/env python3
"""Tudor Printing House - FastAPI Main Application"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from routes import router
from payment_routes import router as payment_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App
app = FastAPI(
    title="Tudor Printing House",
    description="Print-on-demand platform",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router)
app.include_router(payment_router)


@app.get("/", response_class=HTMLResponse)
async def homepage():
    """Homepage with upload form"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tudor Printing House</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
            .form-group { margin: 15px 0; }
            input, select, textarea { width: 100%; padding: 8px; box-sizing: border-box; font-size: 14px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; font-size: 16px; }
            button:hover { background: #0056b3; }
            .result { margin-top: 20px; padding: 10px; border-radius: 5px; }
            .error { background: #f8d7da; color: #721c24; }
            .success { background: #d4edda; color: #155724; }
        </style>
    </head>
    <body>
        <h1>Tudor Printing House</h1>
        <p>Print your book on demand - Start at just €15</p>

        <form id="form">
            <div class="form-group">
                <label>Book Title *</label>
                <input type="text" id="title" placeholder="Enter title" required>
            </div>

            <div class="form-group">
                <label>Author *</label>
                <input type="text" id="author" placeholder="Enter author name" required>
            </div>

            <div class="form-group">
                <label>Cover PDF *</label>
                <input type="file" id="cover" accept=".pdf" required>
            </div>

            <div class="form-group">
                <label>Interior PDF *</label>
                <input type="file" id="interior" accept=".pdf" required>
            </div>

            <div class="form-group">
                <label>Quantity *</label>
                <input type="number" id="quantity" min="1" value="10" required>
            </div>

            <div class="form-group">
                <label>Product Type *</label>
                <select id="product" required>
                    <option value="3x5_booklet">3x5 Booklet</option>
                    <option value="5x8_paperback">5x8 Paperback</option>
                </select>
            </div>

            <div class="form-group">
                <label>Shipping Name *</label>
                <input type="text" id="name" placeholder="Full name" required>
            </div>

            <div class="form-group">
                <label>Street Address *</label>
                <input type="text" id="street" placeholder="123 Main St" required>
            </div>

            <div class="form-group">
                <label>City *</label>
                <input type="text" id="city" placeholder="City" required>
            </div>

            <div class="form-group">
                <label>State *</label>
                <input type="text" id="state" placeholder="State/Province" required>
            </div>

            <div class="form-group">
                <label>Postal Code *</label>
                <input type="text" id="postcode" placeholder="Postal code" required>
            </div>

            <div class="form-group">
                <label>Country Code *</label>
                <input type="text" id="country" placeholder="US, GB, DE, etc" required>
            </div>

            <button type="submit">Create Order</button>
        </form>

        <div id="result"></div>
        <div id="payment-container" style="display:none; margin-top:30px; padding:20px; border:1px solid #ddd; border-radius:5px;">
            <h3>Payment</h3>
            <form id="payment-form">
                <div id="payment-element" style="margin:20px 0;"></div>
                <button id="submit-payment" type="submit" style="width:100%; background:#28a745;">Pay €<span id="amount-display">0</span></button>
                <div id="payment-message" style="margin-top:10px; color:red;"></div>
            </form>
        </div>

        <script src="https://js.stripe.com/v3/"></script>
        <script>
            let stripe, elements, orderId, orderAmount;

            document.getElementById('form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const form = new FormData();
                form.append('title', document.getElementById('title').value);
                form.append('author', document.getElementById('author').value);
                form.append('cover', document.getElementById('cover').files[0]);
                form.append('interior', document.getElementById('interior').files[0]);
                form.append('quantity', document.getElementById('quantity').value);
                form.append('product_id', document.getElementById('product').value);
                form.append('shipping_name', document.getElementById('name').value);
                form.append('shipping_street', document.getElementById('street').value);
                form.append('shipping_city', document.getElementById('city').value);
                form.append('shipping_state', document.getElementById('state').value);
                form.append('shipping_postcode', document.getElementById('postcode').value);
                form.append('shipping_country', document.getElementById('country').value);

                try {
                    const res = await fetch('/api/orders', { method: 'POST', body: form });
                    const data = await res.json();
                    if (res.ok) {
                        orderId = data.order_id;
                        orderAmount = data.total_cost;
                        document.getElementById('result').innerHTML = `<div class="result success"><h3>Order Created!</h3><p><strong>Order ID:</strong> ${data.order_id}</p><p><strong>Status:</strong> ${data.status}</p><p><strong>Cost:</strong> €${data.total_cost}</p></div>`;
                        initPayment();
                    } else {
                        document.getElementById('result').innerHTML = `<div class="result error"><p>Error: ${data.detail}</p></div>`;
                    }
                } catch (e) {
                    document.getElementById('result').innerHTML = `<div class="result error"><p>Error: ${e.message}</p></div>`;
                }
            });

            async function initPayment() {
                const res = await fetch('/api/payment/create-intent', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({order_id: orderId, amount: orderAmount, description: `Book Order ${orderId}`})
                });
                const data = await res.json();
                stripe = Stripe(data.publishable_key);
                elements = stripe.elements({clientSecret: data.client_secret});
                const paymentElement = elements.create('payment');
                paymentElement.mount('#payment-element');
                document.getElementById('amount-display').textContent = orderAmount;
                document.getElementById('payment-container').style.display = 'block';
            }

            document.getElementById('payment-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const {error} = await stripe.confirmPayment({elements, redirect: 'if_required'});
                if (error) {
                    document.getElementById('payment-message').textContent = `Payment failed: ${error.message}`;
                } else {
                    const confirm = await fetch(`/api/payment/confirm/${orderId}`).then(r => r.json());
                    if (confirm.succeeded) {
                        document.getElementById('payment-container').innerHTML = `<div class="result success"><h3>Payment Successful!</h3><p>Your order is being processed. You'll receive a confirmation email shortly.</p></div>`;
                    }
                }
            });
        </script>
    </body>
    </html>
    """


@app.on_event("startup")
async def startup():
    logger.info("Tudor Printing House starting...")
    logger.info("Visit: http://localhost:8000")


if __name__ == "__main__":
    import uvicorn
  