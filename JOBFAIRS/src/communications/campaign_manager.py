"""
Campaign Manager for European Employer ANOFM Job Fair Integration.

Comprehensive campaign management system that orchestrates email campaigns
with proper rate limiting, error handling, and database integration.
Processes campaigns one-by-one with automatic retries and bounce handling.
"""

import logging
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any, Type
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session

from config import get_config
from src.database.connection import get_database
from src.database.models import (
    Employer, ANOFMEvent, Communication, MessageType, EmployerStatus
)
from src.communications.email_client import BrevoEmailClient, EmailResult
from src.communications.templates import (
    EmailTemplate, GermanEmployerTemplate, DutchEmployerTemplate, ANOFMTemplate
)


class CampaignType(Enum):
    """Types of email campaigns."""
    GERMAN_EMPLOYERS = "german_employers"
    DUTCH_EMPLOYERS = "dutch_employers"
    ANOFM_EVENTS = "anofm_events"
    FOLLOW_UP = "follow_up"
    REMINDER = "reminder"


class CampaignPhase(Enum):
    """Campaign deployment phases."""
    PILOT = "pilot"
    SCALING = "scaling"
    FULL = "full"


@dataclass
class CampaignConfig:
    """Configuration for email campaigns."""
    campaign_type: CampaignType
    phase: CampaignPhase
    max_recipients: int
    retry_attempts: int = 3
    retry_delay_base: int = 60  # Base delay in seconds for exponential backoff
    batch_size: int = 10
    pause_between_batches: int = 5  # Seconds between batches


@dataclass
class CampaignResult:
    """Result of campaign execution."""
    campaign_id: str
    campaign_type: CampaignType
    total_recipients: int
    emails_sent: int
    emails_failed: int
    bounces_detected: int
    retries_used: int
    start_time: datetime
    end_time: datetime
    errors: List[str]
    success_rate: float

    @property
    def duration_minutes(self) -> float:
        """Get campaign duration in minutes."""
        return (self.end_time - self.start_time).total_seconds() / 60


