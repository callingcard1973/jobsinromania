"""
Legal Compliance Framework for GDPR and EU Employment Law.

This module provides comprehensive legal compliance management for the
European Employer ANOFM Job Fair Integration System, including:

- GDPR consent management and validation
- Data retention policies and enforcement
- EU employment law compliance tracking
- Legal document template generation
- Event-based compliance checklists
- Cross-border data transfer safeguards

Key Components:
- ComplianceManager: Main compliance validation and tracking
- DocumentTemplates: Legal document generation
- GDPRValidator: GDPR-specific compliance checking
- DataRetentionManager: Automatic data lifecycle management

Example Usage:
    from src.legal import ComplianceManager, DocumentTemplates

    # Initialize compliance manager
    compliance = ComplianceManager(session)

    # Validate worker GDPR compliance
    is_compliant = compliance.validate_worker_gdpr_consent(worker_id)

    # Generate compliance checklist for event
    checklist = compliance.generate_event_compliance_checklist(event_id)

    # Generate legal documents
    templates = DocumentTemplates()
    consent_form = templates.generate_gdpr_consent_form(worker_data)
"""

from .compliance import ComplianceManager, GDPRValidator, DataRetentionManager
from .templates import DocumentTemplates, ComplianceChecklist

__all__ = [
    'ComplianceManager',
    'GDPRValidator',
    'DataRetentionManager',
    'DocumentTemplates',
    'ComplianceChecklist'
]

__version__ = "1.0.0"