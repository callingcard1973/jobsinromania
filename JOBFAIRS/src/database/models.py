"""
Database models for the European Employer ANOFM Job Fair Integration System.

Defines SQLAlchemy models for:
- Employers: European companies seeking Romanian workers
- ANOFMEvents: Romanian job fair events in target regions
- Workers: Romanian workers seeking EU employment
- WorkerEmployerMatches: Connections between workers and employers
- LegalCompliance: GDPR and employment law tracking
- Communications: Email campaign tracking
- FinancialTracking: Payment and fee tracking

All models include GDPR compliance features and audit trails.
"""

import enum
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Text, Boolean,
    ForeignKey, DECIMAL as SQLDecimal, Enum, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates, Session
from sqlalchemy.sql import func

from config import get_config

Base = declarative_base()
config = get_config()


# Enums for type safety
class EmployerStatus(enum.Enum):
    """Employer status in the recruitment process."""
    PROSPECTIVE = "prospective"  # Identified but not contacted
    CONTACTED = "contacted"      # Email sent, awaiting response
    INTERESTED = "interested"    # Expressed interest
    PARTICIPATING = "participating"  # Confirmed for job fair
    COMPLETED = "completed"      # Completed recruitment process
    DECLINED = "declined"        # Declined participation
    BLOCKED = "blocked"          # Blocked due to compliance issues


class EventStatus(enum.Enum):
    """ANOFM job fair event status."""
    ANNOUNCED = "announced"      # Event announced on ANOFM site
    REGISTERED = "registered"    # We registered for participation
    CONFIRMED = "confirmed"      # Our participation confirmed
    ACTIVE = "active"           # Event is currently running
    COMPLETED = "completed"     # Event finished
    CANCELLED = "cancelled"     # Event was cancelled


class WorkerStatus(enum.Enum):
    """Worker status in the system."""
    REGISTERED = "registered"   # Registered, consent given
    SCREENED = "screened"      # Initial screening completed
    QUALIFIED = "qualified"    # Qualified for EU placement
    MATCHED = "matched"        # Matched with employer(s)
    PLACED = "placed"         # Successfully placed
    WITHDRAWN = "withdrawn"   # Withdrew from program
    INACTIVE = "inactive"     # Data retained but inactive


class MatchStage(enum.Enum):
    """Worker-employer matching stages."""
    IDENTIFIED = "identified"   # System identified potential match
    SCREENED = "screened"      # Initial screening completed
    INTERVIEWED = "interviewed"  # Interview conducted
    OFFERED = "offered"        # Job offer made
    ACCEPTED = "accepted"      # Offer accepted
    PLACED = "placed"         # Worker successfully placed
    REJECTED = "rejected"     # Match rejected
    WITHDRAWN = "withdrawn"   # Match withdrawn


class ComplianceType(enum.Enum):
    """Legal compliance requirement types."""
    GDPR_CONSENT = "gdpr_consent"
    WORK_PERMIT = "work_permit"
    LABOR_CONTRACT = "labor_contract"
    ANOFM_REGISTRATION = "anofm_registration"
    EU_MOBILITY = "eu_mobility"
    INSURANCE = "insurance"
    ACCOMMODATION = "accommodation"
    TRANSPORT = "transport"


class ComplianceStatus(enum.Enum):
    """Compliance verification status."""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class MessageType(enum.Enum):
    """Communication message types."""
    INITIAL_CONTACT = "initial_contact"
    FOLLOW_UP = "follow_up"
    INVITATION = "invitation"
    CONFIRMATION = "confirmation"
    REMINDER = "reminder"
    PLACEMENT_UPDATE = "placement_update"
    GDPR_NOTICE = "gdpr_notice"
    COMPLIANCE_REQUEST = "compliance_request"


class TransactionType(enum.Enum):
    """Financial transaction types."""
    REGISTRATION_FEE = "registration_fee"
    PLACEMENT_FEE = "placement_fee"
    COMPLIANCE_COST = "compliance_cost"
    TRAVEL_EXPENSE = "travel_expense"
    ACCOMMODATION_FEE = "accommodation_fee"
    REFUND = "refund"


