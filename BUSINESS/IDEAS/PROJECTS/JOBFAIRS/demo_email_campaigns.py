#!/usr/bin/env python3
"""
Task 4 Demo: Email Campaign System for European Employer ANOFM Job Fair Integration

This demo showcases the complete email campaign functionality including:
- Fresh Brevo API client integration
- Professional HTML/CSS templates for German/Dutch employers and ANOFM events
- Rate limiting with daily quota management (500/day)
- Campaign management with retry logic and bounce handling
- Comprehensive error handling and logging
- Integration with Communication model for tracking

IMPORTANT: Set BREVO_API_KEY in .env file before running campaigns!
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, date, timedelta

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / 'src'))

from config import get_config
from src.database.connection import get_database
from src.database.models import Employer, ANOFMEvent, Communication, EmployerStatus
from src.communications.email_client import BrevoEmailClient
from src.communications.templates import GermanEmployerTemplate, DutchEmployerTemplate, ANOFMTemplate
from src.communications.campaign_manager import CampaignManager, CampaignType, CampaignPhase


def setup_logging():
    """Set up comprehensive logging for demo."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/email_campaigns_demo.log')
        ]
    )
    return logging.getLogger(__name__)


def demo_brevo_client():
    """Demo 1: Brevo Email Client functionality."""
    print("=" * 80)
    print("DEMO 1: BREVO EMAIL CLIENT")
    print("=" * 80)

    try:
        # Initialize client
        print("\\n1. Initializing Brevo client...")
        with BrevoEmailClient() as client:
            print(f"✓ Client initialized successfully")

            # Check sender status
            print("\\n2. Checking sender email verification...")
            config = get_config()
            is_verified, status_msg = client.check_sender_status(config.email.brevo_sender_email)
            print(f"Sender status: {status_msg}")

            # Check account info and quota
            print("\\n3. Checking account information...")
            account_info = client.get_account_info()
            if "error" not in account_info:
                plan_type = account_info.get('plan', {}).get('type', 'Unknown')
                print(f"✓ Account verified - Plan: {plan_type}")

                # Check daily quota
                emails_sent, daily_limit = client.check_daily_quota()
                print(f"✓ Daily quota: {emails_sent}/{daily_limit} emails used")
            else:
                print(f"⚠ Account check warning: {account_info['error']}")

            # Demo template preview (without sending)
            print("\\n4. Generating email templates...")
            german_template = GermanEmployerTemplate()
            sample_vars = {
                'company_name': 'Volkswagen AG',
                'contact_person': 'Hans Mueller'
            }

            subject = german_template.get_subject(**sample_vars)
            print(f"✓ German template subject: {subject}")

            dutch_template = DutchEmployerTemplate()
            dutch_vars = {
                'company_name': 'AgriCorp Netherlands',
                'contact_person': 'Jan van der Berg'
            }

            dutch_subject = dutch_template.get_subject(**dutch_vars)
            print(f"✓ Dutch template subject: {dutch_subject}")

            anofm_template = ANOFMTemplate()
            anofm_vars = {
                'event_name': 'Bursa de Muncă Hunedoara',
                'event_location': 'Hunedoara',
                'event_date': '15 Mai 2026'
            }

            anofm_subject = anofm_template.get_subject(**anofm_vars)
            print(f"✓ ANOFM template subject: {anofm_subject}")

        print("\\n✓ Brevo client demo completed successfully!")

    except Exception as e:
        print(f"✗ Brevo client demo failed: {str(e)}")
        return False

    return True


