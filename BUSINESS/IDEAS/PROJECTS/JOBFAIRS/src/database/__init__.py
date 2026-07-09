"""
Database package for European Employer ANOFM Job Fair Integration System.

This package provides:
- SQLite database models for local data storage
- Connection management for both local and master databases
- CRUD operations for all entities
- GDPR-compliant data retention and management
- Database initialization and migration support
- Master database integration for European employer extraction

Key components:
- models.py: Database models and CRUD operations
- connection.py: Database connection management
- master_integration.py: Master database integration for employer extraction
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
from ..data.master_integration import (
    MasterDatabaseIntegrator,
    extract_german_automotive_employers,
    extract_dutch_agricultural_employers,
    import_all_employers,
    test_master_database
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
    "FinancialTracking",
    "MasterDatabaseIntegrator",
    "extract_german_automotive_employers",
    "extract_dutch_agricultural_employers",
    "import_all_employers",
    "test_master_database"
]