import uuid
import logging
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    import stripe as _stripe
except ImportError:
    _stripe = None

STRIPE_ENABLED = bool(settings.stripe_secret_key) and _stripe is not None
if STRIPE_ENABLED:
    _stripe.api_key = settings.stripe_secret_key


def create_checkout(ad, payment_id: int, success_url: str, cancel_url: str) -> dict:
    """Create a provider checkout session. Falls back to a sandbox session
    (no real charge) when Stripe is not configured, so the flow is testable."""
    amount = settings.ad_publish_price_cents
    if STRIPE_ENABLED:
        session = _stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": settings.currency,
                    "product_data": {"name": f"Publish ad: {ad.title}"},
                    "unit_amount": amount,
                },
                "quantity": 1,
            }],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"payment_id": str(payment_id), "ad_id": str(ad.id)},
        )
        return {"session_id": session.id, "checkout_url": session.url, "sandbox": False}

    session_id = f"sandbox_{uuid.uuid4().hex}"
    return {
        "session_id": session_id,
        "checkout_url": f"/checkout/sandbox?payment_id={payment_id}",
        "sandbox": True,
    }


def verify_webhook(payload: bytes, sig_header: str):
    """Verify and parse a Stripe webhook event. Returns the event dict or None."""
    if not STRIPE_ENABLED or not settings.stripe_webhook_secret:
        return None
    try:
        return _stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except Exception as e:
        logger.error(f"Stripe webhook verification failed: {e}")
        return None
