"""
Master Database Client for PostgreSQL connectivity and query execution.

This module handles all interactions with the master PostgreSQL database on raspibig,
including connection management, query execution, and raw data retrieval.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

from ..database.connection import get_database

logger = logging.getLogger(__name__)


@dataclass
class ExtractionConfig:
    """Configuration for employer extraction."""

    # German automotive keywords
    german_automotive_keywords = [
        "BMW", "Volkswagen", "Audi", "Mercedes", "Porsche", "Auto", "Fahrzeug",
        "Automotive", "automobile", "motor vehicle", "auto parts", "car manufacturing",
        "Automobil", "Kraftfahrzeug", "Kfz", "automotive", "Autohersteller"
    ]

    # Dutch agricultural keywords
    dutch_agricultural_keywords = [
        "Farm", "Agri", "Greenhouse", "Horti", "Food", "Landbouw", "agriculture",
        "farming", "crop", "animal", "greenhouse", "food processing", "Boerderij",
        "Tuinbouw", "Veeteelt", "Glastuinbouw", "Voedsel", "Akkerbouw"
    ]

    # Volume limits (hard limits)
    german_automotive_limit = 50
    dutch_agricultural_limit = 30

    # Email validation
    valid_tlds = [
        ".com", ".de", ".nl", ".eu", ".org", ".net", ".biz", ".info", ".co.uk",
        ".fr", ".it", ".es", ".pl", ".ro", ".bg", ".hu", ".cz", ".sk"
    ]


class MasterDatabaseClient:
    """Client for master PostgreSQL database operations."""

    def __init__(self):
        self.db = get_database()
        self.config = ExtractionConfig()

    def query_german_automotive_companies(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Query German automotive companies from master database.

        Args:
            limit: Maximum number of companies to retrieve (default: 50)

        Returns:
            List of raw company data dictionaries
        """
        if limit is None:
            limit = self.config.german_automotive_limit

        logger.info(f"Querying German automotive companies (limit: {limit})")

        # Build keyword query for automotive sector
        automotive_conditions = []
        for keyword in self.config.german_automotive_keywords:
            automotive_conditions.append(f"LOWER(name) LIKE LOWER('%{keyword}%')")
            automotive_conditions.append(f"LOWER(activity_description) LIKE LOWER('%{keyword}%')")
            automotive_conditions.append(f"LOWER(sector) LIKE LOWER('%{keyword}%')")

        automotive_query = " OR ".join(automotive_conditions)

        query = f"""
        SELECT DISTINCT
            name,
            country_code,
            address,
            city,
            postal_code,
            phone,
            email,
            website,
            activity_description as sector_description,
            sector,
            employee_count,
            registration_number,
            vat_number
        FROM companies
        WHERE country_code = 'DE'
          AND ({automotive_query})
          AND name IS NOT NULL
          AND LENGTH(TRIM(name)) > 0
        ORDER BY
            CASE WHEN email IS NOT NULL AND email != '' THEN 0 ELSE 1 END,
            employee_count DESC NULLS LAST,
            name
        LIMIT {limit}
        """

        try:
            with self.db.get_session(use_postgres=True) as session:
                result = session.execute(sa.text(query))
                companies = []

                for row in result:
                    company_data = {
                        'name': row.name,
                        'country_code': row.country_code,
                        'address': row.address,
                        'city': row.city,
                        'postal_code': row.postal_code,
                        'phone': row.phone,
                        'email': row.email,
                        'website': row.website,
                        'sector_description': row.sector_description,
                        'sector': row.sector,
                        'employee_count': row.employee_count,
                        'registration_number': row.registration_number,
                        'vat_number': row.vat_number
                    }
                    companies.append(company_data)

                logger.info(f"Successfully queried {len(companies)} German automotive companies")
                return companies

        except Exception as e:
            logger.error(f"Failed to query German automotive companies: {e}")
            return []

    def query_dutch_agricultural_companies(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Query Dutch agricultural companies from master database.

        Args:
            limit: Maximum number of companies to retrieve (default: 30)

        Returns:
            List of raw company data dictionaries
        """
        if limit is None:
            limit = self.config.dutch_agricultural_limit

        logger.info(f"Querying Dutch agricultural companies (limit: {limit})")

        # Build keyword query for agricultural sector
        agricultural_conditions = []
        for keyword in self.config.dutch_agricultural_keywords:
            agricultural_conditions.append(f"LOWER(name) LIKE LOWER('%{keyword}%')")
            agricultural_conditions.append(f"LOWER(activity_description) LIKE LOWER('%{keyword}%')")
            agricultural_conditions.append(f"LOWER(sector) LIKE LOWER('%{keyword}%')")

        agricultural_query = " OR ".join(agricultural_conditions)

        query = f"""
        SELECT DISTINCT
            name,
            country_code,
            address,
            city,
            postal_code,
            phone,
            email,
            website,
            activity_description as sector_description,
            sector,
            employee_count,
            registration_number,
            vat_number
        FROM companies
        WHERE country_code = 'NL'
          AND ({agricultural_query})
          AND name IS NOT NULL
          AND LENGTH(TRIM(name)) > 0
        ORDER BY
            CASE WHEN email IS NOT NULL AND email != '' THEN 0 ELSE 1 END,
            employee_count DESC NULLS LAST,
            name
        LIMIT {limit}
        """

        try:
            with self.db.get_session(use_postgres=True) as session:
                result = session.execute(sa.text(query))
                companies = []

                for row in result:
                    company_data = {
                        'name': row.name,
                        'country_code': row.country_code,
                        'address': row.address,
                        'city': row.city,
                        'postal_code': row.postal_code,
                        'phone': row.phone,
                        'email': row.email,
                        'website': row.website,
                        'sector_description': row.sector_description,
                        'sector': row.sector,
                        'employee_count': row.employee_count,
                        'registration_number': row.registration_number,
                        'vat_number': row.vat_number
                    }
                    companies.append(company_data)

                logger.info(f"Successfully queried {len(companies)} Dutch agricultural companies")
                return companies

        except Exception as e:
            logger.error(f"Failed to query Dutch agricultural companies: {e}")
            return []

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to master database and check available data.

        Returns:
            Dictionary with connection status and sample data info
        """
        test_results = {
            'connection': False,
            'tables_accessible': False,
            'sample_data': {},
            'error': None
        }

        try:
            with self.db.get_session(use_postgres=True) as session:
                # Test basic connection
                session.execute(sa.text("SELECT 1"))
                test_results['connection'] = True

                # Test table access
                result = session.execute(sa.text("SELECT COUNT(*) FROM companies WHERE country_code IN ('DE', 'NL')"))
                total_companies = result.scalar()
                test_results['sample_data']['total_de_nl_companies'] = total_companies
                test_results['tables_accessible'] = True

                # Test German automotive sample
                german_query = """
                SELECT COUNT(*) FROM companies
                WHERE country_code = 'DE'
                AND (LOWER(name) LIKE '%auto%' OR LOWER(name) LIKE '%bmw%' OR LOWER(name) LIKE '%volkswagen%')
                """
                result = session.execute(sa.text(german_query))
                test_results['sample_data']['german_automotive_sample'] = result.scalar()

                # Test Dutch agricultural sample
                dutch_query = """
                SELECT COUNT(*) FROM companies
                WHERE country_code = 'NL'
                AND (LOWER(name) LIKE '%farm%' OR LOWER(name) LIKE '%agri%' OR LOWER(name) LIKE '%food%')
                """
                result = session.execute(sa.text(dutch_query))
                test_results['sample_data']['dutch_agricultural_sample'] = result.scalar()

                logger.info(f"Master database connection test successful: {test_results}")

        except Exception as e:
            test_results['error'] = str(e)
            logger.error(f"Master database connection test failed: {e}")

        return test_results