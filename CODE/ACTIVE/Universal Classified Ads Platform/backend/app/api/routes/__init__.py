from .auth import router as auth_router
from .ads import router as ads_router
from .media import router as media_router
from .admin import router as admin_router
from .users import router as users_router
from .categories import router as categories_router
from .payments import router as payments_router

__all__ = [
    "auth_router", "ads_router", "media_router", "admin_router",
    "users_router", "categories_router", "payments_router",
]