class PaymentStatus(enum.Enum):
    """Payment processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


# Base model with common fields
class BaseModel:
    """Base model with common audit fields."""
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class Employer(Base, BaseModel):
    """European employers seeking Romanian workers."""
    __tablename__ = 'employers'

    # Basic information
    name = Column(String(255), nullable=False, index=True)
    country = Column(String(2), nullable=False, index=True)  # ISO 2-letter code
    sector = Column(String(100), nullable=False, index=True)

    # Contact information
    contact_email = Column(String(255), nullable=False, unique=True, index=True)
    contact_person = Column(String(255))
    phone = Column(String(50))
    website = Column(String(255))

    # Address information
    address = Column(Text)
    city = Column(String(100))
    postal_code = Column(String(20))

    # Business information
    company_size = Column(String(50))  # e.g., "50-100", "1000+"
    registration_number = Column(String(50))
    vat_number = Column(String(50))

    # System fields
    status = Column(Enum(EmployerStatus), default=EmployerStatus.PROSPECTIVE,
                   nullable=False, index=True)
    notes = Column(Text)

    # Source tracking
    source_database = Column(String(50))  # e.g., "france_sirene", "germany_register"
    source_record_id = Column(String(100))  # Original record ID in source

    # GDPR compliance
    gdpr_lawful_basis = Column(String(100), default="legitimate_interest")
    data_retention_until = Column(Date)

    # Relationships
    matches = relationship("WorkerEmployerMatch", back_populates="employer")
    communications = relationship("Communication",
                                foreign_keys="Communication.recipient_id",
                                primaryjoin="and_(Employer.id==Communication.recipient_id, "
                                           "Communication.recipient_type=='employer')")

    @validates('country')
    def validate_country(self, key, country):
        """Validate country is a 2-letter ISO code."""
        if len(country) != 2 or not country.isupper():
            raise ValueError("Country must be a 2-letter uppercase ISO code")
        return country

    @validates('contact_email')
    def validate_email(self, key, email):
        """Basic email validation."""
        if '@' not in email or '.' not in email:
            raise ValueError("Invalid email format")
        return email.lower()

    def __repr__(self):
        return f"<Employer(id={self.id}, name='{self.name}', country='{self.country}')>"


class ANOFMEvent(Base, BaseModel):
    """Romanian ANOFM job fair events."""
    __tablename__ = 'anofm_events'

    # Event information
    name = Column(String(255), nullable=False)
    date = Column(Date, nullable=False, index=True)
    end_date = Column(Date)  # For multi-day events
    location = Column(String(255), nullable=False)
    region = Column(String(100), nullable=False, index=True)

    # Organization details
    organizer_contact = Column(String(255))
    organizer_email = Column(String(255))
    organizer_phone = Column(String(50))

    # Participation details
    participation_fee = Column(SQLDecimal(10, 2))
    currency = Column(String(3), default="RON")
    registration_deadline = Column(Date)
    max_participants = Column(Integer)

    # System fields
    status = Column(Enum(EventStatus), default=EventStatus.ANNOUNCED,
                   nullable=False, index=True)
    notes = Column(Text)

    # Source tracking
    anofm_url = Column(String(500))
    anofm_event_id = Column(String(100))
    last_scraped = Column(DateTime)

    # Relationships
    matches = relationship("WorkerEmployerMatch", back_populates="event")
    legal_compliance = relationship("LegalCompliance", back_populates="event")
    financial_tracking = relationship("FinancialTracking", back_populates="event")

    @validates('region')
    def validate_region(self, key, region):
        """Validate region is in target list."""
        target_regions = config.anofm.target_regions
        if region not in target_regions:
            # Log warning but don't fail - new regions might be added
            import logging
            logging.getLogger(__name__).warning(
                f"Region '{region}' not in target list: {target_regions}")
        return region

    def is_upcoming(self) -> bool:
        """Check if event is upcoming."""
        return self.date > date.today()

    def is_registration_open(self) -> bool:
        """Check if registration is still open."""
        if not self.registration_deadline:
            return self.is_upcoming()
        return date.today() <= self.registration_deadline

    def __repr__(self):
        return f"<ANOFMEvent(id={self.id}, name='{self.name}', date={self.date}, region='{self.region}')>"


class Worker(Base, BaseModel):
    """Romanian workers seeking EU employment."""
    __tablename__ = 'workers'

    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(50))

    # Location
    region = Column(String(100), nullable=False, index=True)
    city = Column(String(100))
    county = Column(String(100))

    # Professional information
    sector_experience = Column(String(100), index=True)
    years_experience = Column(Integer)
    education_level = Column(String(50))
    language_skills = Column(JSON)  # e.g., {"en": "B2", "de": "A1"}
    skills = Column(JSON)  # Array of skills

    # EU mobility preferences
    preferred_countries = Column(JSON)  # Array of country codes
    willing_to_relocate = Column(Boolean, default=True)
    family_size = Column(Integer, default=1)

    # System fields
    status = Column(Enum(WorkerStatus), default=WorkerStatus.REGISTERED,
                   nullable=False, index=True)
    notes = Column(Text)

    # GDPR compliance - CRITICAL
    gdpr_consent = Column(Boolean, default=False, nullable=False, index=True)
    gdpr_consent_date = Column(DateTime)
    gdpr_consent_version = Column(String(10), default="1.0")
    data_retention_until = Column(Date, nullable=False)
    consent_source = Column(String(100))  # web form, email, phone, etc.

    # Source tracking
    registration_source = Column(String(100))  # website, anofm, referral, etc.
    referral_code = Column(String(50))

    # Relationships
    matches = relationship("WorkerEmployerMatch", back_populates="worker")
    communications = relationship("Communication",
                                foreign_keys="Communication.recipient_id",
                                primaryjoin="and_(Worker.id==Communication.recipient_id, "
                                           "Communication.recipient_type=='worker')")

    def __init__(self, **kwargs):
        """Initialize worker with automatic data retention calculation."""
        super().__init__(**kwargs)
        if not self.data_retention_until:
            retention_days = config.gdpr.worker_data_retention_days
            self.data_retention_until = date.today() + timedelta(days=retention_days)

    @validates('gdpr_consent')
    def validate_gdpr_consent(self, key, consent):
        """Ensure GDPR consent is properly recorded."""
        if consent and not self.gdpr_consent_date:
            self.gdpr_consent_date = datetime.utcnow()
        return consent

    @validates('email')
    def validate_email(self, key, email):
        """Basic email validation."""
        if email and ('@' not in email or '.' not in email):
            raise ValueError("Invalid email format")
        return email.lower() if email else None

    def is_gdpr_compliant(self) -> bool:
        """Check if worker data is GDPR compliant."""
        return (self.gdpr_consent and
                self.gdpr_consent_date and
                self.data_retention_until > date.today())

    def days_until_retention_expiry(self) -> int:
        """Calculate days until data retention expiry."""
        if not self.data_retention_until:
            return 0
        return (self.data_retention_until - date.today()).days

    def __repr__(self):
        return f"<Worker(id={self.id}, name='{self.first_name} {self.last_name}', region='{self.region}')>"


class WorkerEmployerMatch(Base, BaseModel):
    """Connections between workers and employers."""
    __tablename__ = 'worker_employer_matches'

    # Foreign keys
    worker_id = Column(Integer, ForeignKey('workers.id'), nullable=False, index=True)
    employer_id = Column(Integer, ForeignKey('employers.id'), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey('anofm_events.id'), index=True)

    # Matching details
    match_stage = Column(Enum(MatchStage), default=MatchStage.IDENTIFIED,
                        nullable=False, index=True)
    match_score = Column(SQLDecimal(3, 2))  # 0.00 to 1.00
    match_criteria = Column(JSON)  # Criteria that created the match

    # Interview and placement
    interview_scheduled = Column(DateTime)
    interview_completed = Column(DateTime)
    interview_result = Column(String(100))

    placement_status = Column(String(50))
    placement_date = Column(Date)
    contract_start_date = Column(Date)
    contract_end_date = Column(Date)

    # Follow-up
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(Date)
    follow_up_completed = Column(Boolean, default=False)

    # System fields
    notes = Column(Text)

    # Job details
    job_title = Column(String(255))
    job_description = Column(Text)
    salary_offered = Column(SQLDecimal(10, 2))
    currency = Column(String(3), default="EUR")
    work_location = Column(String(255))

    # Relationships
    worker = relationship("Worker", back_populates="matches")
    employer = relationship("Employer", back_populates="matches")
    event = relationship("ANOFMEvent", back_populates="matches")

    @validates('match_score')
    def validate_match_score(self, key, score):
        """Validate match score is between 0 and 1."""
        if score is not None and (score < 0 or score > 1):
            raise ValueError("Match score must be between 0.00 and 1.00")
        return score

    def advance_stage(self, new_stage: MatchStage, notes: str = None) -> bool:
        """Advance match to next stage with validation."""
        stage_order = [
            MatchStage.IDENTIFIED,
            MatchStage.SCREENED,
            MatchStage.INTERVIEWED,
            MatchStage.OFFERED,
            MatchStage.ACCEPTED,
            MatchStage.PLACED
        ]

        current_index = stage_order.index(self.match_stage)
        new_index = stage_order.index(new_stage)

        # Allow backwards movement for corrections
        if new_index >= current_index - 1:
            self.match_stage = new_stage
            if notes:
                self.notes = f"{self.notes}\n{datetime.now()}: {notes}" if self.notes else notes
            return True
        return False

    def __repr__(self):
        return f"<WorkerEmployerMatch(id={self.id}, worker_id={self.worker_id}, employer_id={self.employer_id}, stage='{self.match_stage.value}')>"


class LegalCompliance(Base):
    """Legal compliance tracking for GDPR and employment law."""
    __tablename__ = 'legal_compliance'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Association
    event_id = Column(Integer, ForeignKey('anofm_events.id'), index=True)
    worker_id = Column(Integer, ForeignKey('workers.id'), index=True)
    employer_id = Column(Integer, ForeignKey('employers.id'), index=True)

    # Compliance details
    compliance_type = Column(Enum(ComplianceType), nullable=False, index=True)
    requirement = Column(String(255), nullable=False)
    description = Column(Text)

    # Verification
    status = Column(Enum(ComplianceStatus), default=ComplianceStatus.PENDING,
                   nullable=False, index=True)
    verified_by = Column(String(100))
    verified_date = Column(DateTime)
    expiration_date = Column(Date)

    # Documentation
    documents = Column(JSON)  # Array of document references
    external_reference = Column(String(100))  # External system reference

    # System fields
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    event = relationship("ANOFMEvent", back_populates="legal_compliance")

    def is_expired(self) -> bool:
        """Check if compliance has expired."""
        return (self.expiration_date and
                self.expiration_date < date.today())

    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until expiry."""
        if not self.expiration_date:
            return None
        return (self.expiration_date - date.today()).days

    def __repr__(self):
        return f"<LegalCompliance(id={self.id}, type='{self.compliance_type.value}', status='{self.status.value}')>"


