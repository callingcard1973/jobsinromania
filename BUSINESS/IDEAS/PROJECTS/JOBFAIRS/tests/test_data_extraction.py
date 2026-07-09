"""
Test suite for Master Database Integration functionality.

Tests cover:
- Connection testing with mock data
- German automotive company extraction
- Dutch agricultural company extraction
- Email validation and generation
- Field mapping and data cleaning
- Import process with error handling
- Volume limits enforcement
"""

import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.orm import Session

# Test imports
from src.data.master_integration import (
    MasterDatabaseIntegrator,
    ExtractionConfig,
    extract_german_automotive_employers,
    extract_dutch_agricultural_employers,
    import_all_employers,
    test_master_database
)
from src.database.models import Employer, EmployerStatus
from src.database.connection import get_database
from config import get_config


class TestExtractionConfig:
    """Test extraction configuration."""

    def test_extraction_config_initialization(self):
        """Test that extraction config initializes with correct values."""
        config = ExtractionConfig()

        # Test German automotive keywords
        assert "BMW" in config.german_automotive_keywords
        assert "Volkswagen" in config.german_automotive_keywords
        assert "automotive" in config.german_automotive_keywords

        # Test Dutch agricultural keywords
        assert "Farm" in config.dutch_agricultural_keywords
        assert "Landbouw" in config.dutch_agricultural_keywords
        assert "agriculture" in config.dutch_agricultural_keywords

        # Test limits
        assert config.german_automotive_limit == 50
        assert config.dutch_agricultural_limit == 30

        # Test valid TLDs
        assert ".de" in config.valid_tlds
        assert ".nl" in config.valid_tlds
        assert ".com" in config.valid_tlds


