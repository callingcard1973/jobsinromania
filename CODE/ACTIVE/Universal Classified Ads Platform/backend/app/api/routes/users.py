from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ...core.database import get_db
from ...core.deps import get_current_user
from ...core.security import verify_password, get_password_hash
from ...models.user import User
from ...models.ad import Ad
from ...api.schemas import UserResponse, AdResponse
from ...api.schemas.user import UserUpdate, PasswordChange

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = data.model_dump(exclude_unset=True)
    if "email" in update_data and update_data["email"] != current_user.email:
        if db.query(User).filter(User.email == update_data["email"]).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    current_user.password_hash = get_password_hash(data.new_password)
    db.commit()


@router.get("/me/ads", response_model=List[AdResponse])
async def list_my_ads(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Ad).filter(Ad.user_id == current_user.id).order_by(Ad.created_at.desc()).all()
