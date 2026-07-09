"""
Legal Compliance Manager for GDPR and EU Employment Law.

This module provides comprehensive compliance management including:
- GDPR consent validation and tracking
- Data retention policy enforcement
- Event compliance checklist generation
- Cross-border data transfer compliance
- Automatic data anonymization procedures
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database.models import (
    Worker, Employer, ANOFMEvent, LegalCompliance,
    WorkerEmployerMatch, Communication,
    ComplianceType, ComplianceStatus, WorkerStatus
)
from config import get_config

logger = logging.getLogger(__name__)


class ComplianceCategory(Enum):
    """8-category compliance framework for ANOFM events."""
    GDPR_CONSENT = "gdpr_consent"
    DATA_SHARING_AGREEMENTS = "data_sharing_agreements"
    EMPLOYER_VETTING = "employer_vetting"
    EMPLOYMENT_CONTRACTS = "employment_contracts"
    DATA_RETENTION_POLICIES = "data_retention_policies"
    CROSS_BORDER_TRANSFERS = "cross_border_transfers"
    WORKER_RIGHTS_INFO = "worker_rights_info"
    ANOFM_REGULATORY = "anofm_regulatory"


@dataclass
class ComplianceResult:
    """Result of a compliance check."""
    compliant: bool
    issues: List[str]
    warnings: List[str]
    expiry_date: Optional[date] = None
    next_review_date: Optional[date] = None


@dataclass
class EventComplianceStatus:
    """Compliance status for an entire event."""
    event_id: int
    total_categories: int
    compliant_categories: int
    completion_percentage: float
    critical_issues: List[str]
    pending_items: List[str]
    next_deadline: Optional[date] = None


class GDPRValidator:
    """GDPR-specific compliance validation."""

    def __init__(self, config):
        self.config = config
        self.consent_validity_days = 730  # 2 years as per GDPR

    def validate_worker_consent(self, worker: Worker) -> ComplianceResult:
        """Validate worker's GDPR consent status."""
        issues = []
        warnings = []

        # Check if consent is given
        if not worker.gdpr_consent:
            issues.append("GDPR consent not provided")

        # Check if consent date is recorded
        if worker.gdpr_consent and not worker.gdpr_consent_date:
            issues.append("GDPR consent date not recorded")

        # Check if consent is still valid (within 2 years)
        if worker.gdpr_consent_date:
            consent_age = (datetime.now() - worker.gdpr_consent_date).days
            if consent_age > self.consent_validity_days:
                issues.append(f"GDPR consent expired ({consent_age} days old, max {self.consent_validity_days})")
            elif consent_age > (self.consent_validity_days - 90):
                warnings.append(f"GDPR consent expires soon ({self.consent_validity_days - consent_age} days remaining)")

        # Check data retention period
        if worker.data_retention_until and worker.data_retention_until <= date.today():
            issues.append("Data retention period expired")

        # Calculate expiry dates
        expiry_date = None
        if worker.gdpr_consent_date:
            expiry_date = (worker.gdpr_consent_date + timedelta(days=self.consent_validity_days)).date()

        next_review_date = None
        if worker.data_retention_until:
            # Review 30 days before expiry
            next_review_date = worker.data_retention_until - timedelta(days=30)

        return ComplianceResult(
            compliant=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            expiry_date=expiry_date,
            next_review_date=next_review_date
        )

    def identify_expired_consent(self, session: Session) -> List[Worker]:
        """Identify workers with expired GDPR consent."""
        cutoff_date = datetime.now() - timedelta(days=self.consent_validity_days)

        return session.query(Worker).filter(
            and_(
                Worker.gdpr_consent == True,
                Worker.gdpr_consent_date <= cutoff_date
            )
        ).all()

    def get_expiring_consent(self, session: Session, days_ahead: int = 90) -> List[Worker]:
        """Get workers whose consent expires soon."""
        start_date = datetime.now() + timedelta(days=days_ahead - 30)
        end_date = datetime.now() + timedelta(days=days_ahead)

        return session.query(Worker).filter(
            and_(
                Worker.gdpr_consent == True,
                Worker.gdpr_consent_date.between(
                    start_date - timedelta(days=self.consent_validity_days),
                    end_date - timedelta(days=self.consent_validity_days)
                )
            )
        ).all()


