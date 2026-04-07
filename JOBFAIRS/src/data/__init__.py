"""
Data package for master database integration.

This package provides modular components for:
- PostgreSQL master database connectivity
- Employer data extraction and validation
- Integration with local database models
"""

from .master_db_client import MasterDatabaseClient
from .employer_extractor import EmployerExtractor

__all__ = [
    'MasterDatabaseClient',
    'EmployerExtractor'
]