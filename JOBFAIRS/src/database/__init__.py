"""
Database package for European Employer ANOFM Job Fair Integration System.

This package provides:
- SQLite database models for local data storage
- Connection management for both local and master databases
- CRUD operations for all entities
- GDPR-compliant data retention and management
- Database initialization and migration support

Key components:
- models.py: Database models and CRUD operations
- connection.py: Database connection management
"""

from .connection import Database, get_database, init_database
from .models import (
    Employer,
    ANOFMEvent,
    Worker,
    WorkerEmployerMatch,
    LegalCompliance,
    Communication,
    FinancialTracking
)

__all__ = [
    "Database",
    "get_database",
    "init_database",
    "Employer",
    "ANOFMEvent",
    "Worker",
    "WorkerEmployerMatch",
    "LegalCompliance",
    "Communication",
    "FinancialTracking"
]