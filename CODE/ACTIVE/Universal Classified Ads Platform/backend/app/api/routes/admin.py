from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...core.database import get_db
from ...core.deps import get_current_admin
from ...models.user import User
from ...models.ad import Ad
from ...api.schemas import UserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()
    total_ads = db.query(Ad).count()
    published_ads = db.query(Ad).filter(Ad.status == "published").count()
    pending_ads = db.query(Ad).filter(Ad.status == "pending_review").count()

    return {
        "total_users": total_users,
        "total_ads": total_ads,
        "published_ads": published_ads,
        "pending_ads": pending_ads
    }