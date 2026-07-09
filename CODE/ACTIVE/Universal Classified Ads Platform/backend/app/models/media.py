import os
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class AdMedia(Base):
    __tablename__ = "ad_media"

    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(Integer, ForeignKey("ads.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ad = relationship("Ad", back_populates="media")

    @property
    def url(self) -> str:
        return f"/uploads/{os.path.basename(self.file_path)}"

    @property
    def thumbnail_url(self):
        if not self.thumbnail_path:
            return None
        return f"/uploads/{os.path.basename(self.thumbnail_path)}"