"""
Comprehensive tests for the Job Fair Integration System database.

Tests cover:
- Database initialization and connection
- Model creation and validation
- CRUD operations for all entities
- Foreign key constraints
- GDPR compliance features
- Data retention handling
- Performance indexes
"""

import pytest
import tempfile
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import inspect, text

# Import test modules
from src.database import (
    Database, get_database, init_database,
    Employer, ANOFMEvent, Worker, WorkerEmployerMatch,
    LegalCompliance, Communication, FinancialTracking
)
from src.database.models import (
    EmployerStatus, EventStatus, WorkerStatus, MatchStage,
    ComplianceType, ComplianceStatus, MessageType,
    TransactionType, PaymentStatus
)
from config import Config


@pytest.fixture
def temp_database():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test.db")

        # Create test configuration
        test_config = Config()
        test_config.database.sqlite_path = db_path

        # Patch the global config
        import config
        original_config = config.config
        config.config = test_config

        try:
            db = Database()
            yield db
        finally:
            db.close_connections()
            config.config = original_config


class TestDatabaseConnection:
    """Test database connection and initialization."""

    def test_database_initialization(self, temp_database):
        """Test database initialization creates all tables."""
        db = temp_database

        # Initialize database
        assert db.initialize_database() == True

        # Check tables were created
        inspector = inspect(db.sqlite_engine)
        tables = set(inspector.get_table_names())

        expected_tables = {
            'employers', 'anofm_events', 'workers', 'worker_employer_matches',
            'legal_compliance', 'communications', 'financial_tracking'
        }

        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    def test_connection_testing(self, temp_database):
        """Test connection testing functionality."""
        db = temp_database
        db.initialize_database()

        results = db.test_connections()

        # SQLite should work
        assert results['sqlite'] == True

        # PostgreSQL might fail (test environment)
        # We don't fail the test for this as it's environment dependent

    def test_database_info(self, temp_database):
        """Test database info retrieval."""
        db = temp_database
        db.initialize_database()

        info = db.get_database_info()

        assert 'sqlite_path' in info
        assert 'tables' in info
        assert 'table_counts' in info
        assert info['initialized'] == True

        # Check all expected tables are present
        expected_tables = {
            'employers', 'anofm_events', 'workers', 'worker_employer_matches',
            'legal_compliance', 'communications', 'financial_tracking'
        }
        assert expected_tables.issubset(set(info['tables']))

    def test_session_management(self, temp_database):
        """Test database session management."""
        db = temp_database
        db.initialize_database()

        # Test SQLite session
        with db.get_session() as session:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_foreign_key_enforcement(self, temp_database):
        """Test that foreign key constraints are enforced."""
        db = temp_database
        db.initialize_database()

        with db.get_session() as session:
            # Try to create a match with non-existent worker
            match = WorkerEmployerMatch(
                worker_id=999,  # Non-existent
                employer_id=999  # Non-existent
            )
            session.add(match)

            # This should fail due to foreign key constraints
            with pytest.raises(Exception):  # SQLite will raise IntegrityError
                session.commit()


class TestEmployerModel:
    """Test Employer model functionality."""

    @pytest.fixture
    def db_session(self, temp_database):
        """Get a database session for testing."""
        db = temp_database
        db.initialize_database()
        with db.get_session() as session:
            yield session

    def test_employer_creation(self, db_session):
        """Test creating an employer record."""
        employer = Employer(
            name="Test Construction GmbH",
            country="DE",
            sector="Construction",
            contact_email="hr@testconstruction.de",
            contact_person="Hans Mueller",
            phone="+49 30 12345678",
            website="https://testconstruction.de"
        )

        db_session.add(employer)
        db_session.commit()

        # Verify creation
        assert employer.id is not None
        assert employer.status == EmployerStatus.PROSPECTIVE
        assert employer.created_at is not None
        assert employer.data_retention_until is not None

    def test_employer_validation(self, db_session):
        """Test employer field validation."""
        # Test invalid country code
        with pytest.raises(ValueError):
            employer = Employer(
                name="Test Company",
                country="DEU",  # Should be 2 letters
                sector="IT",
                contact_email="test@company.com"
            )

        # Test invalid email
        with pytest.raises(ValueError):
            employer = Employer(
                name="Test Company",
                country="DE",
                sector="IT",
                contact_email="invalid-email"
            )

    def test_employer_uniqueness(self, db_session):
        """Test email uniqueness constraint."""
        # Create first employer
        employer1 = Employer(
            name="Company A",
            country="DE",
            sector="IT",
            contact_email="contact@company.com"
        )
        db_session.add(employer1)
        db_session.commit()

        # Try to create another with same email
        employer2 = Employer(
            name="Company B",
            country="FR",
            sector="Manufacturing",
            contact_email="contact@company.com"  # Same email
        )
        db_session.add(employer2)

        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()

    def test_employer_search(self, db_session):
        """Test employer search functionality."""
        # Create test employers
        employers = [
            Employer(
                name="German Construction Co",
                country="DE",
                sector="Construction",
                contact_email="hr@germanconst.de"
            ),
            Employer(
                name="French Manufacturing",
                country="FR",
                sector="Manufacturing",
                contact_email="jobs@frenchmanuf.fr"
            )
        ]

        for employer in employers:
            db_session.add(employer)
        db_session.commit()

        # Test search by country
        german_employers = db_session.query(Employer).filter(
            Employer.country == "DE"
        ).all()
        assert len(german_employers) == 1
        assert german_employers[0].name == "German Construction Co"

        # Test search by sector
        construction_employers = db_session.query(Employer).filter(
            Employer.sector == "Construction"
        ).all()
        assert len(construction_employers) == 1


