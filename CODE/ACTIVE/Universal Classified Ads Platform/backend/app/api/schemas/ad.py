from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class AdStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class AdBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=10)
    category: str = Field(..., min_length=1, max_length=50)
    price: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=2)
    location: str = Field(..., min_length=1, max_length=200)
    contact_info: Optional[str] = Field(None, max_length=500)
    tags: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None


class AdCreate(AdBase):
    pass


class AdUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = Field(None, min_length=1, max_length=50)
    price: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=2)
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    contact_info: Optional[str] = Field(None, max_length=500)
    tags: Optional[str] = Field(None, max_length=500)
    expires_at: Optional[datetime] = None


class AdResponse(AdBase):
    id: int
    user_id: int
    status: str
    is_featured: bool
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AdModerationAction(BaseModel):
    rejection_reason: Optional[str] = None


class AdSearchFilters(BaseModel):
    category: Optional[str] = None
    location: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    status: Optional[str] = None
    search: Optional[str] = None
    featured_only: bool = False