class Communication(Base):
    """Email campaign and communication tracking."""
    __tablename__ = 'communications'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Recipient information
    recipient_type = Column(String(20), nullable=False, index=True)  # 'worker', 'employer'
    recipient_id = Column(Integer, nullable=False, index=True)
    recipient_email = Column(String(255), nullable=False)

    # Message details
    subject = Column(String(255), nullable=False)
    message_type = Column(Enum(MessageType), nullable=False)
    template_id = Column(String(50))
    content = Column(Text)

    # Sending details
    sent_date = Column(DateTime, index=True)
    status = Column(String(50), default="pending")  # pending, sent, failed, bounced
    provider = Column(String(50))  # brevo, gmail, etc.
    provider_message_id = Column(String(255))

    # Response tracking
    response_received = Column(Boolean, default=False)
    response_date = Column(DateTime)
    response_type = Column(String(50))  # reply, click, unsubscribe, etc.

    # Campaign tracking
    campaign_id = Column(String(100))
    campaign_phase = Column(String(50))  # pilot, scaling, full

    # System fields
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Additional tracking
    opens_count = Column(Integer, default=0)
    clicks_count = Column(Integer, default=0)
    last_opened = Column(DateTime)
    last_clicked = Column(DateTime)

    @validates('recipient_type')
    def validate_recipient_type(self, key, recipient_type):
        """Validate recipient type."""
        valid_types = ['worker', 'employer', 'anofm', 'system']
        if recipient_type not in valid_types:
            raise ValueError(f"Recipient type must be one of: {valid_types}")
        return recipient_type

    def mark_sent(self, provider_id: str = None, provider: str = "brevo"):
        """Mark communication as successfully sent."""
        self.status = "sent"
        self.sent_date = datetime.utcnow()
        self.provider = provider
        if provider_id:
            self.provider_message_id = provider_id

    def mark_failed(self, error_reason: str = None):
        """Mark communication as failed."""
        self.status = "failed"
        if error_reason:
            self.notes = f"{self.notes}\nFailed: {error_reason}" if self.notes else f"Failed: {error_reason}"

    def __repr__(self):
        return f"<Communication(id={self.id}, type='{self.message_type.value}', recipient='{self.recipient_type}:{self.recipient_id}')>"


