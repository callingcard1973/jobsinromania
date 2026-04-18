"""
Comprehensive CRUD operations tests for all database models.

Tests cover:
- Create, Read, Update, Delete operations for all entities
- Pagination functionality
- Filtering by criteria
- Error handling for invalid operations
- Data integrity validation
"""

import pytest
import tempfile
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

from src.database import Database, get_database
from src.database.models import (
    Employer, ANOFMEvent, Worker, WorkerEmployerMatch,
    LegalCompliance, Communication, FinancialTracking,
    EmployerStatus, EventStatus, WorkerStatus, MatchStage,
    ComplianceType, ComplianceStatus, MessageType,
    TransactionType, PaymentStatus
)
from config import Config


@pytest.fixture
def temp_database():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = os.path.join(temp_dir, "test_crud.db")

        # Create test configuration
        test_config = Config()
        test_config.database.sqlite_path = db_path

        # Patch the global config
        import config
        original_config = config.config
        config.config = test_config

        try:
            db = Database()
            db.initialize_database()
            yield db
        finally:
            db.close_connections()
            config.config = original_config


@pytest.fixture
def db_session(temp_database):
    """Get a database session for testing."""
    db = temp_database
    with db.get_session() as session:
        yield session


class TestEmployerCRUD:
    """Test CRUD operations for Employer model."""

    def test_create_employer(self, db_session):
        """Test creating an employer."""
        employer = Employer.create(
            db_session,
            name="Tech Solutions GmbH",
            country="DE",
            sector="IT",
            contact_email="hr@techsolutions.de",
            contact_person="Anna Schmidt"
        )
        db_session.commit()

        assert employer.id is not None
        assert employer.name == "Tech Solutions GmbH"
        assert employer.status == EmployerStatus.PROSPECTIVE

    def test_get_employer_by_id(self, db_session):
        """Test retrieving employer by ID."""
        employer = Employer.create(
            db_session,
            name="Build Corp",
            country="AT",
            sector="Construction",
            contact_email="info@buildcorp.at"
        )
        db_session.commit()

        retrieved = Employer.get_by_id(db_session, employer.id)
        assert retrieved is not None
        assert retrieved.name == "Build Corp"
        assert retrieved.id == employer.id

    def test_get_all_employers_with_pagination(self, db_session):
        """Test getting all employers with pagination."""
        # Create multiple employers
        for i in range(5):
            Employer.create(
                db_session,
                name=f"Company {i}",
                country="DE",
                sector="IT",
                contact_email=f"hr{i}@company{i}.de"
            )
        db_session.commit()

        # Test pagination
        page1 = Employer.get_all(db_session, limit=3, offset=0)
        page2 = Employer.get_all(db_session, limit=3, offset=3)

        assert len(page1) == 3
        assert len(page2) == 2
        assert page1[0].id != page2[0].id  # Different records

    def test_update_employer(self, db_session):
        """Test updating an employer."""
        employer = Employer.create(
            db_session,
            name="Old Name",
            country="DE",
            sector="IT",
            contact_email="old@company.de"
        )
        db_session.commit()

        updated = Employer.update(
            db_session,
            employer.id,
            name="New Name",
            status=EmployerStatus.INTERESTED
        )
        db_session.commit()

        assert updated.name == "New Name"
        assert updated.status == EmployerStatus.INTERESTED
        assert updated.contact_email == "old@company.de"  # Unchanged

    def test_delete_employer(self, db_session):
        """Test deleting an employer."""
        employer = Employer.create(
            db_session,
            name="To Delete",
            country="DE",
            sector="IT",
            contact_email="delete@company.de"
        )
        db_session.commit()

        success = Employer.delete(db_session, employer.id)
        db_session.commit()

        assert success == True
        assert Employer.get_by_id(db_session, employer.id) is None

    def test_find_employers_by_criteria(self, db_session):
        """Test finding employers by criteria."""
        # Create test employers
        Employer.create(
            db_session,
            name="German Tech",
            country="DE",
            sector="IT",
            contact_email="hr@germantech.de"
        )
        Employer.create(
            db_session,
            name="Austrian Build",
            country="AT",
            sector="Construction",
            contact_email="hr@austrianbuild.at"
        )
        Employer.create(
            db_session,
            name="German Construction",
            country="DE",
            sector="Construction",
            contact_email="hr@germanconst.de"
        )
        db_session.commit()

        # Find by country
        german_employers = Employer.find_by(db_session, country="DE")
        assert len(german_employers) == 2

        # Find by sector
        it_employers = Employer.find_by(db_session, sector="IT")
        assert len(it_employers) == 1
        assert it_employers[0].name == "German Tech"

        # Find by multiple criteria
        german_construction = Employer.find_by(
            db_session, country="DE", sector="Construction"
        )
        assert len(german_construction) == 1
        assert german_construction[0].name == "German Construction"


