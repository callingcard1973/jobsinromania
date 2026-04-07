"""
Master Database Integration - Compatibility Layer.

This module provides the same interface as the original master_integration.py
but now uses the separated components for better modularity and maintainability.

This ensures backward compatibility with existing code while providing
clean separation of concerns between database client and business logic.
"""

from typing import List, Dict, Any

from .master_db_client import MasterDatabaseClient, ExtractionConfig
from .employer_extractor import EmployerExtractor

# Re-export main classes for compatibility
__all__ = [
    'MasterDatabaseIntegrator',
    'ExtractionConfig',
    'extract_german_automotive_employers',
    'extract_dutch_agricultural_employers',
    'import_all_employers',
    'test_master_database'
]


class MasterDatabaseIntegrator:
    """
    Legacy compatibility wrapper for the original MasterDatabaseIntegrator class.

    This class delegates to the new modular components while maintaining
    the exact same interface for backward compatibility.
    """

    def __init__(self):
        self.extractor = EmployerExtractor()
        self.db_client = MasterDatabaseClient()
        self.config = ExtractionConfig()
        # Expose attributes for backward compatibility with tests
        self.db = self.extractor.db

    def extract_german_automotive_companies(self, limit: int = None) -> List[Dict[str, Any]]:
        """Extract German automotive companies from master database."""
        return self.extractor.extract_german_automotive_companies(limit)

    def extract_dutch_agricultural_companies(self, limit: int = None) -> List[Dict[str, Any]]:
        """Extract Dutch agricultural companies from master database."""
        return self.extractor.extract_dutch_agricultural_companies(limit)

    def import_companies_to_local_db(self, companies: List[Dict[str, Any]]):
        """Import extracted companies into local SQLite database."""
        return self.extractor.import_companies_to_local_db(companies)

    def extract_and_import_all(self) -> Dict[str, Any]:
        """Complete extraction and import process for both sectors."""
        return self.extractor.extract_and_import_all()

    def test_master_database_connection(self) -> Dict[str, Any]:
        """Test connection to master database and check available data."""
        return self.extractor.test_master_database_connection()

    # Legacy method names for exact compatibility
    def _validate_and_clean_email(self, email: str):
        """Validate and clean email address."""
        return self.extractor._validate_and_clean_email(email)

    def _generate_contact_email(self, website: str):
        """Generate likely contact email from website."""
        return self.extractor._generate_contact_email(website)

    def _format_company_size(self, employee_count: int):
        """Format employee count into size category."""
        return self.extractor._format_company_size(employee_count)

    def _extract_contact_person(self, company_data: Dict[str, Any]):
        """Extract contact person from company data."""
        return self.extractor._extract_contact_person(company_data)

    def _clean_phone(self, phone: str):
        """Clean and format phone number."""
        return self.extractor._clean_phone(phone)

    def _clean_website(self, website: str):
        """Clean and format website URL."""
        return self.extractor._clean_website(website)


# Convenience functions for easy access (maintaining exact same interface)
def extract_german_automotive_employers(limit: int = 50) -> List[Dict[str, Any]]:
    """Extract German automotive employers from master database."""
    extractor = EmployerExtractor()
    return extractor.extract_german_automotive_companies(limit)


def extract_dutch_agricultural_employers(limit: int = 30) -> List[Dict[str, Any]]:
    """Extract Dutch agricultural employers from master database."""
    extractor = EmployerExtractor()
    return extractor.extract_dutch_agricultural_companies(limit)


def import_all_employers() -> Dict[str, Any]:
    """Extract and import all European employers to local database."""
    extractor = EmployerExtractor()
    return extractor.extract_and_import_all()


def test_master_database() -> Dict[str, Any]:
    """Test master database connection and data availability."""
    extractor = EmployerExtractor()
    return extractor.test_master_database_connection()