def demo_rate_limiter():
    """Demo 2: Rate Limiter functionality."""
    print("\\n" + "=" * 80)
    print("DEMO 2: RATE LIMITER")
    print("=" * 80)

    try:
        # Initialize rate limiter
        print("\\n1. Initializing rate limiter...")
        rate_limiter = RateLimiter("data/demo_rate_limiter.json")
        print(f"✓ Rate limiter initialized: {rate_limiter}")

        # Check current status
        print("\\n2. Checking current usage...")
        can_send, reason, usage_info = rate_limiter.can_send_email()
        print(f"Can send email: {can_send}")
        print(f"Reason: {reason}")
        print(f"Usage info: {usage_info}")

        # Simulate sending emails
        print("\\n3. Simulating email sends...")
        for i in range(5):
            rate_limiter.record_email_attempt()
            if i < 4:  # Success for first 4
                rate_limiter.record_successful_send()
                print(f"  Email {i + 1}: ✓ Successful")
            else:  # Failure for last one
                rate_limiter.record_failed_send("Bounce detected")
                print(f"  Email {i + 1}: ✗ Failed (bounce)")

        # Check updated status
        print("\\n4. Checking updated usage...")
        stats = rate_limiter.get_usage_stats()
        print(f"Today's stats:")
        print(f"  Successful sends: {stats['today']['successful_sends']}")
        print(f"  Failed attempts: {stats['today']['failed_attempts']}")
        print(f"  Success rate: {stats['today']['percentage_used']:.1f}%")
        print(f"  Remaining: {stats['today']['remaining']}")

        # Check approaching limit
        approaching = rate_limiter.is_approaching_limit(80.0)
        print(f"Approaching limit (80%): {approaching}")

        # Time until reset
        reset_time = rate_limiter.get_time_until_reset()
        print(f"Time until reset: {reset_time}")

        print("\\n✓ Rate limiter demo completed successfully!")

    except Exception as e:
        print(f"✗ Rate limiter demo failed: {str(e)}")
        return False

    return True


def demo_templates():
    """Demo 3: Email Templates with HTML generation."""
    print("\\n" + "=" * 80)
    print("DEMO 3: EMAIL TEMPLATES")
    print("=" * 80)

    try:
        print("\\n1. Testing German Employer Template...")
        german_template = GermanEmployerTemplate()
        german_vars = {
            'company_name': 'Mercedes-Benz AG',
            'contact_person': 'Dr. Klaus Weber',
            'website': 'https://www.mercedes-benz.com'
        }

        german_html = german_template.get_html_content(**german_vars)
        german_text = german_template.get_text_content(**german_vars)

        print(f"✓ German HTML length: {len(german_html)} characters")
        print(f"✓ German text length: {len(german_text)} characters")
        print(f"✓ Subject: {german_template.get_subject(**german_vars)}")

        # Save sample HTML for review
        with open('data/sample_german_email.html', 'w', encoding='utf-8') as f:
            f.write(german_html)
        print("✓ Sample German HTML saved to data/sample_german_email.html")

        print("\\n2. Testing Dutch Employer Template...")
        dutch_template = DutchEmployerTemplate()
        dutch_vars = {
            'company_name': 'Royal Flora Holland',
            'contact_person': 'Pieter van Amsterdam',
            'website': 'https://www.royalfloraholland.com'
        }

        dutch_html = dutch_template.get_html_content(**dutch_vars)
        dutch_text = dutch_template.get_text_content(**dutch_vars)

        print(f"✓ Dutch HTML length: {len(dutch_html)} characters")
        print(f"✓ Dutch text length: {len(dutch_text)} characters")
        print(f"✓ Subject: {dutch_template.get_subject(**dutch_vars)}")

        # Save sample HTML for review
        with open('data/sample_dutch_email.html', 'w', encoding='utf-8') as f:
            f.write(dutch_html)
        print("✓ Sample Dutch HTML saved to data/sample_dutch_email.html")

        print("\\n3. Testing ANOFM Template...")
        anofm_template = ANOFMTemplate()
        anofm_vars = {
            'event_name': 'Bursa Generală de Muncă Hunedoara',
            'event_location': 'Hunedoara, jud. Hunedoara',
            'event_date': '15 Mai 2026',
            'organizer_contact': 'Maria Popescu'
        }

        anofm_html = anofm_template.get_html_content(**anofm_vars)
        anofm_text = anofm_template.get_text_content(**anofm_vars)

        print(f"✓ ANOFM HTML length: {len(anofm_html)} characters")
        print(f"✓ ANOFM text length: {len(anofm_text)} characters")
        print(f"✓ Subject: {anofm_template.get_subject(**anofm_vars)}")

        # Save sample HTML for review
        with open('data/sample_anofm_email.html', 'w', encoding='utf-8') as f:
            f.write(anofm_html)
        print("✓ Sample ANOFM HTML saved to data/sample_anofm_email.html")

        print("\\n✓ Template demo completed successfully!")

    except Exception as e:
        print(f"✗ Template demo failed: {str(e)}")
        return False

    return True