class TestMasterDatabaseIntegrator:
    """Test the master database integrator class."""

    @pytest.fixture
    def integrator(self):
        """Create integrator instance for testing."""
        return MasterDatabaseIntegrator()

    @pytest.fixture
    def mock_companies_data(self):
        """Mock companies data for testing."""
        return [
            {
                'name': 'BMW Manufacturing GmbH',
                'country_code': 'DE',
                'address': 'Petuelring 130',
                'city': 'München',
                'postal_code': '80809',
                'phone': '+49 89 382 0',
                'email': 'info@bmw.de',
                'website': 'https://www.bmw.de',
                'activity_description': 'Automotive manufacturing',
                'sector': 'Manufacturing',
                'employee_count': 15000,
                'registration_number': 'HRB 42243',
                'vat_number': 'DE129273398'
            },
            {
                'name': 'Nederlandse Landbouw BV',
                'country_code': 'NL',
                'address': 'Hoofdstraat 123',
                'city': 'Amsterdam',
                'postal_code': '1000AB',
                'phone': '+31 20 123 4567',
                'email': 'contact@landbouw.nl',
                'website': 'https://www.landbouw.nl',
                'activity_description': 'Agricultural services',
                'sector': 'Agriculture',
                'employee_count': 250,
                'registration_number': '12345678',
                'vat_number': 'NL123456789B01'
            }
        ]

    def test_integrator_initialization(self, integrator):
        """Test that integrator initializes correctly."""
        assert integrator.db is not None
        assert integrator.config is not None
        assert isinstance(integrator.config, ExtractionConfig)

    def test_email_validation(self, integrator):
        """Test email validation and cleaning."""
        # Valid emails
        assert integrator._validate_and_clean_email("test@bmw.de") == "test@bmw.de"
        assert integrator._validate_and_clean_email("  INFO@Company.COM  ") == "info@company.com"
        assert integrator._validate_and_clean_email("hr@landbouw.nl") == "hr@landbouw.nl"

        # Invalid emails
        assert integrator._validate_and_clean_email("") is None
        assert integrator._validate_and_clean_email(None) is None
        assert integrator._validate_and_clean_email("notanemail") is None
        assert integrator._validate_and_clean_email("test@invalid.xyz") is None
        assert integrator._validate_and_clean_email("@domain.com") is None

    def test_contact_email_generation(self, integrator):
        """Test contact email generation from website."""
        # Valid websites
        assert integrator._generate_contact_email("https://www.bmw.de") == "info@bmw.de"
        assert integrator._generate_contact_email("http://company.nl") == "info@company.nl"
        assert integrator._generate_contact_email("https://example.com") == "info@example.com"

        # Invalid websites
        assert integrator._generate_contact_email("") is None
        assert integrator._generate_contact_email(None) is None
        assert integrator._generate_contact_email("not-a-website") is None

    def test_company_size_formatting(self, integrator):
        """Test company size formatting."""
        assert integrator._format_company_size(None) == "Unknown"
        assert integrator._format_company_size(0) == "Unknown"
        assert integrator._format_company_size(5) == "1-10"
        assert integrator._format_company_size(25) == "11-50"
        assert integrator._format_company_size(75) == "51-100"
        assert integrator._format_company_size(150) == "101-250"
        assert integrator._format_company_size(300) == "251-500"
        assert integrator._format_company_size(750) == "501-1000"
        assert integrator._format_company_size(2000) == "1000+"

    def test_phone_cleaning(self, integrator):
        """Test phone number cleaning."""
        assert integrator._clean_phone("+49 89 382 0") == "+49893820"
        assert integrator._clean_phone("(030) 123-456") == "030123456"
        assert integrator._clean_phone("  +31-20-123-4567  ") == "+31201234567"

        # Invalid phones
        assert integrator._clean_phone("") is None
        assert integrator._clean_phone(None) is None
        assert integrator._clean_phone("123") is None  # Too short

    def test_website_cleaning(self, integrator):
        """Test website URL cleaning."""
        assert integrator._clean_website("bmw.de") == "https://bmw.de"
        assert integrator._clean_website("http://example.com") == "http://example.com"
        assert integrator._clean_website("  https://company.nl  ") == "https://company.nl"

        # Invalid websites
        assert integrator._clean_website("") is None
        assert integrator._clean_website(None) is None

    @patch('src.data.master_db_client.get_database')
    def test_extract_german_automotive_companies(self, mock_get_db, integrator, mock_companies_data):
        """Test German automotive companies extraction."""
        # Mock database session and results
        mock_session = MagicMock()
        mock_result = MagicMock()

        # Configure mock to return BMW data
        bmw_row = MagicMock()
        bmw_row.name = mock_companies_data[0]['name']
        bmw_row.country_code = mock_companies_data[0]['country_code']
        bmw_row.address = mock_companies_data[0]['address']
        bmw_row.city = mock_companies_data[0]['city']
        bmw_row.postal_code = mock_companies_data[0]['postal_code']
        bmw_row.phone = mock_companies_data[0]['phone']
        bmw_row.email = mock_companies_data[0]['email']
        bmw_row.website = mock_companies_data[0]['website']
        bmw_row.sector_description = mock_companies_data[0]['activity_description']
        bmw_row.sector = mock_companies_data[0]['sector']
        bmw_row.employee_count = mock_companies_data[0]['employee_count']
        bmw_row.registration_number = mock_companies_data[0]['registration_number']
        bmw_row.vat_number = mock_companies_data[0]['vat_number']

        mock_result.__iter__.return_value = iter([bmw_row])
        mock_session.execute.return_value = mock_result

        # Mock database context manager
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_db.get_session.return_value.__exit__.return_value = None
        mock_get_db.return_value = mock_db

        # Test extraction
        companies = integrator.extract_german_automotive_companies()

        # Verify results
        assert len(companies) == 1
        company = companies[0]
        assert company['name'] == 'BMW Manufacturing GmbH'
        assert company['country'] == 'DE'
        assert company['sector'] == 'Automotive'
        assert company['email'] == 'info@bmw.de'
        assert company['source_database'] == 'germany_register'

    @patch('src.data.master_db_client.get_database')
    def test_extract_dutch_agricultural_companies(self, mock_get_db, integrator, mock_companies_data):
        """Test Dutch agricultural companies extraction."""
        # Mock database session and results
        mock_session = MagicMock()
        mock_result = MagicMock()

        # Configure mock to return Landbouw data
        landbouw_row = MagicMock()
        landbouw_row.name = mock_companies_data[1]['name']
        landbouw_row.country_code = mock_companies_data[1]['country_code']
        landbouw_row.address = mock_companies_data[1]['address']
        landbouw_row.city = mock_companies_data[1]['city']
        landbouw_row.postal_code = mock_companies_data[1]['postal_code']
        landbouw_row.phone = mock_companies_data[1]['phone']
        landbouw_row.email = mock_companies_data[1]['email']
        landbouw_row.website = mock_companies_data[1]['website']
        landbouw_row.sector_description = mock_companies_data[1]['activity_description']
        landbouw_row.sector = mock_companies_data[1]['sector']
        landbouw_row.employee_count = mock_companies_data[1]['employee_count']
        landbouw_row.registration_number = mock_companies_data[1]['registration_number']
        landbouw_row.vat_number = mock_companies_data[1]['vat_number']

        mock_result.__iter__.return_value = iter([landbouw_row])
        mock_session.execute.return_value = mock_result

        # Mock database context manager
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_db.get_session.return_value.__exit__.return_value = None
        mock_get_db.return_value = mock_db

        # Test extraction
        companies = integrator.extract_dutch_agricultural_companies()

        # Verify results
        assert len(companies) == 1
        company = companies[0]
        assert company['name'] == 'Nederlandse Landbouw BV'
        assert company['country'] == 'NL'
        assert company['sector'] == 'Agriculture'
        assert company['email'] == 'contact@landbouw.nl'
        assert company['source_database'] == 'netherlands_register'

    @patch('src.data.master_db_client.get_database')
    def test_import_companies_to_local_db(self, mock_get_db, integrator, mock_companies_data):
        """Test importing companies to local database."""
        # Mock database session
        mock_session = MagicMock()

        # Mock query to return no existing employers
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock database context manager
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_db.get_session.return_value.__exit__.return_value = None
        mock_get_db.return_value = mock_db

        # Transform mock data to expected format
        companies = []
        for company_data in mock_companies_data:
            companies.append({
                'name': company_data['name'],
                'country': company_data['country_code'],
                'email': company_data['email'],
                'website': company_data['website'],
                'address': company_data['address'],
                'city': company_data['city'],
                'postal_code': company_data['postal_code'],
                'phone': company_data['phone'],
                'sector': 'Automotive' if 'BMW' in company_data['name'] else 'Agriculture',
                'company_size': integrator._format_company_size(company_data['employee_count']),
                'registration_number': company_data['registration_number'],
                'vat_number': company_data['vat_number'],
                'source_database': 'test_database',
                'extraction_date': datetime.utcnow()
            })

        # Test import
        successful, failed, errors = integrator.import_companies_to_local_db(companies)

        # Verify results
        assert successful == 2
        assert failed == 0
        assert len(errors) == 0

        # Verify database operations
        assert mock_session.add.call_count == 2
        assert mock_session.commit.called

    @patch('src.data.master_db_client.get_database')
    def test_import_companies_with_errors(self, mock_get_db, integrator):
        """Test importing companies with validation errors."""
        # Mock database session
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock database context manager
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_db.get_session.return_value.__exit__.return_value = None
        mock_get_db.return_value = mock_db

        # Companies with invalid email
        companies_with_errors = [
            {
                'name': 'Invalid Email Company',
                'country': 'DE',
                'email': 'invalid-email',  # Invalid email
                'sector': 'Automotive',
                'extraction_date': datetime.utcnow()
            },
            {
                'name': 'No Email Company',
                'country': 'NL',
                'email': None,  # No email
                'website': None,  # No website to generate from
                'sector': 'Agriculture',
                'extraction_date': datetime.utcnow()
            }
        ]

        # Test import
        successful, failed, errors = integrator.import_companies_to_local_db(companies_with_errors)

        # Verify results
        assert successful == 0
        assert failed == 2
        assert len(errors) == 2

        # Verify no database operations occurred for invalid companies
        assert mock_session.add.call_count == 0

    @patch('src.data.master_db_client.get_database')
    def test_test_master_database_connection(self, mock_get_db, integrator):
        """Test master database connection testing."""
        # Mock successful database session
        mock_session = MagicMock()
        mock_result = MagicMock()

        # Mock query results
        mock_result.scalar.side_effect = [1000, 50, 30]  # Total, German, Dutch
        mock_session.execute.return_value = mock_result

        # Mock database context manager
        mock_db = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        mock_db.get_session.return_value.__exit__.return_value = None
        mock_get_db.return_value = mock_db

        # Test connection
        results = integrator.test_master_database_connection()

        # Verify results
        assert results['connection'] is True
        assert results['tables_accessible'] is True
        assert results['sample_data']['total_de_nl_companies'] == 1000
        assert results['sample_data']['german_automotive_sample'] == 50
        assert results['sample_data']['dutch_agricultural_sample'] == 30
        assert results['error'] is None

    @patch('src.data.master_db_client.get_database')
    def test_test_master_database_connection_failure(self, mock_get_db, integrator):
        """Test master database connection testing with failure."""
        # Mock database error
        mock_db = MagicMock()
        mock_db.get_session.side_effect = Exception("Connection failed")
        mock_get_db.return_value = mock_db

        # Test connection
        results = integrator.test_master_database_connection()

        # Verify results
        assert results['connection'] is False
        assert results['tables_accessible'] is False
        assert 'Connection failed' in results['error']

    @patch('src.data.master_integration.MasterDatabaseIntegrator.extract_german_automotive_companies')
    @patch('src.data.master_integration.MasterDatabaseIntegrator.extract_dutch_agricultural_companies')
    @patch('src.data.master_integration.MasterDatabaseIntegrator.import_companies_to_local_db')
    def test_extract_and_import_all(self, mock_import, mock_dutch, mock_german, integrator):
        """Test complete extraction and import process."""
        # Mock extraction methods
        mock_german_companies = [{'name': 'BMW', 'country': 'DE'}]
        mock_dutch_companies = [{'name': 'Farm BV', 'country': 'NL'}]

        mock_german.return_value = mock_german_companies
        mock_dutch.return_value = mock_dutch_companies

        # Mock import results
        mock_import.side_effect = [
            (1, 0, []),  # German import: 1 success, 0 failed, no errors
            (1, 0, [])   # Dutch import: 1 success, 0 failed, no errors
        ]

        # Test complete process
        results = integrator.extract_and_import_all()

        # Verify results
        assert results['success'] is True
        assert results['total_extracted'] == 2
        assert results['total_imported'] == 2
        assert results['total_failed'] == 0
        assert results['german_automotive']['extracted'] == 1
        assert results['german_automotive']['imported'] == 1
        assert results['dutch_agricultural']['extracted'] == 1
        assert results['dutch_agricultural']['imported'] == 1

        # Verify method calls
        mock_german.assert_called_once()
        mock_dutch.assert_called_once()
        assert mock_import.call_count == 2


