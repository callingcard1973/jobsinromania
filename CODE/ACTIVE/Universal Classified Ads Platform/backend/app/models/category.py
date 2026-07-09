from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from ..core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


DEFAULT_CATEGORIES = [
    ("real-estate", "Real Estate"),
    ("jobs", "Jobs"),
    ("services", "Services"),
    ("vehicles", "Vehicles"),
    ("electronics", "Electronics"),
    ("agriculture", "Agriculture"),
    ("miscellaneous", "Miscellaneous"),
]


def seed_default_categories(db) -> None:
    if db.query(Category).count() == 0:
        for slug, name in DEFAULT_CATEGORIES:
            db.add(Category(slug=slug, name=name, is_active=True))
        db.commit()
