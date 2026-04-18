"""
European Employer ANOFM Job Fair Integration System

This package provides tools for integrating European employers into Romanian ANOFM
job fairs, focusing on regions with mass layoffs (Hunedoara, Gorj, Vaslui).

Main components:
- Database models for employers, workers, events, and compliance
- Email campaign management via Brevo API
- ANOFM website monitoring for job fair events
- GDPR-compliant data management and retention
- Legal compliance tracking and document management

The system operates in three phases:
1. Pilot: 1 employer, 10 workers, 30 days
2. Scaling: 5 employers, 50 workers, 60 days
3. Full deployment: 50+ employers, 500+ workers

Integration with existing infrastructure:
- Master database: PostgreSQL on raspibig (50M+ companies)
- Email system: Brevo API with 500 emails/day limit
- Monitoring: Telegram alerts via existing bot infrastructure
"""

__version__ = "1.0.0"
__author__ = "InterJob Romania"
__description__ = "European Employer ANOFM Job Fair Integration System"

from .database import Database, get_database
from config import get_config

__all__ = [
    "Database",
    "get_database",
    "get_config",
    "__version__",
    "__author__",
    "__description__"
]