class TestConvenienceFunctions:
    """Test convenience functions."""

    @patch('src.data.master_integration.EmployerExtractor')
    def test_extract_german_automotive_employers(self, mock_extractor_class):
        """Test German automotive extraction convenience function."""
        mock_extractor = MagicMock()
        mock_extractor.extract_german_automotive_companies.return_value = [{'test': 'data'}]
        mock_extractor_class.return_value = mock_extractor

        result = extract_german_automotive_employers(limit=25)

        mock_extractor.extract_german_automotive_companies.assert_called_once_with(25)
        assert result == [{'test': 'data'}]

    @patch('src.data.master_integration.EmployerExtractor')
    def test_extract_dutch_agricultural_employers(self, mock_extractor_class):
        """Test Dutch agricultural extraction convenience function."""
        mock_extractor = MagicMock()
        mock_extractor.extract_dutch_agricultural_companies.return_value = [{'test': 'data'}]
        mock_extractor_class.return_value = mock_extractor

        result = extract_dutch_agricultural_employers(limit=15)

        mock_extractor.extract_dutch_agricultural_companies.assert_called_once_with(15)
        assert result == [{'test': 'data'}]

    @patch('src.data.master_integration.EmployerExtractor')
    def test_import_all_employers(self, mock_extractor_class):
        """Test import all employers convenience function."""
        mock_extractor = MagicMock()
        mock_extractor.extract_and_import_all.return_value = {'success': True}
        mock_extractor_class.return_value = mock_extractor

        result = import_all_employers()

        mock_extractor.extract_and_import_all.assert_called_once()
        assert result == {'success': True}

    @patch('src.data.master_integration.EmployerExtractor')
    def test_test_master_database(self, mock_extractor_class):
        """Test master database testing convenience function."""
        mock_extractor = MagicMock()
        mock_extractor.test_master_database_connection.return_value = {'connection': True}
        mock_extractor_class.return_value = mock_extractor

        result = test_master_database()

        mock_extractor.test_master_database_connection.assert_called_once()
        assert result == {'connection': True}


