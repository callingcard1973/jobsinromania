from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from ...core.database import get_db
from ...core.config import get_settings
from ...core.deps import get_current_user
from ...models.ad import Ad, AdStatus
from ...models.payment import Payment, PaymentStatus
from ...models.user import User
from ...api.schemas.payment import PaymentConfig, CheckoutResponse, PaymentResponse
from ...services import payments as pay_service

router = APIRouter(prefix="/payments", tags=["payments"])
settings = get_settings()


def _mark_paid(db: Session, payment: Payment, ref: str) -> None:
    payment.status = PaymentStatus.PAID
    payment.provider_payment_ref = ref
    ad = db.query(Ad).filter(Ad.id == payment.ad_id).first()
    if ad and ad.status in [AdStatus.DRAFT, AdStatus.REJECTED]:
        ad.status = AdStatus.PENDING_REVIEW
    db.commit()


@router.get("/config", response_model=PaymentConfig)
async def payment_config():
    return PaymentConfig(
        stripe_enabled=pay_service.STRIPE_ENABLED,
        publishable_key=settings.stripe_publishable_key,
        amount_cents=settings.ad_publish_price_cents,
        currency=settings.currency,
    )


@router.post("/ads/{ad_id}/checkout", response_model=CheckoutResponse)
async def create_ad_checkout(
    ad_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ad not found")
    if ad.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if ad.status not in [AdStatus.DRAFT, AdStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ad is not awaiting payment (must be draft or rejected)",
        )
    already_paid = (
        db.query(Payment)
        .filter(Payment.ad_id == ad_id, Payment.status == PaymentStatus.PAID)
        .first()
    )
    if already_paid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ad already paid for")

    payment = Payment(
        ad_id=ad.id,
        user_id=current_user.id,
        amount=Decimal(settings.ad_publish_price_cents) / 100,
        currency=settings.currency,
        provider="stripe" if pay_service.STRIPE_ENABLED else "sandbox",
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    base = str(request.base_url).rstrip("/")
    info = pay_service.create_checkout(
        ad,
        payment.id,
        success_url=f"{base}/my-ads?paid=1",
        cancel_url=f"{base}/my-ads?canceled=1",
    )
    payment.provider_session_id = info["session_id"]
    db.commit()

    return CheckoutResponse(
        payment_id=payment.id,
        session_id=info["session_id"],
        checkout_url=info["checkout_url"],
        sandbox=info["sandbox"],
        amount_cents=settings.ad_publish_price_cents,
        currency=settings.currency,
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    event = pay_service.verify_webhook(payload, sig)
    if event is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook")
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment_id = (session.get("metadata") or {}).get("payment_id")
        if payment_id:
            payment = db.query(Payment).filter(Payment.id == int(payment_id)).first()
            if payment and payment.status != PaymentStatus.PAID:
                _mark_paid(db, payment, session.get("payment_intent") or session.get("id"))
    return {"received": True}


@router.post("/sandbox/{payment_id}/confirm", response_model=PaymentResponse)
async def confirm_sandbox_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if pay_service.STRIPE_ENABLED and settings.environment == "production":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sandbox confirm disabled")
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if payment.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if payment.status != PaymentStatus.PAID:
        _mark_paid(db, payment, f"sandbox_intent_{payment_id}")
        db.refresh(payment)
    return payment


@router.get("/me", response_model=List[PaymentResponse])
async def my_payments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Payment)
        .filter(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