class TestWorkerCRUD:
    """Test CRUD operations for Worker model."""

    def test_create_worker(self, db_session):
        """Test creating a worker."""
        worker = Worker.create(
            db_session,
            first_name="Ion",
            last_name="Popescu",
            email="ion.popescu@email.ro",
            region="Hunedoara",
            sector_experience="Construction",
            gdpr_consent=True,
            consent_source="web_form"
        )
        db_session.commit()

        assert worker.id is not None
        assert worker.first_name == "Ion"
        assert worker.gdpr_consent == True
        assert worker.data_retention_until is not None

    def test_get_worker_by_id(self, db_session):
        """Test retrieving worker by ID."""
        worker = Worker.create(
            db_session,
            first_name="Maria",
            last_name="Ionescu",
            email="maria@email.ro",
            region="Gorj",
            gdpr_consent=True
        )
        db_session.commit()

        retrieved = Worker.get_by_id(db_session, worker.id)
        assert retrieved is not None
        assert retrieved.first_name == "Maria"
        assert retrieved.last_name == "Ionescu"

    def test_update_worker(self, db_session):
        """Test updating a worker."""
        worker = Worker.create(
            db_session,
            first_name="Pavel",
            last_name="Constantin",
            email="pavel@email.ro",
            region="Vaslui",
            gdpr_consent=True
        )
        db_session.commit()

        updated = Worker.update(
            db_session,
            worker.id,
            status=WorkerStatus.QUALIFIED,
            years_experience=5
        )
        db_session.commit()

        assert updated.status == WorkerStatus.QUALIFIED
        assert updated.years_experience == 5
        assert updated.first_name == "Pavel"  # Unchanged

    def test_delete_worker(self, db_session):
        """Test deleting a worker."""
        worker = Worker.create(
            db_session,
            first_name="To Delete",
            last_name="Worker",
            email="delete@email.ro",
            region="Hunedoara",
            gdpr_consent=True
        )
        db_session.commit()

        success = Worker.delete(db_session, worker.id)
        db_session.commit()

        assert success == True
        assert Worker.get_by_id(db_session, worker.id) is None

    def test_find_workers_by_criteria(self, db_session):
        """Test finding workers by criteria."""
        # Create test workers
        Worker.create(
            db_session,
            first_name="Ion1",
            last_name="Test1",
            email="ion1@email.ro",
            region="Hunedoara",
            sector_experience="Construction",
            gdpr_consent=True
        )
        Worker.create(
            db_session,
            first_name="Maria1",
            last_name="Test1",
            email="maria1@email.ro",
            region="Gorj",
            sector_experience="Manufacturing",
            gdpr_consent=True
        )
        db_session.commit()

        # Find by region
        hunedoara_workers = Worker.find_by(db_session, region="Hunedoara")
        assert len(hunedoara_workers) == 1
        assert hunedoara_workers[0].first_name == "Ion1"

        # Find by sector experience
        construction_workers = Worker.find_by(
            db_session, sector_experience="Construction"
        )
        assert len(construction_workers) == 1


class TestANOFMEventCRUD:
    """Test CRUD operations for ANOFMEvent model."""

    def test_create_event(self, db_session):
        """Test creating an event."""
        event = ANOFMEvent.create(
            db_session,
            name="Bursa Locurilor de Munca Hunedoara",
            date=date(2025, 6, 15),
            location="Casa de Cultura, Deva",
            region="Hunedoara",
            organizer_contact="AJOFM Hunedoara",
            participation_fee=Decimal("200.00")
        )
        db_session.commit()

        assert event.id is not None
        assert event.name == "Bursa Locurilor de Munca Hunedoara"
        assert event.status == EventStatus.ANNOUNCED

    def test_update_event(self, db_session):
        """Test updating an event."""
        event = ANOFMEvent.create(
            db_session,
            name="Test Event",
            date=date(2025, 6, 15),
            location="Test Location",
            region="Hunedoara"
        )
        db_session.commit()

        updated = ANOFMEvent.update(
            db_session,
            event.id,
            status=EventStatus.REGISTERED,
            participation_fee=Decimal("300.00")
        )
        db_session.commit()

        assert updated.status == EventStatus.REGISTERED
        assert updated.participation_fee == Decimal("300.00")

    def test_find_events_by_criteria(self, db_session):
        """Test finding events by criteria."""
        # Create test events
        ANOFMEvent.create(
            db_session,
            name="Hunedoara Event",
            date=date(2025, 6, 15),
            location="Deva",
            region="Hunedoara"
        )
        ANOFMEvent.create(
            db_session,
            name="Gorj Event",
            date=date(2025, 7, 15),
            location="Targu Jiu",
            region="Gorj"
        )
        db_session.commit()

        # Find by region
        hunedoara_events = ANOFMEvent.find_by(db_session, region="Hunedoara")
        assert len(hunedoara_events) == 1
        assert hunedoara_events[0].name == "Hunedoara Event"


