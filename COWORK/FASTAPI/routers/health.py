#!/usr/bin/env python3
"""Health check and status endpoints."""

from fastapi import APIRouter, status

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "fastapi-raspibig",
        "version": "1.0.0"
    }


@router.get("/status")
def service_status():
    """Service status and info."""
    return {
        "service": "raspibig-api",
        "version": "1.0.0",
        "status": "running"
    }