class FinancialTracking(Base):
    """Payment and fee tracking for events and placements."""
    __tablename__ = 'financial_tracking'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Association
    event_id = Column(Integer, ForeignKey('anofm_events.id'), index=True)
    worker_id = Column(Integer, ForeignKey('workers.id'), index=True)
    employer_id = Column(Integer, ForeignKey('employers.id'), index=True)

    # Transaction details
    transaction_type = Column(Enum(TransactionType), nullable=False, index=True)
    amount = Column(SQLDecimal(10, 2), nullable=False)
    currency = Column(String(3), default="EUR", nullable=False)
    description = Column(Text)

    # Invoice and payment
    invoice_number = Column(String(100))
    invoice_date = Column(Date)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING,
                          nullable=False, index=True)
    payment_date = Column(Date)
    payment_method = Column(String(50))

    # External references
    external_transaction_id = Column(String(255))
    provider_reference = Column(String(255))

    # System fields
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    event = relationship("ANOFMEvent", back_populates="financial_tracking")

    @validates('amount')
    def validate_amount(self, key, amount):
        """Validate amount is positive."""
        if amount is not None and amount < 0:
            raise ValueError("Amount cannot be negative")
        return amount

    def is_overdue(self, days: int = 30) -> bool:
        """Check if payment is overdue."""
        if self.payment_status in [PaymentStatus.COMPLETED, PaymentStatus.REFUNDED]:
            return False

        if not self.invoice_date:
            return False

        overdue_date = self.invoice_date + timedelta(days=days)
        return date.today() > overdue_date

    def __repr__(self):
        return f"<FinancialTracking(id={self.id}, type='{self.transaction_type.value}', amount={self.amount} {self.currency})>"


# Create composite indexes for better performance
Index('idx_worker_employer_event', WorkerEmployerMatch.worker_id,
      WorkerEmployerMatch.employer_id, WorkerEmployerMatch.event_id)
Index('idx_communication_recipient', Communication.recipient_type,
      Communication.recipient_id, Communication.sent_date)
Index('idx_compliance_entity', LegalCompliance.compliance_type,
      LegalCompliance.status, LegalCompliance.expiration_date)
Index('idx_financial_entity', FinancialTracking.transaction_type,
      FinancialTracking.payment_status, FinancialTracking.created_at)