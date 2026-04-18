"""
Comprehensive tests for email campaign system.

Tests cover template management, email client functionality, campaign execution,
and error handling scenarios to ensure robust operation.
"""

import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta

# Test imports
from src.communications.email_client import BrevoEmailClient, EmailResult, BrevoAPIError
from src.communications.campaign_manager import (
    CampaignManager, CampaignType, CampaignPhase, CampaignConfig, CampaignResult
)
from src.communications.templates import (
    EmailTemplate, GermanEmployerTemplate, DutchEmployerTemplate, ANOFMTemplate
)


class TestEmailTemplates(unittest.TestCase):
    """Test email template functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary template directory
        self.temp_dir = tempfile.mkdtemp()

        # Create test HTML template
        self.test_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Template</title></head>
        <body>
            <h1>Hello {name}</h1>
            <p>Company: {company_name}</p>
            <p>Contact: {contact_email}</p>
        </body>
        </html>
        """

        self.template_file = os.path.join(self.temp_dir, "test_template.html")
        with open(self.template_file, 'w', encoding='utf-8') as f:
            f.write(self.test_html)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_german_employer_template_subject(self):
        """Test German employer template subject generation."""
        template = GermanEmployerTemplate()

        # Test with company name
        subject = template.get_subject(company_name="BMW Manufacturing")
        self.assertIn("BMW Manufacturing", subject)
        self.assertIn("Romanian Automotive Workers", subject)

        # Test without company name
        subject = template.get_subject()
        self.assertIn("your company", subject)

    def test_dutch_employer_template_subject(self):
        """Test Dutch employer template subject generation."""
        template = DutchEmployerTemplate()

        subject = template.get_subject(company_name="Dutch Farms BV")
        self.assertIn("Dutch Farms BV", subject)
        self.assertIn("Agricultural Workers", subject)

    def test_anofm_template_subject(self):
        """Test ANOFM template subject generation."""
        template = ANOFMTemplate()

        subject = template.get_subject(event_name="Bursa de Muncă Cluj")
        self.assertIn("Bursa de Muncă Cluj", subject)
        self.assertIn("Parteneriat european", subject)

    def test_template_variable_substitution(self):
        """Test template variable substitution."""
        template = GermanEmployerTemplate()

        # Mock the template directory to use our temp directory
        template.template_dir = self.temp_dir

        # Test variable substitution
        result = template.substitute_variables(
            "Hello {name}, welcome to {company_name}!",
            name="John Doe"
        )

        self.assertIn("John Doe", result)
        self.assertIn("InterJob Romania", result)  # Default company name

    def test_template_file_loading(self):
        """Test HTML template file loading."""
        template = GermanEmployerTemplate()
        template.template_dir = self.temp_dir

        # Test successful loading
        content = template.load_html_template("test_template.html")
        self.assertIn("Hello {name}", content)
        self.assertIn("<title>Test Template</title>", content)

        # Test file not found
        content = template.load_html_template("nonexistent.html")
        self.assertIn("Email Template Error", content)

    def test_template_text_content(self):
        """Test plain text content generation."""
        template = GermanEmployerTemplate()

        text = template.get_text_content(company_name="Test Company")
        self.assertIn("Test Company", text)
        self.assertIn("ROMANIAN AUTOMOTIVE WORKERS", text)
        self.assertIn("interjob.ro/apply.html", text)


