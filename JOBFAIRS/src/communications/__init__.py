"""
Email campaign system for European Employer ANOFM Job Fair Integration.

This module provides comprehensive email campaign functionality including:
- Brevo API integration with fresh client architecture
- Professional HTML templates for employer and ANOFM outreach
- Rate limiting and daily quota management
- Campaign tracking and bounce handling
- Retry mechanisms with exponential backoff
- GDPR compliant communication logging

All email campaigns follow existing infrastructure patterns and integrate
seamlessly with the Communication model for comprehensive tracking.
"""

from .email_client import BrevoEmailClient
from .templates import (
    EmailTemplate,
    GermanEmployerTemplate,
    DutchEmployerTemplate,
    ANOFMTemplate
)
from .campaign_manager import CampaignManager

__all__ = [
    'BrevoEmailClient',
    'EmailTemplate',
    'GermanEmployerTemplate',
    'DutchEmployerTemplate',
    'ANOFMTemplate',
    'CampaignManager'
]