class TestWorkerModel:
    """Test Worker model functionality."""

    @pytest.fixture
    def db_session(self, temp_database):
        """Get a database session for testing."""
        db = temp_database
        db.initialize_database()
        with db.get_session() as session:
            yield session

    def test_worker_creation_with_gdpr(self, db_session):
        """Test creating a worker with GDPR compliance."""
        worker = Worker(
            first_name="Ion",
            last_name="Popescu",
            email="ion.popescu@email.ro",
            phone="0723456789",
            region="Hunedoara",
            sector_experience="Construction",
            gdpr_consent=True,
            consent_source="web_form"
        )

        db_session.add(worker)
        db_session.commit()

        # Verify GDPR compliance
        assert worker.gdpr_consent == True
        assert worker.gdpr_consent_date is not None
        assert worker.data_retention_until is not None
        assert worker.is_gdpr_compliant() == True

    def test_worker_gdpr_validation(self, db_session):
        """Test GDPR compliance validation."""
        # Create worker without consent
        worker = Worker(
            first_name="Maria",
            last_name="Ionescu",
            email="maria@email.ro",
            region="Gorj",
            gdpr_consent=False
        )

        db_session.add(worker)
        db_session.commit()

        assert worker.is_gdpr_compliant() == False

    def test_worker_data_retention(self, db_session):
        """Test data retention calculation."""
        worker = Worker(
            first_name="Pavel",
            last_name="Constantin",
            email="pavel@email.ro",
            region="Vaslui",
            gdpr_consent=True
        )

        db_session.add(worker)
        db_session.commit()

        # Check retention period
        days_until_expiry = worker.days_until_retention_expiry()
        assert days_until_expiry > 0
        assert days_until_expiry <= 1095  # 3 years max

    def test_worker_language_skills(self, db_session):
        """Test JSON field for language skills."""
        worker = Worker(
            first_name="Ana",
            last_name="Dumitrescu",
            email="ana@email.ro",
            region="Hunedoara",
            language_skills={"en": "B2", "de": "A1", "fr": "A2"},
            preferred_countries=["DE", "AT", "FR"],
            gdpr_consent=True
        )

        db_session.add(worker)
        db_session.commit()

        # Verify JSON data
        assert worker.language_skills["en"] == "B2"
        assert "DE" in worker.preferred_countries


