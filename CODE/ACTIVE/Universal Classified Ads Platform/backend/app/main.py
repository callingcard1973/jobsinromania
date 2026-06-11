from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.database import engine, SessionLocal
from app.core.config import get_settings
from app.core.analytics import Analytics
from app.models import Base, seed_default_categories
from app.api.routes import (
    auth_router, ads_router, media_router, admin_router,
    users_router, categories_router, payments_router,
)
from app.middleware import AnalyticsMiddleware
import os

settings = get_settings()

Base.metadata.create_all(bind=engine)

_seed_db = SessionLocal()
try:
    seed_default_categories(_seed_db)
finally:
    _seed_db.close()

app = FastAPI(
    title="Universal Classified Ads Platform",
    description="A scalable platform for creating and managing classified advertisements",
    version="1.0.0"
)

app.add_middleware(AnalyticsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get absolute paths for static files and templates
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(backend_dir)
static_dir = os.path.join(project_root, "frontend", "static")
templates_dir = os.path.join(project_root, "frontend", "templates")

upload_dir = os.path.join(backend_dir, settings.upload_dir)
os.makedirs(upload_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# Use FastAPI's built-in Jinja2Templates
templates = Jinja2Templates(directory=templates_dir)

app.include_router(auth_router, prefix="/api")
app.include_router(ads_router, prefix="/api")
app.include_router(media_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(payments_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    Analytics.track_user_action("anonymous", "page_view", {"page": "home"})
    return templates.TemplateResponse("ads.html", {"request": request})


@app.get("/ads", response_class=HTMLResponse)
async def ads_page(request: Request):
    Analytics.track_user_action("anonymous", "page_view", {"page": "ads"})
    return templates.TemplateResponse("ads.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    Analytics.track_user_action("anonymous", "page_view", {"page": "login"})
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    Analytics.track_user_action("anonymous", "page_view", {"page": "register"})
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/create-ad", response_class=HTMLResponse)
async def create_ad_page(request: Request):
    Analytics.track_user_action("anonymous", "page_view", {"page": "create_ad"})
    return templates.TemplateResponse("create-ad.html", {"request": request})


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.on_event("shutdown")
def _flush_analytics():
    Analytics.flush()