class TestBrevoEmailClient(unittest.TestCase):
    """Test Brevo email client functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock()
        self.mock_config.email.brevo_api_key = "test_api_key"
        self.mock_config.email.brevo_sender_email = "test@interjob.ro"
        self.mock_config.email.brevo_sender_name = "InterJob Romania"
        self.mock_config.email.daily_email_limit = 500

    @patch('src.communications.email_client.get_config')
    @patch('src.communications.email_client.requests.Session')
    def test_client_initialization(self, mock_session_class, mock_get_config):
        """Test Brevo client initialization."""
        mock_get_config.return_value = self.mock_config
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock successful API verification
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"plan": {"type": "free"}}
        mock_session.get.return_value = mock_response

        client = BrevoEmailClient()

        self.assertEqual(client.api_key, "test_api_key")
        self.assertEqual(client.sender_email, "test@interjob.ro")
        mock_session.get.assert_called()

    @patch('src.communications.email_client.get_config')
    def test_client_invalid_api_key(self, mock_get_config):
        """Test client initialization with invalid API key."""
        self.mock_config.email.brevo_api_key = None
        mock_get_config.return_value = self.mock_config

        with self.assertRaises(ValueError):
            BrevoEmailClient()

    @patch('src.communications.email_client.get_config')
    @patch('src.communications.email_client.requests.Session')
    def test_send_email_success(self, mock_session_class, mock_get_config):
        """Test successful email sending."""
        mock_get_config.return_value = self.mock_config
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock API verification
        verify_response = Mock()
        verify_response.status_code = 200
        verify_response.json.return_value = {"plan": {"type": "free"}}

        # Mock email send
        send_response = Mock()
        send_response.status_code = 201
        send_response.json.return_value = {"messageId": "test_message_123"}

        mock_session.get.return_value = verify_response
        mock_session.post.return_value = send_response

        client = BrevoEmailClient()

        result = client.send_email(
            to_email="recipient@example.com",
            to_name="Test Recipient",
            subject="Test Subject",
            html_content="<p>Test content</p>"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.message_id, "test_message_123")
        self.assertEqual(result.retry_count, 0)

    @patch('src.communications.email_client.get_config')
    @patch('src.communications.email_client.requests.Session')
    def test_send_email_invalid_recipient(self, mock_session_class, mock_get_config):
        """Test email sending with invalid recipient."""
        mock_get_config.return_value = self.mock_config
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock API verification
        verify_response = Mock()
        verify_response.status_code = 200
        verify_response.json.return_value = {"plan": {"type": "free"}}
        mock_session.get.return_value = verify_response

        client = BrevoEmailClient()

        # Test invalid email
        result = client.send_email(
            to_email="invalid_email",
            to_name="Test Recipient",
            subject="Test Subject",
            html_content="<p>Test content</p>"
        )

        self.assertFalse(result.success)
        self.assertIn("Invalid recipient email", result.error_message)

    @patch('src.communications.email_client.get_config')
    @patch('src.communications.email_client.requests.Session')
    def test_send_email_rate_limited(self, mock_session_class, mock_get_config):
        """Test email sending when rate limited."""
        mock_get_config.return_value = self.mock_config
        mock_session = Mock()
        mock_session_class.return_value = mock_session

        # Mock API verification
        verify_response = Mock()
        verify_response.status_code = 200
        verify_response.json.return_value = {"plan": {"type": "free"}}

        # Mock rate limited response
        rate_limited_response = Mock()
        rate_limited_response.status_code = 429

        mock_session.get.return_value = verify_response
        mock_session.post.return_value = rate_limited_response

        client = BrevoEmailClient()

        with patch('time.sleep'):  # Mock sleep to speed up test
            result = client.send_email(
                to_email="recipient@example.com",
                to_name="Test Recipient",
                subject="Test Subject",
                html_content="<p>Test content</p>"
            )

        self.assertFalse(result.success)
        self.assertEqual(result.retry_count, 3)


class TestCampaignManager(unittest.TestCase):
    """Test campaign manager functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock()
        self.mock_db = Mock()

        # Mock database session
        self.mock_session = Mock()
        self.mock_db.get_session.return_value.__enter__.return_value = self.mock_session
        self.mock_db.get_session.return_value.__exit__.return_value = None

    @patch('src.communications.campaign_manager.get_config')
    @patch('src.communications.campaign_manager.get_database')
    def test_campaign_manager_initialization(self, mock_get_database, mock_get_config):
        """Test campaign manager initialization."""
        mock_get_config.return_value = self.mock_config
        mock_get_database.return_value = self.mock_db

        manager = CampaignManager()

        self.assertIsNotNone(manager.templates)
        self.assertEqual(len(manager.templates), 5)
        self.assertIn(CampaignType.GERMAN_EMPLOYERS, manager.templates)

    @patch('src.communications.campaign_manager.get_config')
    @patch('src.communications.campaign_manager.get_database')
    def test_campaign_config_creation(self, mock_get_database, mock_get_config):
        """Test campaign configuration creation."""
        mock_get_config.return_value = self.mock_config
        mock_get_database.return_value = self.mock_db

        manager = CampaignManager()

        config = manager._create_campaign_config(
            CampaignType.GERMAN_EMPLOYERS,
            CampaignPhase.PILOT,
            max_recipients=25
        )

        self.assertEqual(config.campaign_type, CampaignType.GERMAN_EMPLOYERS)
        self.assertEqual(config.phase, CampaignPhase.PILOT)
        self.assertEqual(config.max_recipients, 25)
        self.assertEqual(config.retry_attempts, 3)

    @patch('src.communications.campaign_manager.get_config')
    @patch('src.communications.campaign_manager.get_database')
    def test_rate_limiting(self, mock_get_database, mock_get_config):
        """Test rate limiting functionality."""
        mock_get_config.return_value = self.mock_config
        mock_get_database.return_value = self.mock_db

        manager = CampaignManager()
        manager.daily_limit = 10
        manager.emails_sent_today = 5

        # Should allow sending
        can_send, reason, info = manager.can_send_email()
        self.assertTrue(can_send)
        self.assertEqual(info['remaining'], 5)

        # Hit limit
        manager.emails_sent_today = 10
        can_send, reason, info = manager.can_send_email()
        self.assertFalse(can_send)
        self.assertIn("Daily limit reached", reason)

    @patch('src.communications.campaign_manager.get_config')
    @patch('src.communications.campaign_manager.get_database')
    def test_dry_run_campaign(self, mock_get_database, mock_get_config):
        """Test dry run campaign execution."""
        mock_get_config.return_value = self.mock_config
        mock_get_database.return_value = self.mock_db

        # Mock recipients query
        mock_employers = [
            Mock(id=1, contact_email="test1@example.com", contact_person="Manager 1",
                 name="Company 1", country="DE", sector="Automotive", website="test1.com"),
            Mock(id=2, contact_email="test2@example.com", contact_person="Manager 2",
                 name="Company 2", country="DE", sector="Automotive", website="test2.com")
        ]
        self.mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = mock_employers

        manager = CampaignManager()

        result = manager.execute_campaign(
            CampaignType.GERMAN_EMPLOYERS,
            CampaignPhase.PILOT,
            max_recipients=2,
            dry_run=True
        )

        self.assertEqual(result.total_recipients, 2)
        self.assertEqual(result.emails_sent, 2)
        self.assertEqual(result.emails_failed, 0)
        self.assertEqual(result.success_rate, 100.0)

    @patch('src.communications.campaign_manager.get_config')
    @patch('src.communications.campaign_manager.get_database')
    def test_campaign_statistics(self, mock_get_database, mock_get_config):
        """Test campaign statistics generation."""
        mock_get_config.return_value = self.mock_config
        mock_get_database.return_value = self.mock_db

        # Mock communications data
        mock_communications = [
            Mock(status='sent', campaign_id='german_employers_pilot_123', notes=''),
            Mock(status='failed', campaign_id='german_employers_pilot_123', notes='bounce detected'),
            Mock(status='sent', campaign_id='dutch_employers_pilot_456', notes='')
        ]

        self.mock_session.query.return_value.filter.return_value.all.return_value = mock_communications

        manager = CampaignManager()
        stats = manager.get_campaign_statistics(days=30)

        self.assertEqual(stats['total_emails_sent'], 2)
        self.assertEqual(stats['total_emails_failed'], 1)
        self.assertEqual(stats['success_rate'], 66.67)  # Approximately
        self.assertEqual(stats['total_campaigns'], 2)


class TestEmailCampaignIntegration(unittest.TestCase):
    """Integration tests for email campaign system."""

    def test_template_and_client_integration(self):
        """Test integration between templates and email client."""
        # This would be a more comprehensive integration test
        # that tests the full pipeline from template generation
        # to email sending in a controlled environment
        pass

    def test_campaign_end_to_end(self):
        """Test end-to-end campaign execution."""
        # This would test the complete campaign flow including:
        # - Recipient selection
        # - Template generation
        # - Email sending
        # - Database recording
        # - Error handling
        pass


if __name__ == '__main__':
    unittest.main()