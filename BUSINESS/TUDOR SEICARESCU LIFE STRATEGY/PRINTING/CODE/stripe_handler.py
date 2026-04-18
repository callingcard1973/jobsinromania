"""Stripe Payment Integration for Tudor Printing House"""

import os
import logging
from typing import Dict, Any
import stripe

logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class StripePayment:
    """Handle Stripe payment processing"""

    def __init__(self):
        self.publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
        if not stripe.api_key or not self.publishable_key:
            logger.warning("Stripe keys not configured")

    def create_payment_intent(
        self,
        order_id: str,
        amount_cents: int,
        description: str
    ) -> Dict[str, Any]:
        """
        Create Stripe payment intent for order

        Args:
            order_id: Tudor order ID
            amount_cents: Amount in cents (e.g., 1500 for €15.00)
            description: Order description

        Returns:
            {client_secret, order_id, amount, publishable_key}
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="eur",
                description=description,
                metadata={"order_id": order_id},
                automatic_payment_methods={"enabled": True}
            )

            logger.info(f"Payment intent created: {intent.id} (order: {order_id})")

            return {
                "client_secret": intent.client_secret,
                "order_id": order_id,
                "amount": amount_cents / 100,  # Convert to euros
                "publishable_key": self.publishable_key,
                "intent_id": intent.id
            }

        except Exception as e:
            logger.error(f"Payment intent error: {str(e)}")
            raise

    def confirm_payment(self, intent_id: str) -> Dict[str, Any]:
        """Get payment confirmation status"""
        try:
            intent = stripe.PaymentIntent.retrieve(intent_id)

            return {
                "status": intent.status,
                "order_id": intent.metadata.get("order_id"),
                "amount": intent.amount / 100,
                "currency": intent.currency,
                "succeeded": intent.status == "succeeded"
            }

        except Exception as e:
            logger.error(f"Confirmation error: {str(e)}")
            raise

    def create_customer(
        self,
        email: str,
        name: str,
        phone: str = None
    ) -> str:
        """Create Stripe customer for recurring orders"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                phone=phone
            )

            logger.info(f"Customer created: {customer.id}")
            return customer.id

        except Exception as e:
            logger.error(f"Customer creation error: {str(e)}")
            raise

    def create_webhook_endpoint(self, url: str) -> str:
        """Create Stripe webhook endpoint (run once during setup)"""
        try:
            endpoint = stripe.WebhookEndpoint.create(
                url=url,
                enabled_events=[
                    "payment_intent.succeeded",
                    "payment_intent.payment_failed",
                    "charge.refunded"
                ]
            )

            logger.info(f"Webhook created: {endpoint.id}")
            return endpoint.secret

        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            raise

    @staticmethod
    def verify_webhook_signature(body: bytes, signature: str, endpoint_secret: str) -> Dict:
        """Verify Stripe webhook is authentic"""
        try:
            event = stripe.Webhook.construct_event(
                body,
                signature,
                endpoint_secret
            )
            return event

        except ValueError:
            logger.error("Invalid webhook signature")
            raise

        except stripe.error.SignatureVerenceError:
            logger.error("Invalid signature verification")
            raise


# Pricing helper
def calculate_order_cost(quantity: int, product_id: str, base_price: float = 8.0) -> tuple:
    """
    Calculate total order cost

    Returns: (cost_for_lulu, customer_price, margin)
    """
    lulu_cost = quantity * base_price
    customer_price = quantity * 15.0  # €15 per book
    margin = customer_price - lulu_cost

    return (lulu_cost, customer_price, margin)
