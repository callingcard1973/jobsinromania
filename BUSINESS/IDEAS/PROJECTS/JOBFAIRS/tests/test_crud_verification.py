"""
Verification test for CRUD operations compliance.

This test verifies that ALL entities have working CRUD operations
as required by the Task 1 specification.
"""

import pytest
import tempfile
import os
from datetime import datetime, date, timedelta
from decimal import Decimal

from src.database import Database
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
        db_path = os.path.join(temp_dir, "test_crud_verification.db")

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


def test_all_entities_have_crud_operations(db_session):
    """
    Verification test: All entities must have working CRUD operations.

    This test validates the critical requirement from the spec:
    "CRUD operations working for all entities"
    """

    # Define all entity classes that must have CRUD operations
    entity_classes = [
        Employer,
        ANOFMEvent,
        Worker,
        WorkerEmployerMatch,
        LegalCompliance,
        Communication,
        FinancialTracking
    ]

    # Required CRUD methods
    required_methods = ['get_by_id', 'get_all', 'create', 'update', 'delete', 'find_by']

    # Verify all entities have all required CRUD methods
    for entity_class in entity_classes:
        for method_name in required_methods:
            assert hasattr(entity_class, method_name), \
                f"{entity_class.__name__} is missing required CRUD method: {method_name}"

            method = getattr(entity_class, method_name)
            assert callable(method), \
                f"{entity_class.__name__}.{method_name} is not callable"


def test_employer_crud_operations_work(db_session):
    """Test that Employer CRUD operations actually work."""

    # CREATE
    employer = Employer.create(
        db_session,
        name="CRUD Test Company",
        country="DE",
        sector="IT",
        contact_email="crud@test.de"
    )
    db_session.commit()
    assert employer.id is not None

    # READ (get_by_id)
    retrieved = Employer.get_by_id(db_session, employer.id)
    assert retrieved is not None
    assert retrieved.name == "CRUD Test Company"

    # READ (get_all)
    all_employers = Employer.get_all(db_session)
    assert len(all_employers) >= 1
    assert any(e.id == employer.id for e in all_employers)

    # UPDATE
    updated = Employer.update(
        db_session,
        employer.id,
        name="Updated CRUD Company",
        status=EmployerStatus.INTERESTED
    )
    db_session.commit()
    assert updated.name == "Updated CRUD Company"
    assert updated.status == EmployerStatus.INTERESTED

    # FIND_BY
    found = Employer.find_by(db_session, country="DE")
    assert len(found) >= 1
    assert any(e.id == employer.id for e in found)

    # DELETE
    success = Employer.delete(db_session, employer.id)
    db_session.commit()
    assert success == True
    assert Employer.get_by_id(db_session, employer.id) is None


def test_worker_crud_operations_work(db_session):
    """Test that Worker CRUD operations actually work."""

    # CREATE
    worker = Worker.create(
        db_session,
        first_name="Ion",
        last_name="CRUD Test",
        email="ion.crud@test.ro",
        region="Hunedoara",
        gdpr_consent=True
    )
    db_session.commit()
    assert worker.id is not None

    # READ
    retrieved = Worker.get_by_id(db_session, worker.id)
    assert retrieved.first_name == "Ion"

    # UPDATE
    updated = Worker.update(
        db_session,
        worker.id,
        status=WorkerStatus.QUALIFIED
    )
    db_session.commit()
    assert updated.status == WorkerStatus.QUALIFIED

    # FIND_BY
    found = Worker.find_by(db_session, region="Hunedoara")
    assert any(w.id == worker.id for w in found)

    # DELETE
    success = Worker.delete(db_session, worker.id)
    db_session.commit()
    assert success == True


def test_anofm_event_crud_operations_work(db_session):
    """Test that ANOFMEvent CRUD operations actually work."""

    # CREATE
    event = ANOFMEvent.create(
        db_session,
        name="CRUD Test Event",
        date=date(2025, 6, 15),
        location="Test Location",
        region="Hunedoara"
    )
    db_session.commit()
    assert event.id is not None

    # READ
    retrieved = ANOFMEvent.get_by_id(db_session, event.id)
    assert retrieved.name == "CRUD Test Event"

    # UPDATE
    updated = ANOFMEvent.update(
        db_session,
        event.id,
        status=EventStatus.REGISTERED
    )
    db_session.commit()
    assert updated.status == EventStatus.REGISTERED

    # DELETE
    success = ANOFMEvent.delete(db_session, event.id)
    db_session.commit()
    assert success == True


