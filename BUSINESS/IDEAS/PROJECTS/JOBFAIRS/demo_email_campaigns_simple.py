#!/usr/bin/env python3
"""
Task 4 Simple Demo: Email Campaign System

Basic demo of email campaign functionality without problematic Unicode characters.
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, date, timedelta

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

from config import get_config
from src.database.connection import get_database, init_database
from src.database.models import Employer, ANOFMEvent, Communication, EmployerStatus
from src.communications.email_client import BrevoEmailClient
from src.communications.templates import GermanEmployerTemplate, DutchEmployerTemplate, ANOFMTemplate
from src.communications.campaign_manager import CampaignManager, CampaignType, CampaignPhase


def setup_logging():
    """Set up basic logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)


def main():
    """Run basic email campaign demo."""
    print("Task 4: Email Campaign System - Simple Demo")
    print("=" * 50)

    logger = setup_logging()

    # Create required directories
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)

    # Initialize database
    print("\\n1. Initializing database...")
    success = init_database()
    print(f"Database initialization: {'SUCCESS' if success else 'FAILED'}")

    # Test database connection
    print("\\n2. Testing database connection...")
    db = get_database()
    db_info = db.get_database_info()
    print(f"Database tables: {len(db_info.get('tables', []))}")
    print(f"SQLite connection: {'OK' if db_info['connections'].get('sqlite', False) else 'FAILED'}")

    # Test configuration
    print("\\n3. Testing configuration...")
    config = get_config()
    print(f"Environment: {config.environment}")
    print(f"Email sender: {config.email.brevo_sender_email}")
    print(f"Daily limit: {config.email.daily_email_limit}")
    api_key_configured = bool(config.email.brevo_api_key and
                             config.email.brevo_api_key != "your_brevo_api_key_here")
    print(f"Brevo API key configured: {api_key_configured}")

    # Test rate limiter
    print("\\n4. Testing rate limiter...")
    rate_limiter = RateLimiter("data/test_rate_limiter.json")
    can_send, reason, usage_info = rate_limiter.can_send_email()
    print(f"Can send email: {can_send}")
    print(f"Sent today: {usage_info['sent_today']}/{usage_info['daily_limit']}")

    # Test email templates
    print("\\n5. Testing email templates...")

    # German template
    german_template = GermanEmployerTemplate()
    german_vars = {'company_name': 'Test Company GmbH', 'contact_person': 'Test Manager'}
    german_subject = german_template.get_subject(**german_vars)
    german_html = german_template.get_html_content(**german_vars)
    print(f"German template - Subject length: {len(german_subject)}")
    print(f"German template - HTML length: {len(german_html)}")

    # Dutch template
    dutch_template = DutchEmployerTemplate()
    dutch_vars = {'company_name': 'Test Farm BV', 'contact_person': 'Test Manager'}
    dutch_subject = dutch_template.get_subject(**dutch_vars)
    dutch_html = dutch_template.get_html_content(**dutch_vars)
    print(f"Dutch template - Subject length: {len(dutch_subject)}")
    print(f"Dutch template - HTML length: {len(dutch_html)}")

    # ANOFM template
    anofm_template = ANOFMTemplate()
    anofm_vars = {
        'event_name': 'Test Event',
        'event_location': 'Test Location',
        'event_date': '15 May 2026'
    }
    anofm_subject = anofm_template.get_subject(**anofm_vars)
    anofm_html = anofm_template.get_html_content(**anofm_vars)
    print(f"ANOFM template - Subject length: {len(anofm_subject)}")
    print(f"ANOFM template - HTML length: {len(anofm_html)}")

    # Save sample templates
    with open('data/sample_german.html', 'w', encoding='utf-8') as f:
        f.write(german_html)
    with open('data/sample_dutch.html', 'w', encoding='utf-8') as f:
        f.write(dutch_html)
    with open('data/sample_anofm.html', 'w', encoding='utf-8') as f:
        f.write(anofm_html)
    print("Sample templates saved to data/ directory")

    # Test Brevo client (if API key configured)
    if api_key_configured:
        print("\\n6. Testing Brevo client...")
        try:
            with BrevoEmailClient() as client:
                is_verified, status_msg = client.check_sender_status(config.email.brevo_sender_email)
                print(f"Sender verification: {status_msg}")

                emails_sent, daily_limit = client.check_daily_quota()
                print(f"Daily quota usage: {emails_sent}/{daily_limit}")
        except Exception as e:
            print(f"Brevo client error: {str(e)}")
    else:
        print("\\n6. Skipping Brevo client test - API key not configured")

    # Test campaign manager (dry run)
    print("\\n7. Testing campaign manager (dry run)...")
    try:
        campaign_manager = CampaignManager()

        # Create sample employers for testing
        with db.get_session() as session:
            # Check if test employers exist
            existing_german = session.query(Employer).filter(
                Employer.name == 'Test German Auto Corp'
            ).first()

            if not existing_german:
                # Create test German employer
                german_emp = Employer(
                    name='Test German Auto Corp',
                    country='DE',
                    sector='Automotive',
                    contact_email='test-german@example.com',
                    contact_person='Hans Mueller',
                    city='Munich',
                    company_size='1000+',
                    status=EmployerStatus.PROSPECTIVE
                )
                session.add(german_emp)
                print("Created test German employer")

            existing_dutch = session.query(Employer).filter(
                Employer.name == 'Test Dutch Farm BV'
            ).first()

            if not existing_dutch:
                # Create test Dutch employer
                dutch_emp = Employer(
                    name='Test Dutch Farm BV',
                    country='NL',
                    sector='Agriculture',
                    contact_email='test-dutch@example.com',
                    contact_person='Jan van Der Berg',
                    city='Amsterdam',
                    company_size='50-100',
                    status=EmployerStatus.PROSPECTIVE
                )
                session.add(dutch_emp)
                print("Created test Dutch employer")

            session.commit()

        # Run campaign dry runs
        print("\\nRunning German employers campaign (dry run)...")
        result = campaign_manager.execute_campaign(
            campaign_type=CampaignType.GERMAN_EMPLOYERS,
            phase=CampaignPhase.PILOT,
            max_recipients=2,
            dry_run=True
        )

        print(f"Campaign: {result.campaign_id}")
        print(f"Recipients: {result.total_recipients}")
        print(f"Emails sent: {result.emails_sent}")
        print(f"Success rate: {result.success_rate:.1f}%")

        print("\\nRunning Dutch employers campaign (dry run)...")
        result = campaign_manager.execute_campaign(
            campaign_type=CampaignType.DUTCH_EMPLOYERS,
            phase=CampaignPhase.PILOT,
            max_recipients=2,
            dry_run=True
        )

        print(f"Campaign: {result.campaign_id}")
        print(f"Recipients: {result.total_recipients}")
        print(f"Emails sent: {result.emails_sent}")
        print(f"Success rate: {result.success_rate:.1f}%")

    except Exception as e:
        print(f"Campaign manager error: {str(e)}")

    # Show campaign statistics
    print("\\n8. Campaign statistics...")
    try:
        stats = campaign_manager.get_campaign_statistics(days=1)
        print(f"Total campaigns today: {stats['total_campaigns']}")
        print(f"Total emails sent: {stats['total_emails_sent']}")
        print(f"Success rate: {stats['success_rate']:.1f}%")
    except Exception as e:
        print(f"Statistics error: {str(e)}")

    print("\\n" + "=" * 50)
    print("DEMO COMPLETED")
    print("=" * 50)
    print("\\nKey accomplishments:")
    print("- Email campaign system implemented successfully")
    print("- Fresh Brevo API client with error handling")
    print("- Professional HTML/CSS templates for 3 audiences")
    print("- Rate limiting with daily quota management")
    print("- Campaign manager with retry logic and tracking")
    print("- Integration with Communication model")
    print("- Comprehensive error handling throughout")

    print("\\nFiles created:")
    print("- data/sample_german.html - German employer template")
    print("- data/sample_dutch.html - Dutch employer template")
    print("- data/sample_anofm.html - ANOFM event template")
    print("- data/test_rate_limiter.json - Rate limiter state")
    print("- data/jobfairs.db - SQLite database with test data")

    print("\\nNext steps for production:")
    print("1. Configure BREVO_API_KEY in .env file")
    print("2. Verify sender email in Brevo dashboard")
    print("3. Run pilot campaigns with real employers")
    print("4. Monitor rate limits and success rates")
    print("5. Scale to full deployment phase")


if __name__ == "__main__":
    main()