class TestWorkerEmployerMatchCRUD:
    """Test CRUD operations for WorkerEmployerMatch model."""

    @pytest.fixture
    def test_entities(self, db_session):
        """Create test worker, employer, and event."""
        worker = Worker.create(
            db_session,
            first_name="Test",
            last_name="Worker",
            email="worker@test.ro",
            region="Hunedoara",
            gdpr_consent=True
        )

        employer = Employer.create(
            db_session,
            name="Test Employer",
            country="DE",
            sector="Construction",
            contact_email="hr@test.de"
        )

        event = ANOFMEvent.create(
            db_session,
            name="Test Event",
            date=date(2025, 6, 15),
            location="Test Location",
            region="Hunedoara"
        )

        db_session.commit()
        return worker, employer, event

    def test_create_match(self, db_session, test_entities):
        """Test creating a worker-employer match."""
        worker, employer, event = test_entities

        match = WorkerEmployerMatch.create(
            db_session,
            worker_id=worker.id,
            employer_id=employer.id,
            event_id=event.id,
            match_score=Decimal("0.85"),
            job_title="Construction Worker"
        )
        db_session.commit()

        assert match.id is not None
        assert match.worker_id == worker.id
        assert match.employer_id == employer.id
        assert match.match_score == Decimal("0.85")

    def test_update_match(self, db_session, test_entities):
        """Test updating a match."""
        worker, employer, event = test_entities

        match = WorkerEmployerMatch.create(
            db_session,
            worker_id=worker.id,
            employer_id=employer.id,
            event_id=event.id
        )
        db_session.commit()

        updated = WorkerEmployerMatch.update(
            db_session,
            match.id,
            match_stage=MatchStage.SCREENED,
            salary_offered=Decimal("2500.00")
        )
        db_session.commit()

        assert updated.match_stage == MatchStage.SCREENED
        assert updated.salary_offered == Decimal("2500.00")

    def test_find_matches_by_criteria(self, db_session, test_entities):
        """Test finding matches by criteria."""
        worker, employer, event = test_entities

        # Create multiple matches
        WorkerEmployerMatch.create(
            db_session,
            worker_id=worker.id,
            employer_id=employer.id,
            event_id=event.id,
            match_stage=MatchStage.IDENTIFIED
        )

        # Create second worker and match
        worker2 = Worker.create(
            db_session,
            first_name="Worker2",
            last_name="Test",
            email="worker2@test.ro",
            region="Gorj",
            gdpr_consent=True
        )

        WorkerEmployerMatch.create(
            db_session,
            worker_id=worker2.id,
            employer_id=employer.id,
            event_id=event.id,
            match_stage=MatchStage.SCREENED
        )
        db_session.commit()

        # Find by employer
        employer_matches = WorkerEmployerMatch.find_by(
            db_session, employer_id=employer.id
        )
        assert len(employer_matches) == 2

        # Find by match stage
        screened_matches = WorkerEmployerMatch.find_by(
            db_session, match_stage=MatchStage.SCREENED
        )
        assert len(screened_matches) == 1


class TestCommunicationCRUD:
    """Test CRUD operations for Communication model."""

    @pytest.fixture
    def test_employer(self, db_session):
        """Create test employer."""
        employer = Employer.create(
            db_session,
            name="Test Company",
            country="DE",
            sector="IT",
            contact_email="test@company.de"
        )
        db_session.commit()
        return employer

    def test_create_communication(self, db_session, test_employer):
        """Test creating a communication."""
        comm = Communication.create(
            db_session,
            recipient_type="employer",
            recipient_id=test_employer.id,
            recipient_email=test_employer.contact_email,
            subject="Job Fair Invitation",
            message_type=MessageType.INVITATION,
            campaign_id="test_campaign"
        )
        db_session.commit()

        assert comm.id is not None
        assert comm.recipient_type == "employer"
        assert comm.status == "pending"

    def test_update_communication(self, db_session, test_employer):
        """Test updating a communication."""
        comm = Communication.create(
            db_session,
            recipient_type="employer",
            recipient_id=test_employer.id,
            recipient_email=test_employer.contact_email,
            subject="Test Email",
            message_type=MessageType.INITIAL_CONTACT
        )
        db_session.commit()

        updated = Communication.update(
            db_session,
            comm.id,
            status="sent",
            provider="brevo"
        )
        db_session.commit()

        assert updated.status == "sent"
        assert updated.provider == "brevo"


