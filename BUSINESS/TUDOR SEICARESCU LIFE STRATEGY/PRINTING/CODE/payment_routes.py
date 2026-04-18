"""Payment Routes - Stripe Integration for Tudor Printing House"""

import logging
from fastapi import APIRouter, HTTPException, Request
from stripe_handler import StripePayment, calculate_order_cost
import os

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/payment", tags=["payment"])

stripe_payment = StripePayment()

# In-memory payment tracking (replace with DB)
payments = {}


@router.post("/create-intent")
async def create_payment_intent(order_id: str, amount: float, description: str):
    """
    Create Stripe payment intent for order

    Args:
        order_id: Order ID from /api/orders
        amount: Order total in euros
        description: "Book: Title by Author"

    Returns:
        {client_secret, publishable_key, amount}
    """
    try:
        amount_cents = int(amount * 100)  # Convert to cents

        intent_data = stripe_payment.create_payment_intent(
            order_id=order_id,
            amount_cents=amount_cents,
            description=description
        )

        # Store payment record
        payments[order_id] = {
            "order_id": order_id,
            "amount": amount,
            "intent_id": intent_data["intent_id"],
            "status": "pending"
        }

        logger.info(f"Payment intent created for order {order_id}: €{amount}")

        return intent_data

    except Exception as e:
        logger.error(f"Payment intent error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/confirm/{order_id}")
async def confirm_payment(order_id: str):
    """
    Check payment status after customer completes checkout

    Returns:
        {status: "succeeded"|"processing"|"failed", order_id, amount}
    """
    try:
        if order_id not in payments:
            raise HTTPException(status_code=404, detail="Order not found")

        intent_id = payments[order_id]["intent_id"]
        confirmation = stripe_payment.confirm_payment(intent_id)

        # Update payment status
        payments[order_id]["status"] = confirmation["status"]

        logger.info(f"Payment status for {order_id}: {confirmation['status']}")

        return confirmation

    except Exception as e:
        logger.error(f"Confirmation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhooks (payment succeeded, failed, refunded)

    Set up webhook:
    1. Get endpoint secret from Stripe dashboard
    2. Add to .env: STRIPE_WEBHOOK_SECRET
    3. Test: stripe listen --forward-to localhost:8000/api/payment/webhook
    """
    try:
        body = await request.body()
        signature = request.headers.get("stripe-signature")
        endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        if not endpoint_secret:
            logger.warning("No webhook secret configured")
            return {"received": True}

        event = stripe_payment.verify_webhook_signature(
            body,
            signature,
            endpoint_secret
        )

        # Handle events
        if event["type"] == "payment_intent.succeeded":
            intent = event["data"]["object"]
            order_id = intent["metadata"].get("order_id")
            logger.info(f"Payment succeeded for order {order_id}")

            # TODO: Update order status in database
            # TODO: Send confirmation email
            # TODO: Trigger print job submission

        elif event["type"] == "payment_intent.payment_failed":
            intent = event["data"]["object"]
            order_id = intent["metadata"].get("order_id")
            logger.warning(f"Payment failed for order {order_id}")

            # TODO: Update order status
            # TODO: Send failure email

        elif event["type"] == "charge.refunded":
            charge = event["data"]["object"]
            logger.info(f"Charge refunded: {charge['id']}")

            # TODO: Handle refund

        return {"received": True}

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook error")


@router.get("/pricing")
async def get_pricing(quantity: int = 10, product_id: str = "3x5_booklet"):
    """
    Get pricing for a print order

    Returns:
        {customer_price: €150, lulu_cost: €80, margin: €70}
    """
    try:
        lulu_cost, customer_price, margin = calculate_order_cost(quantity, product_id)

        return {
            "quantity": quantity,
            "product_id": product_id,
            "price_per_book": 15.0,
            "customer_price": customer_price,
            "lulu_cost": lulu_cost,
            "margin_per_order": margin,
            "margin_percent": (margin / customer_price * 100)
        }

    except Exception as e:
        logger.error(f"Pricing error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