class TestANOFMEventModel:
    """Test ANOFM Event model functionality."""

    @pytest.fixture
    def db_session(self, temp_database):
        """Get a database session for testing."""
        db = temp_database
        db.initialize_database()
        with db.get_session() as session:
            yield session

    def test_event_creation(self, db_session):
        """Test creating an ANOFM event."""
        event = ANOFMEvent(
            name="Bursa Locurilor de Munca Hunedoara",
            date=date(2025, 6, 15),
            location="Casa de Cultura, Deva",
            region="Hunedoara",
            organizer_contact="AJOFM Hunedoara",
            organizer_email="contact@ajofm-hunedoara.ro",
            participation_fee=Decimal("200.00"),
            registration_deadline=date(2025, 6, 1)
        )

        db_session.add(event)
        db_session.commit()

        # Verify creation
        assert event.id is not None
        assert event.status == EventStatus.ANNOUNCED
        assert event.is_upcoming() == True
        assert event.is_registration_open() == True

    def test_event_date_logic(self, db_session):
        """Test event date-related methods."""
        # Past event
        past_event = ANOFMEvent(
            name="Past Event",
            date=date(2024, 1, 1),
            location="Test Location",
            region="Hunedoara"
        )

        db_session.add(past_event)
        db_session.commit()

        assert past_event.is_upcoming() == False

    def test_event_region_validation(self, db_session):
        """Test event region handling."""
        # Valid target region
        event = ANOFMEvent(
            name="Test Event",
            date=date(2025, 6, 15),
            location="Test Location",
            region="Hunedoara"  # Valid target region
        )

        db_session.add(event)
        db_session.commit()

        assert event.region == "Hunedoara"


class TestWorkerEmployerMatch:
    """Test WorkerEmployerMatch model functionality."""

    @pytest.fixture
    def db_with_data(self, temp_database):
        """Database with test worker, employer, and event."""
        db = temp_database
        db.initialize_database()

        with db.get_session() as session:
            # Create test employer
            employer = Employer(
                name="Test Construction",
                country="DE",
                sector="Construction",
                contact_email="hr@test.de"
            )
            session.add(employer)

            # Create test worker
            worker = Worker(
                first_name="Test",
                last_name="Worker",
                email="worker@test.ro",
                region="Hunedoara",
                gdpr_consent=True
            )
            session.add(worker)

            # Create test event
            event = ANOFMEvent(
                name="Test Event",
                date=date(2025, 6, 15),
                location="Test Location",
                region="Hunedoara"
            )
            session.add(event)

            session.commit()

            yield db, worker.id, employer.id, event.id

    def test_match_creation(self, db_with_data):
        """Test creating a worker-employer match."""
        db, worker_id, employer_id, event_id = db_with_data

        with db.get_session() as session:
            match = WorkerEmployerMatch(
                worker_id=worker_id,
                employer_id=employer_id,
                event_id=event_id,
                match_score=Decimal("0.85"),
                job_title="Construction Worker",
                salary_offered=Decimal("2500.00")
            )

            session.add(match)
            session.commit()

            assert match.id is not None
            assert match.match_stage == MatchStage.IDENTIFIED
            assert match.match_score == Decimal("0.85")

    def test_match_stage_advancement(self, db_with_data):
        """Test advancing match stages."""
        db, worker_id, employer_id, event_id = db_with_data

        with db.get_session() as session:
            match = WorkerEmployerMatch(
                worker_id=worker_id,
                employer_id=employer_id,
                event_id=event_id
            )
            session.add(match)
            session.commit()

            # Advance to screened
            success = match.advance_stage(MatchStage.SCREENED, "Initial screening completed")
            assert success == True
            assert match.match_stage == MatchStage.SCREENED

    def test_match_validation(self, db_with_data):
        """Test match field validation."""
        db, worker_id, employer_id, event_id = db_with_data

        with db.get_session() as session:
            # Test invalid match score
            with pytest.raises(ValueError):
                match = WorkerEmployerMatch(
                    worker_id=worker_id,
                    employer_id=employer_id,
                    match_score=Decimal("1.5")  # > 1.0
                )


class TestCommunicationModel:
    """Test Communication model functionality."""

    @pytest.fixture
    def db_with_employer(self, temp_database):
        """Database with test employer."""
        db = temp_database
        db.initialize_database()

        with db.get_session() as session:
            employer = Employer(
                name="Test Company",
                country="DE",
                sector="IT",
                contact_email="test@company.de"
            )
            session.add(employer)
            session.commit()

            yield db, employer.id

    def test_communication_creation(self, db_with_employer):
        """Test creating a communication record."""
        db, employer_id = db_with_employer

        with db.get_session() as session:
            comm = Communication(
                recipient_type="employer",
                recipient_id=employer_id,
                recipient_email="test@company.de",
                subject="Job Fair Invitation",
                message_type=MessageType.INVITATION,
                campaign_id="pilot_2025_q2"
            )

            session.add(comm)
            session.commit()

            assert comm.id is not None
            assert comm.status == "pending"
            assert comm.created_at is not None

    def test_communication_status_updates(self, db_with_employer):
        """Test communication status update methods."""
        db, employer_id = db_with_employer

        with db.get_session() as session:
            comm = Communication(
                recipient_type="employer",
                recipient_id=employer_id,
                recipient_email="test@company.de",
                subject="Test Email",
                message_type=MessageType.INITIAL_CONTACT
            )
            session.add(comm)
            session.commit()

            # Mark as sent
            comm.mark_sent("brevo_123", "brevo")
            session.commit()

            assert comm.status == "sent"
            assert comm.sent_date is not None
            assert comm.provider == "brevo"
            assert comm.provider_message_id == "brevo_123"

    def test_communication_validation(self, db_with_employer):
        """Test communication field validation."""
        db, employer_id = db_with_employer

        with db.get_session() as session:
            # Test invalid recipient type
            with pytest.raises(ValueError):
                comm = Communication(
                    recipient_type="invalid_type",
                    recipient_id=employer_id,
                    recipient_email="test@company.de",
                    subject="Test",
                    message_type=MessageType.INITIAL_CONTACT
                )


