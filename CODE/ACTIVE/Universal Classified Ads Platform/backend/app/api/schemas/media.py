from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MediaResponse(BaseModel):
    id: int
    ad_id: int
    url: str
    thumbnail_url: Optional[str] = None
    original_filename: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True