def demo_database_integration():
    """Demo 4: Database integration with existing employers and events."""
    print("\\n" + "=" * 80)
    print("DEMO 4: DATABASE INTEGRATION")
    print("=" * 80)

    try:
        db = get_database()

        print("\\n1. Checking existing employers...")
        with db.get_session() as session:
            # German automotive employers
            german_employers = session.query(Employer).filter(
                Employer.country == 'DE',
                Employer.sector == 'Automotive'
            ).limit(5).all()

            print(f"German automotive employers: {len(german_employers)}")
            for emp in german_employers[:3]:
                print(f"  - {emp.name} ({emp.contact_email})")

            # Dutch agricultural employers
            dutch_employers = session.query(Employer).filter(
                Employer.country == 'NL',
                Employer.sector == 'Agriculture'
            ).limit(5).all()

            print(f"\\nDutch agricultural employers: {len(dutch_employers)}")
            for emp in dutch_employers[:3]:
                print(f"  - {emp.name} ({emp.contact_email})")

        print("\\n2. Creating sample ANOFM events...")
        campaign_manager = CampaignManager()
        created, existing = campaign_manager.create_sample_data()
        print(f"✓ ANOFM events created: {created}, existing: {existing}")

        print("\\n3. Checking ANOFM events...")
        with db.get_session() as session:
            events = session.query(ANOFMEvent).filter(
                ANOFMEvent.date >= date.today()
            ).limit(5).all()

            print(f"Upcoming ANOFM events: {len(events)}")
            for event in events[:3]:
                print(f"  - {event.name} on {event.date} ({event.organizer_email})")

        print("\\n4. Checking communication history...")
        with db.get_session() as session:
            recent_communications = session.query(Communication).order_by(
                Communication.created_at.desc()
            ).limit(5).all()

            print(f"Recent communications: {len(recent_communications)}")
            for comm in recent_communications[:3]:
                print(f"  - {comm.message_type.value} to {comm.recipient_email} ({comm.status})")

        print("\\n✓ Database integration demo completed successfully!")

    except Exception as e:
        print(f"✗ Database integration demo failed: {str(e)}")
        return False

    return True


def demo_campaign_manager():
    """Demo 5: Complete Campaign Manager functionality."""
    print("\\n" + "=" * 80)
    print("DEMO 5: CAMPAIGN MANAGER (DRY RUN)")
    print("=" * 80)

    try:
        campaign_manager = CampaignManager()

        # Demo German employers campaign (dry run)
        print("\\n1. Running German employers campaign (dry run)...")
        result = campaign_manager.execute_campaign(
            campaign_type=CampaignType.GERMAN_EMPLOYERS,
            phase=CampaignPhase.PILOT,
            max_recipients=3,
            dry_run=True
        )

        print(f"✓ Campaign completed: {result.campaign_id}")
        print(f"  Recipients: {result.total_recipients}")
        print(f"  Sent: {result.emails_sent}")
        print(f"  Failed: {result.emails_failed}")
        print(f"  Success rate: {result.success_rate:.1f}%")
        print(f"  Duration: {result.duration_minutes:.2f} minutes")

        # Demo Dutch employers campaign (dry run)
        print("\\n2. Running Dutch employers campaign (dry run)...")
        result = campaign_manager.execute_campaign(
            campaign_type=CampaignType.DUTCH_EMPLOYERS,
            phase=CampaignPhase.PILOT,
            max_recipients=2,
            dry_run=True
        )

        print(f"✓ Campaign completed: {result.campaign_id}")
        print(f"  Recipients: {result.total_recipients}")
        print(f"  Sent: {result.emails_sent}")
        print(f"  Failed: {result.emails_failed}")
        print(f"  Success rate: {result.success_rate:.1f}%")

        # Demo ANOFM events campaign (dry run)
        print("\\n3. Running ANOFM events campaign (dry run)...")
        result = campaign_manager.execute_campaign(
            campaign_type=CampaignType.ANOFM_EVENTS,
            phase=CampaignPhase.PILOT,
            max_recipients=2,
            dry_run=True
        )

        print(f"✓ Campaign completed: {result.campaign_id}")
        print(f"  Recipients: {result.total_recipients}")
        print(f"  Sent: {result.emails_sent}")
        print(f"  Failed: {result.emails_failed}")
        print(f"  Success rate: {result.success_rate:.1f}%")

        # Get campaign statistics
        print("\\n4. Getting campaign statistics...")
        stats = campaign_manager.get_campaign_statistics(days=1)
        print(f"Campaign statistics (last 1 day):")
        print(f"  Total campaigns: {stats['total_campaigns']}")
        print(f"  Emails sent: {stats['total_emails_sent']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Rate limiter usage: {stats['rate_limiter_stats']['today']['percentage_used']:.1f}%")

        print("\\n✓ Campaign manager demo completed successfully!")

    except Exception as e:
        print(f"✗ Campaign manager demo failed: {str(e)}")
        return False

    return True


