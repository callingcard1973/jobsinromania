#!/usr/bin/env python3
"""Health check and status endpoints."""

from fastapi import APIRouter, status

__version__ = "1.0.0"
SERVICE_NAME = "fastapi-raspibig"

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Check service availability."""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": __version__
    }


@router.get("/status")
def service_status():
    """Current service state."""
    return {
        "service": SERVICE_NAME,
        "version": __version__,
        "status": "running"
    }