class DataRetentionManager:
    """Automatic data retention and anonymization management."""

    def __init__(self, config):
        self.config = config

    def identify_expired_data(self, session: Session) -> Dict[str, List]:
        """Identify all data subject to retention expiry."""
        today = date.today()

        expired_data = {
            'workers': session.query(Worker).filter(Worker.data_retention_until <= today).all(),
            'employers': session.query(Employer).filter(Employer.data_retention_until <= today).all(),
            'communications': []  # Will be added if Communication model has retention field
        }

        return expired_data

    def anonymize_worker_data(self, session: Session, worker_id: int) -> bool:
        """Anonymize expired worker data while preserving audit trail."""
        worker = session.query(Worker).filter(Worker.id == worker_id).first()
        if not worker:
            logger.error(f"Worker {worker_id} not found for anonymization")
            return False

        if worker.data_retention_until > date.today():
            logger.warning(f"Worker {worker_id} data retention not yet expired")
            return False

        # Store original data in notes for audit
        original_data = {
            'first_name': worker.first_name,
            'last_name': worker.last_name,
            'email': worker.email,
            'phone': worker.phone,
            'anonymized_at': datetime.now().isoformat()
        }

        # Anonymize PII fields
        worker.first_name = f"ANONYMIZED_{worker.id:05d}"
        worker.last_name = "USER"
        worker.email = f"anonymized_{worker.id}@example.com"
        worker.phone = None
        worker.notes = f"ANONYMIZED: {json.dumps(original_data)}"
        worker.status = WorkerStatus.INACTIVE

        session.flush()
        logger.info(f"Anonymized worker {worker_id} data")
        return True

    def get_retention_summary(self, session: Session) -> Dict[str, Any]:
        """Get comprehensive data retention summary."""
        today = date.today()
        next_30_days = today + timedelta(days=30)

        summary = {
            'expired_workers': session.query(Worker).filter(Worker.data_retention_until <= today).count(),
            'expiring_workers_30d': session.query(Worker).filter(
                and_(Worker.data_retention_until > today, Worker.data_retention_until <= next_30_days)
            ).count(),
            'expired_employers': session.query(Employer).filter(Employer.data_retention_until <= today).count(),
            'expiring_employers_30d': session.query(Employer).filter(
                and_(Employer.data_retention_until > today, Employer.data_retention_until <= next_30_days)
            ).count(),
            'last_check': datetime.now().isoformat()
        }

        return summary