def demo_real_email_send():
    """Demo 6: Real email send to test address (optional)."""
    print("\\n" + "=" * 80)
    print("DEMO 6: REAL EMAIL SEND (OPTIONAL)")
    print("=" * 80)

    # Check if API key is configured
    config = get_config()
    if not config.email.brevo_api_key or config.email.brevo_api_key == "your_brevo_api_key_here":
        print("⚠ Skipping real email send - BREVO_API_KEY not configured")
        print("  To test real sending:")
        print("  1. Set BREVO_API_KEY in .env file")
        print("  2. Verify sender email in Brevo dashboard")
        print("  3. Update test email address below")
        return True

    # Get test email from user
    print("\\nTo test real email sending, enter a test email address.")
    print("⚠ WARNING: This will send a real email and count against your quota!")
    test_email = input("Enter test email (or press Enter to skip): ").strip()

    if not test_email:
        print("Skipped real email send")
        return True

    try:
        print(f"\\nSending test email to {test_email}...")

        # Initialize client and template
        with BrevoEmailClient() as client:
            template = GermanEmployerTemplate()

            # Template variables
            variables = {
                'company_name': 'Test Company GmbH',
                'contact_person': 'Test Manager',
                'website': 'https://example.com'
            }

            # Generate content
            subject = template.get_subject(**variables)
            html_content = template.get_html_content(**variables)
            text_content = template.get_text_content(**variables)

            # Send email
            result = client.send_email(
                to_email=test_email,
                to_name="Test Recipient",
                subject=f"[TEST] {subject}",
                html_content=html_content,
                text_content=text_content,
                template_variables=variables
            )

            if result.success:
                print(f"✓ Email sent successfully!")
                print(f"  Message ID: {result.message_id}")
                print(f"  Retry count: {result.retry_count}")
            else:
                print(f"✗ Email failed to send:")
                print(f"  Error: {result.error_message}")
                print(f"  Bounce detected: {result.bounce_detected}")
                print(f"  Retry count: {result.retry_count}")

        print("\\n✓ Real email send demo completed!")

    except Exception as e:
        print(f"✗ Real email send demo failed: {str(e)}")
        return False

    return True


def main():
    """Run all email campaign demos."""
    print("TASK 4: EMAIL CAMPAIGN SYSTEM DEMO")
    print("European Employer ANOFM Job Fair Integration")
    print(f"Demo started at: {datetime.now()}")
    print()

    # Setup logging
    logger = setup_logging()
    logger.info("Email campaigns demo starting")

    # Create data directory if it doesn't exist
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)

    # Track demo results
    demo_results = []

    # Run all demos
    demos = [
        ("Brevo Email Client", demo_brevo_client),
        ("Rate Limiter", demo_rate_limiter),
        ("Email Templates", demo_templates),
        ("Database Integration", demo_database_integration),
        ("Campaign Manager", demo_campaign_manager),
        ("Real Email Send", demo_real_email_send),
    ]

    for demo_name, demo_func in demos:
        logger.info(f"Starting demo: {demo_name}")
        try:
            success = demo_func()
            demo_results.append((demo_name, success))
            if success:
                logger.info(f"Demo completed successfully: {demo_name}")
            else:
                logger.error(f"Demo failed: {demo_name}")
        except Exception as e:
            logger.error(f"Demo crashed: {demo_name} - {str(e)}")
            demo_results.append((demo_name, False))

    # Summary
    print("\\n" + "=" * 80)
    print("DEMO SUMMARY")
    print("=" * 80)
    print()
    for demo_name, success in demo_results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{demo_name}: {status}")

    successful_demos = sum(1 for _, success in demo_results if success)
    total_demos = len(demo_results)

    print(f"\\nOverall: {successful_demos}/{total_demos} demos passed")

    if successful_demos == total_demos:
        print("\\n🎉 All demos completed successfully!")
        print("\\nTask 4: Email Campaign System is ready for production!")
        print("\\nNext steps:")
        print("1. Configure BREVO_API_KEY in .env for production")
        print("2. Verify sender email in Brevo dashboard")
        print("3. Set appropriate rate limits for deployment phase")
        print("4. Run pilot campaign with real employers")
    else:
        print("\\n⚠ Some demos failed - check logs for details")

    logger.info(f"Email campaigns demo completed: {successful_demos}/{total_demos} successful")


if __name__ == "__main__":
    main()