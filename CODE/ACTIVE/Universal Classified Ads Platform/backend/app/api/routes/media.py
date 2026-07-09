from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
import uuid
import logging
from PIL import Image, ImageFile

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import get_settings
from app.models.ad import Ad
from app.models.media import AdMedia
from app.models.user import User
from app.api.schemas import MediaResponse

router = APIRouter(prefix="/ads/{ad_id}/media", tags=["media"])
settings = get_settings()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_image(file: UploadFile, file_size: int) -> bool:
    if file.content_type not in settings.allowed_image_types.split(','):
        return False
    if file_size > settings.max_upload_size:
        return False
    return True


def create_thumbnail(image_path: str, thumbnail_path: str, size=(300, 300)) -> bool:
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            img.save(thumbnail_path, optimize=True, quality=85)
        return True
    except Exception as e:
        logger.error(f"Failed to create thumbnail: {e}")
        return False


@router.post("/", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    ad_id: int,
    file: UploadFile = File(...),
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

    os.makedirs(settings.upload_dir, exist_ok=True)

    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(settings.upload_dir, unique_filename)
    thumbnail_path = os.path.join(settings.upload_dir, f"thumb_{unique_filename}")

    contents = await file.read()
    file_size = len(contents)

    if not validate_image(file, file_size):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file"
        )

    with open(file_path, "wb") as f:
        f.write(contents)

    thumbnail_created = create_thumbnail(file_path, thumbnail_path)

    media = AdMedia(
        ad_id=ad_id,
        file_path=file_path,
        thumbnail_path=thumbnail_path if thumbnail_created else None,
        original_filename=file.filename,
        file_size=file_size,
        mime_type=file.content_type
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    return media


@router.get("/", response_model=List[MediaResponse])
async def list_ad_media(
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

    media_items = db.query(AdMedia).filter(AdMedia.ad_id == ad_id).all()
    return media_items


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    ad_id: int,
    media_id: int,
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

    media = db.query(AdMedia).filter(
        AdMedia.id == media_id,
        AdMedia.ad_id == ad_id
    ).first()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )

    if os.path.exists(media.file_path):
        os.remove(media.file_path)
    if media.thumbnail_path and os.path.exists(media.thumbnail_path):
        os.remove(media.thumbnail_path)

    db.delete(media)
    db.commit()