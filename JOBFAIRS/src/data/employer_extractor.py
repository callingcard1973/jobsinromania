"""
Employer Extractor for data validation, cleaning, and import to local database.

This module handles business logic for extracting employer data from the master database,
performing validation and cleaning, and importing to the local SQLite database.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from .master_db_client import MasterDatabaseClient
from ..database.connection import get_database
from ..database.models import Employer, EmployerStatus

logger = logging.getLogger(__name__)


class EmployerExtractor:
    """Business logic for employer data extraction and validation."""

    def __init__(self):
        self.db_client = MasterDatabaseClient()
        self.db = get_database()

    def extract_german_automotive_companies(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Extract German automotive companies from master database.

        Args:
            limit: Maximum number of companies to extract (default: 50)

        Returns:
            List of processed company data dictionaries
        """
        raw_companies = self.db_client.query_german_automotive_companies(limit)

        processed_companies = []
        for company_data in raw_companies:
            processed_company = {
                'name': company_data['name'],
                'country': company_data['country_code'],
                'address': company_data['address'],
                'city': company_data['city'],
                'postal_code': company_data['postal_code'],
                'phone': company_data['phone'],
                'email': company_data['email'],
                'website': company_data['website'],
                'sector': 'Automotive',
                'sector_description': company_data['sector_description'],
                'original_sector': company_data['sector'],
                'company_size': self._format_company_size(company_data['employee_count']),
                'registration_number': company_data['registration_number'],
                'vat_number': company_data['vat_number'],
                'source_database': 'germany_register',
                'extraction_date': datetime.utcnow()
            }
            processed_companies.append(processed_company)

        return processed_companies

    def extract_dutch_agricultural_companies(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Extract Dutch agricultural companies from master database.

        Args:
            limit: Maximum number of companies to extract (default: 30)

        Returns:
            List of processed company data dictionaries
        """
        raw_companies = self.db_client.query_dutch_agricultural_companies(limit)

        processed_companies = []
        for company_data in raw_companies:
            processed_company = {
                'name': company_data['name'],
                'country': company_data['country_code'],
                'address': company_data['address'],
                'city': company_data['city'],
                'postal_code': company_data['postal_code'],
                'phone': company_data['phone'],
                'email': company_data['email'],
                'website': company_data['website'],
                'sector': 'Agriculture',
                'sector_description': company_data['sector_description'],
                'original_sector': company_data['sector'],
                'company_size': self._format_company_size(company_data['employee_count']),
                'registration_number': company_data['registration_number'],
                'vat_number': company_data['vat_number'],
                'source_database': 'netherlands_register',
                'extraction_date': datetime.utcnow()
            }
            processed_companies.append(processed_company)

        return processed_companies

    def import_companies_to_local_db(self, companies: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
        """
        Import extracted companies into local SQLite database.

        Args:
            companies: List of company data dictionaries

        Returns:
            Tuple of (successful_imports, failed_imports, error_messages)
        """
        successful_imports = 0
        failed_imports = 0
        error_messages = []

        logger.info(f"Importing {len(companies)} companies to local database")

        try:
            with self.db.get_session() as session:
                for company_data in companies:
                    try:
                        # Validate and clean email
                        email = self._validate_and_clean_email(company_data.get('email'))
                        if not email:
                            # Try to generate contact email from website
                            email = self._generate_contact_email(company_data.get('website'))

                        if not email:
                            error_messages.append(f"No valid email for {company_data['name']}")
                            failed_imports += 1
                            continue

                        # Check if employer already exists
                        existing = session.query(Employer).filter(
                            Employer.contact_email == email
                        ).first()

                        if existing:
                            logger.debug(f"Employer already exists: {email}")
                            continue

                        # Create new employer
                        employer_data = {
                            'name': company_data['name'][:255],  # Ensure length limit
                            'country': company_data['country'],
                            'sector': company_data['sector'],
                            'contact_email': email,
                            'contact_person': self._extract_contact_person(company_data),
                            'phone': self._clean_phone(company_data.get('phone')),
                            'website': self._clean_website(company_data.get('website')),
                            'address': company_data.get('address'),
                            'city': company_data.get('city'),
                            'postal_code': company_data.get('postal_code'),
                            'company_size': company_data.get('company_size'),
                            'registration_number': company_data.get('registration_number'),
                            'vat_number': company_data.get('vat_number'),
                            'status': EmployerStatus.PROSPECTIVE,
                            'source_database': company_data.get('source_database'),
                            'notes': f"Extracted on {company_data.get('extraction_date', datetime.utcnow())}\n"
                                   f"Original sector: {company_data.get('original_sector', 'Unknown')}\n"
                                   f"Sector description: {company_data.get('sector_description', 'N/A')}"
                        }

                        employer = Employer(**employer_data)
                        session.add(employer)
                        session.flush()  # Get ID without full commit

                        successful_imports += 1
                        logger.debug(f"Successfully imported: {employer.name}")

                    except Exception as e:
                        error_message = f"Failed to import {company_data.get('name', 'Unknown')}: {str(e)}"
                        error_messages.append(error_message)
                        logger.error(error_message)
                        failed_imports += 1
                        continue

                # Commit all successful imports
                session.commit()

        except Exception as e:
            logger.error(f"Database session error during import: {e}")
            error_messages.append(f"Database error: {str(e)}")
            return successful_imports, failed_imports, error_messages

        logger.info(f"Import completed: {successful_imports} successful, {failed_imports} failed")
        return successful_imports, failed_imports, error_messages

    def extract_and_import_all(self) -> Dict[str, Any]:
        """
        Complete extraction and import process for both sectors.

        Returns:
            Dictionary with operation results and statistics
        """
        results = {
            'start_time': datetime.utcnow(),
            'german_automotive': {'extracted': 0, 'imported': 0, 'failed': 0},
            'dutch_agricultural': {'extracted': 0, 'imported': 0, 'failed': 0},
            'total_extracted': 0,
            'total_imported': 0,
            'total_failed': 0,
            'errors': [],
            'success': False
        }

        try:
            # Extract German automotive companies
            logger.info("Starting German automotive company extraction")
            german_companies = self.extract_german_automotive_companies()
            results['german_automotive']['extracted'] = len(german_companies)
            results['total_extracted'] += len(german_companies)

            if german_companies:
                imported, failed, errors = self.import_companies_to_local_db(german_companies)
                results['german_automotive']['imported'] = imported
                results['german_automotive']['failed'] = failed
                results['total_imported'] += imported
                results['total_failed'] += failed
                results['errors'].extend(errors)

            # Extract Dutch agricultural companies
            logger.info("Starting Dutch agricultural company extraction")
            dutch_companies = self.extract_dutch_agricultural_companies()
            results['dutch_agricultural']['extracted'] = len(dutch_companies)
            results['total_extracted'] += len(dutch_companies)

            if dutch_companies:
                imported, failed, errors = self.import_companies_to_local_db(dutch_companies)
                results['dutch_agricultural']['imported'] = imported
                results['dutch_agricultural']['failed'] = failed
                results['total_imported'] += imported
                results['total_failed'] += failed
                results['errors'].extend(errors)

            results['success'] = results['total_imported'] > 0
            results['end_time'] = datetime.utcnow()
            results['duration'] = (results['end_time'] - results['start_time']).total_seconds()

            logger.info(f"Extraction completed: {results['total_extracted']} extracted, "
                       f"{results['total_imported']} imported, {results['total_failed']} failed")

        except Exception as e:
            logger.error(f"Critical error during extraction and import: {e}")
            results['errors'].append(f"Critical error: {str(e)}")
            results['success'] = False

        return results

    def test_master_database_connection(self) -> Dict[str, Any]:
        """
        Test connection to master database and check available data.

        Returns:
            Dictionary with connection status and sample data info
        """
        return self.db_client.test_connection()

    def _validate_and_clean_email(self, email: str) -> Optional[str]:
        """
        Validate and clean email address.

        Args:
            email: Raw email address

        Returns:
            Cleaned email or None if invalid
        """
        if not email or not isinstance(email, str):
            return None

        # Basic cleanup
        email = email.strip().lower()
        if not email:
            return None

        # Check basic format
        if '@' not in email:
            return None

        try:
            local, domain = email.rsplit('@', 1)

            # Check for valid TLD
            domain_valid = any(domain.endswith(tld) for tld in self.db_client.config.valid_tlds)
            if not domain_valid:
                return None

            # Check local part
            if not local or len(local) < 1:
                return None

            return email

        except ValueError:
            return None

    def _generate_contact_email(self, website: str) -> Optional[str]:
        """
        Generate likely contact email from website.

        Args:
            website: Company website URL

        Returns:
            Generated email or None
        """
        if not website:
            return None

        try:
            # Extract domain from website
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', website)
            if not domain_match:
                return None

            domain = domain_match.group(1)

            # Generate common contact emails
            contact_prefixes = ['info', 'contact', 'hr', 'jobs', 'careers']

            for prefix in contact_prefixes:
                email = f"{prefix}@{domain}"
                if self._validate_and_clean_email(email):
                    return email

            return None

        except Exception:
            return None

    def _format_company_size(self, employee_count: int) -> str:
        """
        Format employee count into size category.

        Args:
            employee_count: Number of employees

        Returns:
            Size category string
        """
        if not employee_count or employee_count <= 0:
            return "Unknown"
        elif employee_count <= 10:
            return "1-10"
        elif employee_count <= 50:
            return "11-50"
        elif employee_count <= 100:
            return "51-100"
        elif employee_count <= 250:
            return "101-250"
        elif employee_count <= 500:
            return "251-500"
        elif employee_count <= 1000:
            return "501-1000"
        else:
            return "1000+"

    def _extract_contact_person(self, company_data: Dict[str, Any]) -> Optional[str]:
        """
        Extract contact person from company data.

        Args:
            company_data: Company information dictionary

        Returns:
            Contact person name or None
        """
        # This would be enhanced based on actual master DB schema
        # For now, return None to let it be filled manually
        return None

    def _clean_phone(self, phone: str) -> Optional[str]:
        """
        Clean and format phone number.

        Args:
            phone: Raw phone number

        Returns:
            Cleaned phone number or None
        """
        if not phone:
            return None

        # Remove common separators and spaces
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)

        # Keep only digits and plus sign at start
        if cleaned.startswith('+'):
            # Keep the plus sign and following digits
            match = re.match(r'^(\+\d+)$', cleaned)
            if match:
                cleaned = match.group(1)
            else:
                return None
        else:
            # Only digits
            if not re.match(r'^\d+$', cleaned):
                return None

        if len(cleaned) < 7:  # Minimum reasonable phone length
            return None

        return cleaned[:50]  # Respect database column limit

    def _clean_website(self, website: str) -> Optional[str]:
        """
        Clean and format website URL.

        Args:
            website: Raw website URL

        Returns:
            Cleaned URL or None
        """
        if not website:
            return None

        website = website.strip()

        # Add protocol if missing
        if not website.startswith(('http://', 'https://')):
            website = f"https://{website}"

        # Basic validation
        if not re.match(r'https?://[^\s/$.?#].[^\s]*', website):
            return None

        return website[:255]  # Respect database column limit