class ComplianceManager:
    """Main legal compliance management class."""

    def __init__(self, session: Session):
        self.session = session
        self.config = get_config()
        self.gdpr_validator = GDPRValidator(self.config)
        self.retention_manager = DataRetentionManager(self.config)

    def validate_worker_gdpr_consent(self, worker_id: int) -> bool:
        """Validate worker GDPR consent with date checks."""
        worker = self.session.query(Worker).filter(Worker.id == worker_id).first()
        if not worker:
            logger.error(f"Worker {worker_id} not found")
            return False

        result = self.gdpr_validator.validate_worker_consent(worker)
        return result.compliant

    def identify_expired_data_subjects(self, anonymize: bool = False) -> Dict[str, List]:
        """Identify expired data subject and optionally anonymize."""
        expired_data = self.retention_manager.identify_expired_data(self.session)

        if anonymize:
            # Anonymize expired worker data
            for worker in expired_data['workers']:
                self.retention_manager.anonymize_worker_data(self.session, worker.id)

        return expired_data

    def create_compliance_record(self,
                               compliance_type: ComplianceType,
                               requirement: str,
                               event_id: Optional[int] = None,
                               worker_id: Optional[int] = None,
                               employer_id: Optional[int] = None,
                               status: ComplianceStatus = ComplianceStatus.PENDING,
                               expiration_date: Optional[date] = None) -> LegalCompliance:
        """Create a new compliance tracking record."""
        compliance = LegalCompliance(
            event_id=event_id,
            worker_id=worker_id,
            employer_id=employer_id,
            compliance_type=compliance_type,
            requirement=requirement,
            status=status,
            expiration_date=expiration_date
        )

        self.session.add(compliance)
        self.session.flush()
        logger.info(f"Created compliance record {compliance.id} for {compliance_type.value}")
        return compliance

    def update_compliance_status(self,
                                compliance_id: int,
                                status: ComplianceStatus,
                                verified_by: str,
                                documents: Optional[List[str]] = None,
                                notes: Optional[str] = None) -> bool:
        """Update compliance record status and verification."""
        compliance = self.session.query(LegalCompliance).filter(
            LegalCompliance.id == compliance_id
        ).first()

        if not compliance:
            logger.error(f"Compliance record {compliance_id} not found")
            return False

        compliance.status = status
        compliance.verified_by = verified_by
        compliance.verified_date = datetime.now()

        if documents:
            compliance.documents = documents

        if notes:
            compliance.notes = f"{compliance.notes}\n{notes}" if compliance.notes else notes

        self.session.flush()
        logger.info(f"Updated compliance record {compliance_id} to {status.value}")
        return True

    def generate_event_compliance_checklist(self, event_id: int) -> Dict[str, Any]:
        """Generate 8-category compliance checklist for an event."""
        event = self.session.query(ANOFMEvent).filter(ANOFMEvent.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        # Define compliance requirements for each category
        compliance_categories = {
            ComplianceCategory.GDPR_CONSENT: {
                "requirements": [
                    "Worker GDPR consent forms collected",
                    "Consent dates properly recorded",
                    "Consent version tracking in place",
                    "Withdrawal mechanisms available"
                ],
                "status": "pending"
            },
            ComplianceCategory.DATA_SHARING_AGREEMENTS: {
                "requirements": [
                    "Data sharing agreements with employers",
                    "Cross-border transfer safeguards",
                    "Third-party processor agreements",
                    "Data security requirements defined"
                ],
                "status": "pending"
            },
            ComplianceCategory.EMPLOYER_VETTING: {
                "requirements": [
                    "Employer registration verification",
                    "Business license validation",
                    "Previous compliance history check",
                    "Financial stability assessment"
                ],
                "status": "pending"
            },
            ComplianceCategory.EMPLOYMENT_CONTRACTS: {
                "requirements": [
                    "EU-compliant employment contracts",
                    "Salary and benefits disclosure",
                    "Working conditions specification",
                    "Termination clauses compliance"
                ],
                "status": "pending"
            },
            ComplianceCategory.DATA_RETENTION_POLICIES: {
                "requirements": [
                    "Data retention periods defined",
                    "Automatic deletion procedures",
                    "Audit trail maintenance",
                    "Anonymization protocols"
                ],
                "status": "pending"
            },
            ComplianceCategory.CROSS_BORDER_TRANSFERS: {
                "requirements": [
                    "Adequacy decisions verified",
                    "Standard contractual clauses",
                    "Binding corporate rules compliance",
                    "Transfer impact assessments"
                ],
                "status": "pending"
            },
            ComplianceCategory.WORKER_RIGHTS_INFO: {
                "requirements": [
                    "Worker rights information provided",
                    "Complaint procedures established",
                    "Legal aid contact information",
                    "Trade union rights disclosure"
                ],
                "status": "pending"
            },
            ComplianceCategory.ANOFM_REGULATORY: {
                "requirements": [
                    "ANOFM registration compliance",
                    "Reporting requirements met",
                    "Fee payment verification",
                    "Documentation submission complete"
                ],
                "status": "pending"
            }
        }

        # Check existing compliance records for this event
        existing_compliance = self.session.query(LegalCompliance).filter(
            LegalCompliance.event_id == event_id
        ).all()

        # Update statuses based on existing records
        for compliance in existing_compliance:
            category_key = None
            # Map compliance types to categories
            if compliance.compliance_type == ComplianceType.GDPR_CONSENT:
                category_key = ComplianceCategory.GDPR_CONSENT
            elif compliance.compliance_type == ComplianceType.LABOR_CONTRACT:
                category_key = ComplianceCategory.EMPLOYMENT_CONTRACTS
            elif compliance.compliance_type == ComplianceType.ANOFM_REGISTRATION:
                category_key = ComplianceCategory.ANOFM_REGULATORY

            if category_key and category_key in compliance_categories:
                compliance_categories[category_key]["status"] = compliance.status.value
                compliance_categories[category_key]["verified_by"] = compliance.verified_by
                compliance_categories[category_key]["verified_date"] = compliance.verified_date.isoformat() if compliance.verified_date else None

        # Calculate completion statistics
        total_categories = len(compliance_categories)
        compliant_categories = sum(1 for cat in compliance_categories.values()
                                 if cat["status"] == "verified")
        completion_percentage = (compliant_categories / total_categories) * 100

        return {
            "event_id": event_id,
            "event_name": event.name,
            "event_date": event.date.isoformat(),
            "compliance_categories": {cat.value: data for cat, data in compliance_categories.items()},
            "summary": {
                "total_categories": total_categories,
                "compliant_categories": compliant_categories,
                "completion_percentage": completion_percentage,
                "status": "complete" if completion_percentage == 100 else "in_progress"
            },
            "generated_at": datetime.now().isoformat()
        }

    def get_event_compliance_status(self, event_id: int) -> EventComplianceStatus:
        """Get comprehensive compliance status for an event."""
        checklist = self.generate_event_compliance_checklist(event_id)

        critical_issues = []
        pending_items = []
        next_deadline = None

        for category, data in checklist["compliance_categories"].items():
            if data["status"] == "rejected":
                critical_issues.append(f"{category}: Compliance rejected")
            elif data["status"] == "pending":
                pending_items.extend([f"{category}: {req}" for req in data["requirements"]])

        # Find next deadline from compliance records
        compliance_records = self.session.query(LegalCompliance).filter(
            and_(
                LegalCompliance.event_id == event_id,
                LegalCompliance.expiration_date.isnot(None),
                LegalCompliance.expiration_date > date.today()
            )
        ).order_by(LegalCompliance.expiration_date).first()

        if compliance_records:
            next_deadline = compliance_records.expiration_date

        return EventComplianceStatus(
            event_id=event_id,
            total_categories=checklist["summary"]["total_categories"],
            compliant_categories=checklist["summary"]["compliant_categories"],
            completion_percentage=checklist["summary"]["completion_percentage"],
            critical_issues=critical_issues,
            pending_items=pending_items,
            next_deadline=next_deadline
        )

    def get_compliance_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive compliance dashboard."""
        today = date.today()

        # GDPR compliance summary
        gdpr_expired = self.gdpr_validator.identify_expired_consent(self.session)
        gdpr_expiring = self.gdpr_validator.get_expiring_consent(self.session)

        # Data retention summary
        retention_summary = self.retention_manager.get_retention_summary(self.session)

        # Event compliance summary
        active_events = self.session.query(ANOFMEvent).filter(
            ANOFMEvent.date >= today
        ).all()

        event_compliance = []
        for event in active_events:
            status = self.get_event_compliance_status(event.id)
            event_compliance.append({
                "event_id": event.id,
                "event_name": event.name,
                "event_date": event.date.isoformat(),
                "completion_percentage": status.completion_percentage,
                "critical_issues_count": len(status.critical_issues)
            })

        # Overall compliance score calculation
        total_workers = self.session.query(Worker).filter(Worker.gdpr_consent == True).count()
        compliant_workers = total_workers - len(gdpr_expired)
        worker_compliance_rate = (compliant_workers / total_workers * 100) if total_workers > 0 else 100

        avg_event_compliance = (
            sum(event["completion_percentage"] for event in event_compliance) /
            len(event_compliance)
        ) if event_compliance else 100

        overall_score = (worker_compliance_rate + avg_event_compliance) / 2

        return {
            "overall_compliance_score": round(overall_score, 2),
            "gdpr_compliance": {
                "expired_consent_count": len(gdpr_expired),
                "expiring_consent_count": len(gdpr_expiring),
                "worker_compliance_rate": round(worker_compliance_rate, 2)
            },
            "data_retention": retention_summary,
            "event_compliance": event_compliance,
            "alerts": {
                "critical_count": len(gdpr_expired) + retention_summary["expired_workers"],
                "warning_count": len(gdpr_expiring) + retention_summary["expiring_workers_30d"]
            },
            "last_updated": datetime.now().isoformat()
        }