class TestLegalComplianceCRUD:
    """Test CRUD operations for LegalCompliance model."""

    @pytest.fixture
    def test_event(self, db_session):
        """Create test event."""
        event = ANOFMEvent.create(
            db_session,
            name="Test Event",
            date=date(2025, 6, 15),
            location="Test Location",
            region="Hunedoara"
        )
        db_session.commit()
        return event

    def test_create_compliance(self, db_session, test_event):
        """Test creating a compliance record."""
        compliance = LegalCompliance.create(
            db_session,
            event_id=test_event.id,
            compliance_type=ComplianceType.ANOFM_REGISTRATION,
            requirement="Register participation with ANOFM",
            status=ComplianceStatus.PENDING
        )
        db_session.commit()

        assert compliance.id is not None
        assert compliance.compliance_type == ComplianceType.ANOFM_REGISTRATION
        assert compliance.status == ComplianceStatus.PENDING

    def test_update_compliance(self, db_session, test_event):
        """Test updating a compliance record."""
        compliance = LegalCompliance.create(
            db_session,
            event_id=test_event.id,
            compliance_type=ComplianceType.WORK_PERMIT,
            requirement="Valid work permit",
            status=ComplianceStatus.PENDING
        )
        db_session.commit()

        updated = LegalCompliance.update(
            db_session,
            compliance.id,
            status=ComplianceStatus.VERIFIED,
            verified_by="Admin User"
        )
        db_session.commit()

        assert updated.status == ComplianceStatus.VERIFIED
        assert updated.verified_by == "Admin User"


class TestFinancialTrackingCRUD:
    """Test CRUD operations for FinancialTracking model."""

    @pytest.fixture
    def test_event(self, db_session):
        """Create test event."""
        event = ANOFMEvent.create(
            db_session,
            name="Test Event",
            date=date(2025, 6, 15),
            location="Test Location",
            region="Hunedoara"
        )
        db_session.commit()
        return event

    def test_create_financial_record(self, db_session, test_event):
        """Test creating a financial record."""
        financial = FinancialTracking.create(
            db_session,
            event_id=test_event.id,
            transaction_type=TransactionType.REGISTRATION_FEE,
            amount=Decimal("200.00"),
            currency="EUR",
            description="Event registration fee"
        )
        db_session.commit()

        assert financial.id is not None
        assert financial.transaction_type == TransactionType.REGISTRATION_FEE
        assert financial.amount == Decimal("200.00")
        assert financial.payment_status == PaymentStatus.PENDING

    def test_update_financial_record(self, db_session, test_event):
        """Test updating a financial record."""
        financial = FinancialTracking.create(
            db_session,
            event_id=test_event.id,
            transaction_type=TransactionType.PLACEMENT_FEE,
            amount=Decimal("500.00"),
            description="Placement fee"
        )
        db_session.commit()

        updated = FinancialTracking.update(
            db_session,
            financial.id,
            payment_status=PaymentStatus.COMPLETED,
            payment_date=date.today()
        )
        db_session.commit()

        assert updated.payment_status == PaymentStatus.COMPLETED
        assert updated.payment_date == date.today()

    def test_find_financial_by_criteria(self, db_session, test_event):
        """Test finding financial records by criteria."""
        # Create multiple records
        FinancialTracking.create(
            db_session,
            event_id=test_event.id,
            transaction_type=TransactionType.REGISTRATION_FEE,
            amount=Decimal("200.00"),
            payment_status=PaymentStatus.PENDING
        )

        FinancialTracking.create(
            db_session,
            event_id=test_event.id,
            transaction_type=TransactionType.PLACEMENT_FEE,
            amount=Decimal("500.00"),
            payment_status=PaymentStatus.COMPLETED
        )
        db_session.commit()

        # Find by transaction type
        registration_fees = FinancialTracking.find_by(
            db_session, transaction_type=TransactionType.REGISTRATION_FEE
        )
        assert len(registration_fees) == 1
        assert registration_fees[0].amount == Decimal("200.00")

        # Find by payment status
        pending_payments = FinancialTracking.find_by(
            db_session, payment_status=PaymentStatus.PENDING
        )
        assert len(pending_payments) == 1


class TestCRUDErrorHandling:
    """Test error handling in CRUD operations."""

    def test_get_nonexistent_record(self, db_session):
        """Test getting a record that doesn't exist."""
        result = Employer.get_by_id(db_session, 99999)
        assert result is None

    def test_update_nonexistent_record(self, db_session):
        """Test updating a record that doesn't exist."""
        result = Employer.update(db_session, 99999, name="New Name")
        assert result is None

    def test_delete_nonexistent_record(self, db_session):
        """Test deleting a record that doesn't exist."""
        result = Employer.delete(db_session, 99999)
        assert result == False

    def test_find_with_invalid_criteria(self, db_session):
        """Test finding records with invalid criteria."""
        # Should return empty list for non-existent attributes
        results = Employer.find_by(db_session, nonexistent_field="value")
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])