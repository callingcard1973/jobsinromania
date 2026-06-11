from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base
from .user import AdStatus


class Ad(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    price = Column(Numeric(12, 2), nullable=True)
    location = Column(String(200), nullable=False)
    contact_info = Column(String(500), nullable=True)
    tags = Column(String(500), nullable=True)
    status = Column(String(20), default=AdStatus.DRAFT, index=True)
    is_featured = Column(Boolean, default=False)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="ads")
    media = relationship("AdMedia", back_populates="ad", cascade="all, delete-orphan")
    external_posts = relationship("ExternalPost", back_populates="ad", cascade="all, delete-orphan")