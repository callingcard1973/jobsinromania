#!/usr/bin/env python3
"""FastAPI application for raspibig."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv

from routers import health

# Constants
__version__ = "1.0.0"
SERVICE_NAME = "raspibig-api"

# Config from environment
load_dotenv()
APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
try:
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
except ValueError:
    APP_PORT = 8000

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
try:
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
except ValueError:
    DB_PORT = 5432

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("FastAPI starting on %s:%s", APP_HOST, APP_PORT)
    logger.info("PostgreSQL: %s:%s/%s", DB_HOST, DB_PORT, os.getenv("DB_NAME", "interjob_master"))
    yield
    logger.info("FastAPI shutdown")


app = FastAPI(
    title="Raspibig API",
    description="Production API service on raspibig",
    version=__version__,
    lifespan=lifespan
)

# CORS: explicit origins only, no wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000", "https://api.interjob.ro"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Raspibig FastAPI Service", "version": __version__}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=APP_HOST,
        port=APP_PORT,
        workers=2,
        log_level="info"
    )