class CampaignManager:
    """
    Comprehensive email campaign manager with professional execution.

    Features:
    - One-by-one campaign processing with rate limiting
    - Automatic retry with exponential backoff
    - Bounce detection and handling
    - Integration with Communication model
    - Comprehensive logging and error handling
    - Phase-based limits enforcement
    """

    def __init__(self):
        """Initialize campaign manager with all required components."""
        self.config = get_config()
        self.logger = logging.getLogger(__name__)

        # Initialize components
        self.db = get_database()

        # Create rate limiter with 500 emails per day
        self.daily_limit = 500
        self.emails_sent_today = 0
        self.last_reset = datetime.now().date()

        # Template mapping
        self.templates: Dict[CampaignType, Type[EmailTemplate]] = {
            CampaignType.GERMAN_EMPLOYERS: GermanEmployerTemplate,
            CampaignType.DUTCH_EMPLOYERS: DutchEmployerTemplate,
            CampaignType.ANOFM_EVENTS: ANOFMTemplate,
            CampaignType.FOLLOW_UP: GermanEmployerTemplate,  # Use appropriate template
            CampaignType.REMINDER: ANOFMTemplate  # Use appropriate template
        }

        self.logger.info("Campaign manager initialized successfully")

    def can_send_email(self) -> Tuple[bool, str, Dict[str, Any]]:
        """Check if we can send an email based on rate limits."""
        # Reset counter if new day
        today = datetime.now().date()
        if today > self.last_reset:
            self.emails_sent_today = 0
            self.last_reset = today

        if self.emails_sent_today >= self.daily_limit:
            return False, f"Daily limit reached ({self.daily_limit})", {
                "emails_sent_today": self.emails_sent_today,
                "daily_limit": self.daily_limit
            }

        return True, "OK", {
            "emails_sent_today": self.emails_sent_today,
            "daily_limit": self.daily_limit,
            "remaining": self.daily_limit - self.emails_sent_today
        }

    def record_email_sent(self):
        """Record that an email was sent."""
        self.emails_sent_today += 1

    def execute_campaign(
        self,
        campaign_type: CampaignType,
        phase: CampaignPhase = CampaignPhase.PILOT,
        max_recipients: Optional[int] = None,
        dry_run: bool = False
    ) -> CampaignResult:
        """
        Execute complete email campaign with comprehensive management.

        Args:
            campaign_type: Type of campaign to execute
            phase: Deployment phase (pilot, scaling, full)
            max_recipients: Optional override for recipient limit
            dry_run: If True, simulate without sending emails

        Returns:
            CampaignResult with comprehensive execution details
        """
        start_time = datetime.utcnow()
        campaign_id = f"{campaign_type.value}_{phase.value}_{start_time.strftime('%Y%m%d_%H%M%S')}"

        self.logger.info(f"Starting campaign: {campaign_id} (dry_run={dry_run})")

        # Initialize result tracking
        result = CampaignResult(
            campaign_id=campaign_id,
            campaign_type=campaign_type,
            total_recipients=0,
            emails_sent=0,
            emails_failed=0,
            bounces_detected=0,
            retries_used=0,
            start_time=start_time,
            end_time=start_time,
            errors=[],
            success_rate=0.0
        )

        try:
            # Create campaign configuration
            config = self._create_campaign_config(campaign_type, phase, max_recipients)

            # Get recipients based on campaign type
            recipients = self._get_campaign_recipients(campaign_type, config.max_recipients)
            result.total_recipients = len(recipients)

            if not recipients:
                self.logger.warning(f"No recipients found for campaign {campaign_id}")
                result.end_time = datetime.utcnow()
                return result

            self.logger.info(f"Campaign {campaign_id}: Processing {len(recipients)} recipients")

            # Initialize email client
            if not dry_run:
                email_client = BrevoEmailClient()
            else:
                email_client = None

            # Initialize template
            template_class = self.templates[campaign_type]
            template = template_class()

            # Process recipients one by one
            with self.db.get_session() as session:
                for i, recipient in enumerate(recipients, 1):
                    # Check rate limits
                    if not dry_run:
                        can_send, reason, usage_info = self.can_send_email()
                        if not can_send:
                            self.logger.warning(f"Rate limit reached: {reason}")
                            result.errors.append(f"Rate limit reached at recipient {i}: {reason}")
                            break

                    # Process individual recipient
                    send_result = self._send_to_recipient(
                        recipient=recipient,
                        template=template,
                        email_client=email_client,
                        session=session,
                        campaign_id=campaign_id,
                        dry_run=dry_run
                    )

                    # Update result tracking
                    if send_result.success:
                        result.emails_sent += 1
                        if not dry_run:
                            self.record_email_sent()
                    else:
                        result.emails_failed += 1
                        if send_result.bounce_detected:
                            result.bounces_detected += 1

                    result.retries_used += send_result.retry_count

                    # Log progress
                    if i % 10 == 0 or i == len(recipients):
                        self.logger.info(f"Campaign progress: {i}/{len(recipients)} "
                                       f"({result.emails_sent} sent, {result.emails_failed} failed)")

                    # Pause between sends to respect rate limits
                    if not dry_run and i < len(recipients):
                        time.sleep(2)  # 2 second pause between emails

            # Close email client
            if email_client:
                email_client.close()

            # Calculate final statistics
            result.end_time = datetime.utcnow()
            if result.total_recipients > 0:
                result.success_rate = (result.emails_sent / result.total_recipients) * 100

            self.logger.info(f"Campaign {campaign_id} completed: {result.emails_sent}/{result.total_recipients} "
                           f"sent ({result.success_rate:.1f}% success rate)")

            return result

        except Exception as e:
            self.logger.error(f"Campaign {campaign_id} failed: {str(e)}")
            result.errors.append(f"Campaign execution failed: {str(e)}")
            result.end_time = datetime.utcnow()
            return result

    def _create_campaign_config(
        self,
        campaign_type: CampaignType,
        phase: CampaignPhase,
        max_recipients: Optional[int] = None
    ) -> CampaignConfig:
        """Create campaign configuration based on type and phase."""
        # Default phase limits
        phase_limits = {
            'pilot': {'max_employers': 50, 'max_workers': 100},
            'scaling': {'max_employers': 200, 'max_workers': 500},
            'full': {'max_employers': 1000, 'max_workers': 2000}
        }

        # Determine max recipients
        if max_recipients is not None:
            max_recip = max_recipients
        elif campaign_type in [CampaignType.GERMAN_EMPLOYERS, CampaignType.DUTCH_EMPLOYERS]:
            max_recip = phase_limits[phase.value].get('max_employers', 50)
        else:  # ANOFM events
            max_recip = phase_limits[phase.value].get('max_workers', 100)

        return CampaignConfig(
            campaign_type=campaign_type,
            phase=phase,
            max_recipients=max_recip,
            retry_attempts=3,
            retry_delay_base=60,
            batch_size=10,
            pause_between_batches=5
        )

    def _get_campaign_recipients(self, campaign_type: CampaignType, max_recipients: int) -> List[Dict[str, Any]]:
        """
        Get recipients for campaign based on type and limits.

        Args:
            campaign_type: Type of campaign
            max_recipients: Maximum number of recipients

        Returns:
            List of recipient dictionaries with required fields
        """
        recipients = []

        try:
            with self.db.get_session() as session:
                if campaign_type == CampaignType.GERMAN_EMPLOYERS:
                    # Get German automotive employers
                    employers = session.query(Employer).filter(
                        Employer.country == 'DE',
                        Employer.sector == 'Automotive',
                        Employer.status.in_([EmployerStatus.PROSPECTIVE, EmployerStatus.CONTACTED]),
                        Employer.contact_email.isnot(None)
                    ).limit(max_recipients).all()

                    recipients = [
                        {
                            'id': emp.id,
                            'type': 'employer',
                            'email': emp.contact_email,
                            'name': emp.contact_person or 'Hiring Manager',
                            'company_name': emp.name,
                            'country': emp.country,
                            'sector': emp.sector,
                            'website': emp.website
                        }
                        for emp in employers
                    ]

                elif campaign_type == CampaignType.DUTCH_EMPLOYERS:
                    # Get Dutch agricultural employers
                    employers = session.query(Employer).filter(
                        Employer.country == 'NL',
                        Employer.sector == 'Agriculture',
                        Employer.status.in_([EmployerStatus.PROSPECTIVE, EmployerStatus.CONTACTED]),
                        Employer.contact_email.isnot(None)
                    ).limit(max_recipients).all()

                    recipients = [
                        {
                            'id': emp.id,
                            'type': 'employer',
                            'email': emp.contact_email,
                            'name': emp.contact_person or 'Agricultural Manager',
                            'company_name': emp.name,
                            'country': emp.country,
                            'sector': emp.sector,
                            'website': emp.website
                        }
                        for emp in employers
                    ]

                elif campaign_type == CampaignType.ANOFM_EVENTS:
                    # Get upcoming ANOFM events
                    events = session.query(ANOFMEvent).filter(
                        ANOFMEvent.date >= date.today(),
                        ANOFMEvent.organizer_email.isnot(None)
                    ).order_by(ANOFMEvent.date).limit(max_recipients).all()

                    recipients = [
                        {
                            'id': event.id,
                            'type': 'anofm_event',
                            'email': event.organizer_email,
                            'name': event.organizer_contact or 'ANOFM Organizer',
                            'event_name': event.name,
                            'event_date': event.date.strftime('%d %B %Y') if event.date else '',
                            'event_location': event.location,
                            'region': event.region
                        }
                        for event in events
                    ]

        except Exception as e:
            self.logger.error(f"Error getting recipients for {campaign_type}: {str(e)}")

        self.logger.info(f"Found {len(recipients)} recipients for {campaign_type.value}")
        return recipients

    def _send_to_recipient(
        self,
        recipient: Dict[str, Any],
        template: EmailTemplate,
        email_client: Optional[BrevoEmailClient],
        session: Session,
        campaign_id: str,
        dry_run: bool = False
    ) -> EmailResult:
        """
        Send email to individual recipient with retry logic.

        Args:
            recipient: Recipient information
            template: Email template instance
            email_client: Brevo client (None for dry run)
            session: Database session
            campaign_id: Campaign identifier
            dry_run: If True, simulate without sending

        Returns:
            EmailResult with send status
        """
        email = recipient['email']
        name = recipient['name']

        try:
            # Generate email content
            subject = template.get_subject(**recipient)
            html_content = template.get_html_content(**recipient)
            text_content = template.get_text_content(**recipient)

            # Create communication record
            message_type = self._get_message_type(recipient['type'])
            communication = Communication(
                recipient_type=recipient['type'],
                recipient_id=recipient['id'],
                recipient_email=email,
                subject=subject,
                message_type=message_type,
                template_id=template.__class__.__name__,
                content=html_content[:5000],  # Truncate for storage
                campaign_id=campaign_id,
                campaign_phase="pilot",  # Default phase
                status="pending"
            )
            session.add(communication)
            session.flush()  # Get ID

            # Send email with retries
            for attempt in range(4):  # 0, 1, 2, 3 = 4 attempts total
                if dry_run:
                    # Simulate successful send for dry run
                    result = EmailResult(
                        success=True,
                        message_id=f"dry_run_{communication.id}",
                        retry_count=attempt,
                        send_time=datetime.utcnow()
                    )
                    break
                else:
                    # Actually send email
                    result = email_client.send_email(
                        to_email=email,
                        to_name=name,
                        subject=subject,
                        html_content=html_content,
                        text_content=text_content,
                        template_variables=recipient
                    )

                if result.success:
                    # Success - break retry loop
                    break
                elif result.bounce_detected:
                    # Don't retry bounces
                    self.logger.warning(f"Bounce detected for {email}: {result.error_message}")
                    break
                elif attempt < 3:
                    # Retry with exponential backoff
                    delay = (2 ** attempt) * 60  # 60, 120, 240 seconds
                    self.logger.warning(f"Retry {attempt + 1}/4 for {email} in {delay}s: {result.error_message}")
                    time.sleep(delay)

            # Update communication record
            if result.success:
                communication.mark_sent(result.message_id, "brevo")
                self.logger.info(f"Email sent successfully to {email}")
            else:
                communication.mark_failed(result.error_message)
                self.logger.error(f"Email failed to {email}: {result.error_message}")

            # Update employer status if applicable
            if recipient['type'] == 'employer' and result.success:
                employer = session.query(Employer).filter(Employer.id == recipient['id']).first()
                if employer and employer.status == EmployerStatus.PROSPECTIVE:
                    employer.status = EmployerStatus.CONTACTED

            session.commit()
            return result

        except Exception as e:
            self.logger.error(f"Error sending to {email}: {str(e)}")
            session.rollback()
            return EmailResult(
                success=False,
                error_message=f"Processing error: {str(e)}"
            )

    def _get_message_type(self, recipient_type: str) -> MessageType:
        """Get appropriate message type for recipient."""
        if recipient_type == 'employer':
            return MessageType.INITIAL_CONTACT
        elif recipient_type == 'anofm_event':
            return MessageType.INVITATION
        else:
            return MessageType.INITIAL_CONTACT

    def get_campaign_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get campaign statistics for the last N days.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with comprehensive statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        stats = {
            'period_days': days,
            'period_start': cutoff_date.isoformat(),
            'total_campaigns': 0,
            'total_emails_sent': 0,
            'total_emails_failed': 0,
            'bounce_rate': 0.0,
            'success_rate': 0.0,
            'by_campaign_type': {},
            'daily_limit': self.daily_limit,
            'emails_sent_today': self.emails_sent_today
        }

        try:
            with self.db.get_session() as session:
                # Get communication stats
                communications = session.query(Communication).filter(
                    Communication.created_at >= cutoff_date
                ).all()

                stats['total_campaigns'] = len(set(comm.campaign_id for comm in communications if comm.campaign_id))

                sent_count = sum(1 for comm in communications if comm.status == 'sent')
                failed_count = sum(1 for comm in communications if comm.status == 'failed')
                bounced_count = sum(1 for comm in communications
                                  if comm.status == 'failed' and 'bounce' in (comm.notes or '').lower())

                stats['total_emails_sent'] = sent_count
                stats['total_emails_failed'] = failed_count

                total_emails = sent_count + failed_count
                if total_emails > 0:
                    stats['success_rate'] = (sent_count / total_emails) * 100
                    stats['bounce_rate'] = (bounced_count / total_emails) * 100

                # Stats by campaign type
                by_type = {}
                for comm in communications:
                    if not comm.campaign_id:
                        continue

                    campaign_type = comm.campaign_id.split('_')[0] if '_' in comm.campaign_id else 'unknown'
                    if campaign_type not in by_type:
                        by_type[campaign_type] = {'sent': 0, 'failed': 0}

                    if comm.status == 'sent':
                        by_type[campaign_type]['sent'] += 1
                    elif comm.status == 'failed':
                        by_type[campaign_type]['failed'] += 1

                stats['by_campaign_type'] = by_type

        except Exception as e:
            self.logger.error(f"Error getting campaign statistics: {str(e)}")

        return stats

    def create_sample_data(self) -> Tuple[int, int]:
        """
        Create sample ANOFM events for demonstration purposes.

        Returns:
            Tuple of (events_created, events_existing)
        """
        sample_events = [
            {
                'name': 'Bursa Generală de Muncă Hunedoara',
                'date': date.today() + timedelta(days=30),
                'location': 'Hunedoara, jud. Hunedoara',
                'region': 'Hunedoara',
                'organizer_contact': 'Maria Popescu',
                'organizer_email': 'hunedoara@anofm.ro',
                'organizer_phone': '0254-123456',
                'participation_fee': 150.00,
                'registration_deadline': date.today() + timedelta(days=15),
                'anofm_url': 'https://www.anofm.ro/burse-de-munca/hunedoara'
            },
            {
                'name': 'Bursa de Muncă pentru Construcții și Industrie Gorj',
                'date': date.today() + timedelta(days=45),
                'location': 'Târgu Jiu, jud. Gorj',
                'region': 'Gorj',
                'organizer_contact': 'Ion Dumitrescu',
                'organizer_email': 'gorj.industrie@anofm.ro',
                'organizer_phone': '0253-987654',
                'participation_fee': 200.00,
                'registration_deadline': date.today() + timedelta(days=25),
                'anofm_url': 'https://www.anofm.ro/burse-de-munca/gorj'
            },
            {
                'name': 'Bursa de Muncă Agricultură și Servicii Vaslui',
                'date': date.today() + timedelta(days=60),
                'location': 'Vaslui, jud. Vaslui',
                'region': 'Vaslui',
                'organizer_contact': 'Elena Constantinescu',
                'organizer_email': 'vaslui.agricultura@anofm.ro',
                'organizer_phone': '0235-456789',
                'participation_fee': 100.00,
                'registration_deadline': date.today() + timedelta(days=40),
                'anofm_url': 'https://www.anofm.ro/burse-de-munca/vaslui'
            }
        ]

        created_count = 0
        existing_count = 0

        try:
            with self.db.get_session() as session:
                for event_data in sample_events:
                    # Check if event already exists
                    existing = session.query(ANOFMEvent).filter(
                        ANOFMEvent.name == event_data['name'],
                        ANOFMEvent.date == event_data['date']
                    ).first()

                    if existing:
                        existing_count += 1
                        self.logger.info(f"ANOFM event already exists: {event_data['name']}")
                    else:
                        # Create new event
                        event = ANOFMEvent(**event_data)
                        session.add(event)
                        created_count += 1
                        self.logger.info(f"Created ANOFM event: {event_data['name']}")

                session.commit()

        except Exception as e:
            self.logger.error(f"Error creating sample ANOFM events: {str(e)}")

        return created_count, existing_count