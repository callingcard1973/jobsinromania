from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime, timezone
from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user, get_current_moderator, get_current_admin
from app.models.ad import Ad, AdStatus
from app.models.category import Category
from app.models.user import User
from app.api.schemas import AdCreate, AdUpdate, AdResponse, AdModerationAction, AdSearchFilters

router = APIRouter(prefix="/ads", tags=["ads"])


def _validate_category(db: Session, slug: Optional[str]) -> None:
    if slug is None:
        return
    if db.query(Category).count() == 0:
        return
    valid = db.query(Category).filter(Category.slug == slug, Category.is_active == True).first()
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or inactive category: {slug}",
        )


@router.post("/", response_model=AdResponse, status_code=status.HTTP_201_CREATED)
async def create_ad(
    ad_data: AdCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    _validate_category(db, ad_data.category)
    ad = Ad(
        user_id=current_user.id,
        **ad_data.model_dump(),
        status=AdStatus.DRAFT
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


@router.get("/", response_model=List[AdResponse])
async def list_ads(
    response: Response,
    status: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    featured_only: bool = False,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
    sort: str = Query("newest", pattern="^(newest|oldest|featured)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    query = db.query(Ad)
    is_privileged = bool(current_user and current_user.role in ["moderator", "admin"])

    if not is_privileged:
        if not status:
            query = query.filter(Ad.status == AdStatus.PUBLISHED)
        elif status != AdStatus.PUBLISHED:
            raise HTTPException(
                status_code=403,
                detail="Only moderators/admins can view non-published ads"
            )
        now = datetime.utcnow()
        query = query.filter(or_(Ad.expires_at == None, Ad.expires_at > now))

    if status:
        query = query.filter(Ad.status == status)
    if category:
        query = query.filter(Ad.category == category)
    if location:
        query = query.filter(Ad.location.ilike(f"%{location}%"))
    if min_price is not None:
        query = query.filter(Ad.price >= min_price)
    if max_price is not None:
        query = query.filter(Ad.price <= max_price)
    if featured_only:
        query = query.filter(Ad.is_featured == True)
    if created_from is not None:
        query = query.filter(Ad.created_at >= created_from)
    if created_to is not None:
        query = query.filter(Ad.created_at <= created_to)
    if search:
        query = query.filter(
            or_(
                Ad.title.ilike(f"%{search}%"),
                Ad.description.ilike(f"%{search}%")
            )
        )

    total = query.count()
    if sort == "oldest":
        query = query.order_by(Ad.created_at.asc())
    elif sort == "featured":
        query = query.order_by(Ad.is_featured.desc(), Ad.created_at.desc())
    else:
        query = query.order_by(Ad.created_at.desc())

    ads = query.offset(skip).limit(limit).all()
    response.headers["X-Total-Count"] = str(total)
    return ads


@router.get("/{ad_id}", response_model=AdResponse)
async def get_ad(
    ad_id: int,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    is_owner_or_mod = bool(
        current_user
        and (current_user.id == ad.user_id or current_user.role in ["moderator", "admin"])
    )

    if ad.status != AdStatus.PUBLISHED and not is_owner_or_mod:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if (
        ad.expires_at is not None
        and ad.expires_at <= datetime.utcnow()
        and not is_owner_or_mod
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    return ad


@router.put("/{ad_id}", response_model=AdResponse)
async def update_ad(
    ad_id: int,
    ad_data: AdUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    if ad.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    update_data = ad_data.model_dump(exclude_unset=True)
    if "category" in update_data:
        _validate_category(db, update_data["category"])
    for field, value in update_data.items():
        setattr(ad, field, value)

    db.commit()
    db.refresh(ad)
    return ad


@router.delete("/{ad_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ad(
    ad_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    if ad.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    db.delete(ad)
    db.commit()


@router.post("/{ad_id}/submit", response_model=AdResponse)
async def submit_ad_for_review(
    ad_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    if ad.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    if ad.status not in [AdStatus.DRAFT, AdStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft or rejected ads can be submitted"
        )

    ad.status = AdStatus.PENDING_REVIEW
    db.commit()
    db.refresh(ad)
    return ad


@router.post("/{ad_id}/approve", response_model=AdResponse)
async def approve_ad(
    ad_id: int,
    current_user: User = Depends(get_current_moderator),
    db: Session = Depends(get_db)
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    if ad.status != AdStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ads pending review can be approved"
        )

    ad.status = AdStatus.APPROVED
    ad.rejection_reason = None
    db.commit()
    db.refresh(ad)
    return ad


@router.post("/{ad_id}/reject", response_model=AdResponse)
async def reject_ad(
    ad_id: int,
    action: AdModerationAction,
    current_user: User = Depends(get_current_moderator),
    db: Session = Depends(get_db)
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    if ad.status != AdStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only ads pending review can be rejected"
        )

    ad.status = AdStatus.REJECTED
    ad.rejection_reason = action.rejection_reason
    db.commit()
    db.refresh(ad)
    return ad


@router.post("/{ad_id}/publish", response_model=AdResponse)
async def publish_ad(
    ad_id: int,
    current_user: User = Depends(get_current_moderator),
    db: Session = Depends(get_db)
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    if ad.status not in [AdStatus.APPROVED, AdStatus.PUBLISHED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved ads can be published"
        )

    ad.status = AdStatus.PUBLISHED
    db.commit()
    db.refresh(ad)
    return ad


@router.post("/{ad_id}/feature", response_model=AdResponse)
async def feature_ad(
    ad_id: int,
    current_user: User = Depends(get_current_moderator),
    db: Session = Depends(get_db)
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    ad.is_featured = not ad.is_featured
    db.commit()
    db.refresh(ad)
    return ad


@router.post("/{ad_id}/archive", response_model=AdResponse)
async def archive_ad(
    ad_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ad = db.query(Ad).filter(Ad.id == ad_id).first()
    if not ad:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ad not found"
        )

    if ad.user_id != current_user.id and current_user.role not in ["moderator", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    ad.status = AdStatus.ARCHIVED
    db.commit()
    db.refresh(ad)
    return ad