# Integration test with real database models (requires proper setup)
@pytest.mark.integration
class TestRealDatabaseIntegration:
    """Integration tests with real database models."""

    @pytest.fixture
    def temp_db_config(self):
        """Create temporary database configuration for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            tmp_path = tmp.name

        # Override config to use temporary database
        original_config = get_config()
        original_config.database.sqlite_path = tmp_path

        yield tmp_path

        # Cleanup
        Path(tmp_path).unlink(missing_ok=True)

    def test_real_import_with_models(self, temp_db_config):
        """Test import process with real database models."""
        from src.database import init_database, get_database

        # Initialize temporary database
        success = init_database()
        assert success

        # Create integrator and test import
        integrator = MasterDatabaseIntegrator()

        test_companies = [
            {
                'name': 'Test Automotive GmbH',
                'country': 'DE',
                'email': 'test@automotive.de',
                'sector': 'Automotive',
                'website': 'https://automotive.de',
                'address': 'Test Street 123',
                'city': 'Munich',
                'postal_code': '80809',
                'phone': '+49891234567',
                'company_size': '51-100',
                'registration_number': 'HRB12345',
                'vat_number': 'DE123456789',
                'source_database': 'test_database',
                'extraction_date': datetime.utcnow()
            }
        ]

        # Test import
        successful, failed, errors = integrator.import_companies_to_local_db(test_companies)

        # Verify import
        assert successful == 1
        assert failed == 0
        assert len(errors) == 0

        # Verify database content
        db = get_database()
        with db.get_session() as session:
            employers = session.query(Employer).all()
            assert len(employers) == 1

            employer = employers[0]
            assert employer.name == 'Test Automotive GmbH'
            assert employer.country == 'DE'
            assert employer.contact_email == 'test@automotive.de'
            assert employer.sector == 'Automotive'
            assert employer.status == EmployerStatus.PROSPECTIVE