class TestLegalComplianceModel:
    """Test Legal Compliance model functionality."""

    @pytest.fixture
    def db_with_event(self, temp_database):
        """Database with test event."""
        db = temp_database
        db.initialize_database()

        with db.get_session() as session:
            event = ANOFMEvent(
                name="Test Event",
                date=date(2025, 6, 15),
                location="Test Location",
                region="Hunedoara"
            )
            session.add(event)
            session.commit()

            yield db, event.id

    def test_compliance_creation(self, db_with_event):
        """Test creating a compliance record."""
        db, event_id = db_with_event

        with db.get_session() as session:
            compliance = LegalCompliance(
                event_id=event_id,
                compliance_type=ComplianceType.ANOFM_REGISTRATION,
                requirement="Register participation with ANOFM",
                status=ComplianceStatus.PENDING,
                expiration_date=date(2025, 6, 10)
            )

            session.add(compliance)
            session.commit()

            assert compliance.id is not None
            assert compliance.status == ComplianceStatus.PENDING

    def test_compliance_expiry_check(self, db_with_event):
        """Test compliance expiry checking."""
        db, event_id = db_with_event

        with db.get_session() as session:
            # Expired compliance
            expired_compliance = LegalCompliance(
                event_id=event_id,
                compliance_type=ComplianceType.WORK_PERMIT,
                requirement="Valid work permit",
                expiration_date=date(2024, 1, 1)  # Past date
            )
            session.add(expired_compliance)
            session.commit()

            assert expired_compliance.is_expired() == True
            assert expired_compliance.days_until_expiry() < 0


class TestFinancialTrackingModel:
    """Test Financial Tracking model functionality."""

    @pytest.fixture
    def db_with_event(self, temp_database):
        """Database with test event."""
        db = temp_database
        db.initialize_database()

        with db.get_session() as session:
            event = ANOFMEvent(
                name="Test Event",
                date=date(2025, 6, 15),
                location="Test Location",
                region="Hunedoara"
            )
            session.add(event)
            session.commit()

            yield db, event.id

    def test_financial_record_creation(self, db_with_event):
        """Test creating a financial record."""
        db, event_id = db_with_event

        with db.get_session() as session:
            transaction = FinancialTracking(
                event_id=event_id,
                transaction_type=TransactionType.REGISTRATION_FEE,
                amount=Decimal("200.00"),
                currency="EUR",
                description="ANOFM event registration fee",
                invoice_number="INV-2025-001"
            )

            session.add(transaction)
            session.commit()

            assert transaction.id is not None
            assert transaction.payment_status == PaymentStatus.PENDING
            assert transaction.amount == Decimal("200.00")

    def test_financial_validation(self, db_with_event):
        """Test financial record validation."""
        db, event_id = db_with_event

        with db.get_session() as session:
            # Test negative amount validation
            with pytest.raises(ValueError):
                transaction = FinancialTracking(
                    event_id=event_id,
                    transaction_type=TransactionType.PLACEMENT_FEE,
                    amount=Decimal("-100.00")  # Negative amount
                )

    def test_financial_overdue_check(self, db_with_event):
        """Test overdue payment checking."""
        db, event_id = db_with_event

        with db.get_session() as session:
            # Create overdue transaction
            old_transaction = FinancialTracking(
                event_id=event_id,
                transaction_type=TransactionType.REGISTRATION_FEE,
                amount=Decimal("200.00"),
                invoice_date=date.today() - timedelta(days=45)  # 45 days ago
            )
            session.add(old_transaction)
            session.commit()

            assert old_transaction.is_overdue(days=30) == True
            assert old_transaction.is_overdue(days=60) == False