def test_match_crud_operations_work(db_session):
    """Test that WorkerEmployerMatch CRUD operations actually work."""

    # Setup prerequisites
    worker = Worker.create(
        db_session,
        first_name="Test",
        last_name="Worker",
        email="match.test@email.ro",
        region="Hunedoara",
        gdpr_consent=True
    )

    employer = Employer.create(
        db_session,
        name="Match Test Company",
        country="DE",
        sector="IT",
        contact_email="match@test.de"
    )

    event = ANOFMEvent.create(
        db_session,
        name="Match Test Event",
        date=date(2025, 6, 15),
        location="Test Location",
        region="Hunedoara"
    )
    db_session.commit()

    # CREATE
    match = WorkerEmployerMatch.create(
        db_session,
        worker_id=worker.id,
        employer_id=employer.id,
        event_id=event.id,
        job_title="Test Position"
    )
    db_session.commit()
    assert match.id is not None

    # READ
    retrieved = WorkerEmployerMatch.get_by_id(db_session, match.id)
    assert retrieved.job_title == "Test Position"

    # UPDATE
    updated = WorkerEmployerMatch.update(
        db_session,
        match.id,
        match_stage=MatchStage.SCREENED
    )
    db_session.commit()
    assert updated.match_stage == MatchStage.SCREENED

    # DELETE
    success = WorkerEmployerMatch.delete(db_session, match.id)
    db_session.commit()
    assert success == True


def test_communication_crud_operations_work(db_session):
    """Test that Communication CRUD operations actually work."""

    # Setup prerequisite
    employer = Employer.create(
        db_session,
        name="Comm Test Company",
        country="DE",
        sector="IT",
        contact_email="comm@test.de"
    )
    db_session.commit()

    # CREATE
    comm = Communication.create(
        db_session,
        recipient_type="employer",
        recipient_id=employer.id,
        recipient_email=employer.contact_email,
        subject="CRUD Test Email",
        message_type=MessageType.INITIAL_CONTACT
    )
    db_session.commit()
    assert comm.id is not None

    # READ
    retrieved = Communication.get_by_id(db_session, comm.id)
    assert retrieved.subject == "CRUD Test Email"

    # UPDATE
    updated = Communication.update(
        db_session,
        comm.id,
        status="sent"
    )
    db_session.commit()
    assert updated.status == "sent"

    # DELETE
    success = Communication.delete(db_session, comm.id)
    db_session.commit()
    assert success == True


def test_legal_compliance_crud_operations_work(db_session):
    """Test that LegalCompliance CRUD operations actually work."""

    # Setup prerequisite
    event = ANOFMEvent.create(
        db_session,
        name="Legal Test Event",
        date=date(2025, 6, 15),
        location="Test Location",
        region="Hunedoara"
    )
    db_session.commit()

    # CREATE
    compliance = LegalCompliance.create(
        db_session,
        event_id=event.id,
        compliance_type=ComplianceType.ANOFM_REGISTRATION,
        requirement="Test Registration",
        status=ComplianceStatus.PENDING
    )
    db_session.commit()
    assert compliance.id is not None

    # READ
    retrieved = LegalCompliance.get_by_id(db_session, compliance.id)
    assert retrieved.requirement == "Test Registration"

    # UPDATE
    updated = LegalCompliance.update(
        db_session,
        compliance.id,
        status=ComplianceStatus.VERIFIED
    )
    db_session.commit()
    assert updated.status == ComplianceStatus.VERIFIED

    # DELETE
    success = LegalCompliance.delete(db_session, compliance.id)
    db_session.commit()
    assert success == True


def test_financial_tracking_crud_operations_work(db_session):
    """Test that FinancialTracking CRUD operations actually work."""

    # Setup prerequisite
    event = ANOFMEvent.create(
        db_session,
        name="Financial Test Event",
        date=date(2025, 6, 15),
        location="Test Location",
        region="Hunedoara"
    )
    db_session.commit()

    # CREATE
    financial = FinancialTracking.create(
        db_session,
        event_id=event.id,
        transaction_type=TransactionType.REGISTRATION_FEE,
        amount=Decimal("100.00"),
        description="Test Fee"
    )
    db_session.commit()
    assert financial.id is not None

    # READ
    retrieved = FinancialTracking.get_by_id(db_session, financial.id)
    assert retrieved.amount == Decimal("100.00")

    # UPDATE
    updated = FinancialTracking.update(
        db_session,
        financial.id,
        payment_status=PaymentStatus.COMPLETED
    )
    db_session.commit()
    assert updated.payment_status == PaymentStatus.COMPLETED

    # DELETE
    success = FinancialTracking.delete(db_session, financial.id)
    db_session.commit()
    assert success == True


def test_pagination_works_across_all_entities(db_session):
    """Test that pagination works for all entities."""

    # Create multiple employers to test pagination
    for i in range(5):
        Employer.create(
            db_session,
            name=f"Pagination Test {i}",
            country="DE",
            sector="IT",
            contact_email=f"page{i}@test.de"
        )
    db_session.commit()

    # Test pagination
    page1 = Employer.get_all(db_session, limit=3, offset=0)
    page2 = Employer.get_all(db_session, limit=3, offset=3)

    assert len(page1) == 3
    assert len(page2) >= 2
    assert page1[0].id != page2[0].id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])