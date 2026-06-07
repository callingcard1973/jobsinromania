#!/usr/bin/env python3
"""FastAPI application for raspibig."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from dotenv import load_dotenv

from routers import health

load_dotenv()

app = FastAPI(
    title="Raspibig API",
    description="Production API service on raspibig",
    version="1.0.0"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Raspibig FastAPI Service", "version": "1.0.0"}


@app.on_event("startup")
async def startup_event():
    """Log startup."""
    logger.info("FastAPI application starting on raspibig:8000")
    logger.info("PostgreSQL target: %s:%s/%s",
                os.getenv("DB_HOST"),
                os.getenv("DB_PORT"),
                os.getenv("DB_NAME"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", 8000)),
        workers=2,
        log_level="info"
    )