class TestDatabaseIntegration:
    """Integration tests for complete database functionality."""

    @pytest.fixture
    def full_database(self, temp_database):
        """Fully initialized database with sample data."""
        db = temp_database
        db.initialize_database()

        with db.get_session() as session:
            # Create sample employer
            employer = Employer(
                name="Deutsche Bau GmbH",
                country="DE",
                sector="Construction",
                contact_email="hr@deutschebau.de",
                contact_person="Klaus Weber",
                phone="+49 30 1234567"
            )
            session.add(employer)

            # Create sample worker
            worker = Worker(
                first_name="Mihai",
                last_name="Popescu",
                email="mihai.popescu@email.ro",
                region="Hunedoara",
                sector_experience="Construction",
                language_skills={"en": "B1", "de": "A2"},
                gdpr_consent=True
            )
            session.add(worker)

            # Create sample event
            event = ANOFMEvent(
                name="Bursa Locurilor de Munca Hunedoara",
                date=date(2025, 6, 15),
                location="Casa de Cultura, Deva",
                region="Hunedoara",
                participation_fee=Decimal("200.00")
            )
            session.add(event)

            session.commit()

            yield db, worker, employer, event

    def test_complete_workflow(self, full_database):
        """Test a complete workflow from employer contact to placement."""
        db, worker, employer, event = full_database

        with db.get_session() as session:
            # Step 1: Create initial communication
            comm = Communication(
                recipient_type="employer",
                recipient_id=employer.id,
                recipient_email=employer.contact_email,
                subject="Job Fair Invitation - Hunedoara",
                message_type=MessageType.INVITATION,
                campaign_id="pilot_2025_q2"
            )
            session.add(comm)

            # Step 2: Create worker-employer match
            match = WorkerEmployerMatch(
                worker_id=worker.id,
                employer_id=employer.id,
                event_id=event.id,
                match_score=Decimal("0.88"),
                job_title="Construction Worker",
                salary_offered=Decimal("2500.00")
            )
            session.add(match)

            # Step 3: Create compliance requirements
            compliance = LegalCompliance(
                event_id=event.id,
                worker_id=worker.id,
                employer_id=employer.id,
                compliance_type=ComplianceType.WORK_PERMIT,
                requirement="EU work permit verification",
                status=ComplianceStatus.PENDING
            )
            session.add(compliance)

            # Step 4: Create financial record
            financial = FinancialTracking(
                event_id=event.id,
                worker_id=worker.id,
                transaction_type=TransactionType.PLACEMENT_FEE,
                amount=Decimal("500.00"),
                description="Successful placement fee"
            )
            session.add(financial)

            session.commit()

            # Verify all relationships work
            assert len(worker.matches) == 1
            assert len(employer.matches) == 1
            assert len(event.matches) == 1
            assert len(event.legal_compliance) == 1
            assert len(event.financial_tracking) == 1

    def test_gdpr_data_cleanup(self, full_database):
        """Test GDPR data retention and cleanup."""
        db, worker, employer, event = full_database

        with db.get_session() as session:
            # Check worker GDPR compliance
            assert worker.is_gdpr_compliant() == True

            # Simulate expired consent
            worker.data_retention_until = date.today() - timedelta(days=1)
            session.commit()

            # Check compliance status
            assert worker.days_until_retention_expiry() < 0

    def test_database_constraints_and_indexes(self, full_database):
        """Test that database constraints and indexes are working."""
        db, worker, employer, event = full_database

        # Test that we can query efficiently using indexes
        with db.get_session() as session:
            # These queries should use indexes
            employers_by_country = session.query(Employer).filter(
                Employer.country == "DE"
            ).all()

            workers_by_region = session.query(Worker).filter(
                Worker.region == "Hunedoara"
            ).all()

            events_by_date = session.query(ANOFMEvent).filter(
                ANOFMEvent.date >= date.today()
            ).all()

            # Verify results
            assert len(employers_by_country) >= 1
            assert len(workers_by_region) >= 1
            assert len(events_by_date) >= 1


# Test configuration and setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment configuration."""
    import logging

    # Configure logging for tests
    logging.basicConfig(
        level=logging.WARNING,  # Reduce noise in tests
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])