from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime


class PaymentConfig(BaseModel):
    stripe_enabled: bool
    publishable_key: str
    amount_cents: int
    currency: str


class CheckoutResponse(BaseModel):
    payment_id: int
    session_id: str
    checkout_url: str
    sandbox: bool
    amount_cents: int
    currency: str


class PaymentResponse(BaseModel):
    id: int
    ad_id: int
    user_id: int
    amount: Decimal
    currency: str
    provider: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
