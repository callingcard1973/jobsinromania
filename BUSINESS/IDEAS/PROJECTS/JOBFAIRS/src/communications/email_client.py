"""
Brevo Email Client for European Employer ANOFM Job Fair Integration.

Fresh Brevo client implementation with comprehensive error handling,
retry mechanisms, and proper integration with the Communication model.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import get_config


@dataclass
class EmailResult:
    """Result of email sending operation."""
    success: bool
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    bounce_detected: bool = False
    retry_count: int = 0
    send_time: Optional[datetime] = None


class BrevoAPIError(Exception):
    """Custom exception for Brevo API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class BrevoEmailClient:
    """
    Fresh Brevo API client with comprehensive email sending capabilities.

    Features:
    - Fresh HTTP client for each session
    - Proper error handling and retry logic
    - Bounce detection and handling
    - Rate limiting integration
    - Comprehensive logging
    - Integration with Communication model
    """

    def __init__(self):
        """Initialize Brevo client with fresh configuration."""
        self.config = get_config()
        self.logger = logging.getLogger(__name__)

        if not self.config.email.brevo_api_key:
            raise ValueError("BREVO_API_KEY not configured. Check .env file.")

        self.api_key = self.config.email.brevo_api_key
        self.sender_email = self.config.email.brevo_sender_email
        self.sender_name = self.config.email.brevo_sender_name

        # API endpoints
        self.base_url = "https://api.brevo.com/v3"
        self.send_url = f"{self.base_url}/smtp/email"
        self.account_url = f"{self.base_url}/account"

        # Initialize fresh HTTP session with proper configuration
        self.session = self._create_http_session()

        # Verify API key on initialization
        self._verify_api_key()

    def _create_http_session(self) -> requests.Session:
        """Create properly configured HTTP session with retries."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=2,  # Exponential backoff: 2, 4, 8 seconds
            raise_on_status=False
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set headers
        session.headers.update({
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': self.api_key
        })

        # Set timeout
        session.timeout = 30

        return session

    def _verify_api_key(self) -> None:
        """Verify API key is valid by checking account info."""
        try:
            response = self.session.get(self.account_url)
            if response.status_code == 401:
                raise BrevoAPIError("Invalid Brevo API key")
            elif response.status_code != 200:
                raise BrevoAPIError(f"API verification failed: {response.status_code}")

            account_info = response.json()
            self.logger.info(f"Brevo API verified. Plan: {account_info.get('plan', {}).get('type', 'Unknown')}")

        except requests.RequestException as e:
            raise BrevoAPIError(f"Failed to verify Brevo API key: {str(e)}")

    def check_sender_status(self, email: str) -> Tuple[bool, str]:
        """
        Check if sender email is verified and active.

        Args:
            email: Sender email to check

        Returns:
            Tuple of (is_verified, status_message)
        """
        try:
            # Check senders endpoint
            senders_url = f"{self.base_url}/senders"
            response = self.session.get(senders_url)

            if response.status_code != 200:
                return False, f"Failed to check senders: {response.status_code}"

            senders = response.json().get('senders', [])

            for sender in senders:
                if sender.get('email', '').lower() == email.lower():
                    if sender.get('active', False):
                        return True, "Sender verified and active"
                    else:
                        return False, f"Sender not active. Status: {sender.get('status', 'Unknown')}"

            return False, f"Sender email {email} not found in verified senders"

        except requests.RequestException as e:
            return False, f"Error checking sender status: {str(e)}"

    def send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None
    ) -> EmailResult:
        """
        Send email with comprehensive error handling and retry logic.

        Args:
            to_email: Recipient email address
            to_name: Recipient name
            subject: Email subject
            html_content: HTML email content
            text_content: Optional plain text content
            template_variables: Variables for template substitution

        Returns:
            EmailResult with success status and details
        """
        start_time = datetime.utcnow()

        # Validate inputs
        if not to_email or '@' not in to_email:
            return EmailResult(
                success=False,
                error_message=f"Invalid recipient email: {to_email}"
            )

        if not subject or not html_content:
            return EmailResult(
                success=False,
                error_message="Subject and HTML content are required"
            )

        # Prepare email payload
        payload = {
            "sender": {
                "name": self.sender_name,
                "email": self.sender_email
            },
            "to": [
                {
                    "email": to_email,
                    "name": to_name
                }
            ],
            "subject": subject,
            "htmlContent": html_content
        }

        if text_content:
            payload["textContent"] = text_content

        # Add template variables if provided
        if template_variables:
            payload["params"] = template_variables

        # Send email with retries
        for retry_count in range(4):  # 0, 1, 2, 3 = 4 attempts total
            try:
                self.logger.info(f"Sending email to {to_email} (attempt {retry_count + 1}/4)")

                response = self.session.post(self.send_url, json=payload)

                if response.status_code == 201:
                    # Success
                    result_data = response.json()
                    message_id = result_data.get('messageId')

                    self.logger.info(f"Email sent successfully to {to_email}. Message ID: {message_id}")

                    return EmailResult(
                        success=True,
                        message_id=message_id,
                        retry_count=retry_count,
                        send_time=start_time
                    )

                elif response.status_code == 400:
                    # Bad request - don't retry
                    error_data = response.json()
                    error_message = error_data.get('message', 'Bad request')

                    # Check for bounce indicators
                    bounce_detected = any(indicator in error_message.lower() for indicator in [
                        'invalid email', 'blocked', 'blacklisted', 'bounce', 'unsubscribed'
                    ])

                    self.logger.warning(f"Bad request sending to {to_email}: {error_message}")

                    return EmailResult(
                        success=False,
                        error_message=f"Bad request: {error_message}",
                        bounce_detected=bounce_detected,
                        retry_count=retry_count
                    )

                elif response.status_code == 429:
                    # Rate limited - wait and retry
                    self.logger.warning(f"Rate limited. Retry {retry_count + 1}/4")
                    if retry_count < 3:
                        time.sleep(2 ** retry_count)  # Exponential backoff: 1, 2, 4 seconds
                        continue

                elif response.status_code >= 500:
                    # Server error - retry
                    self.logger.warning(f"Server error {response.status_code}. Retry {retry_count + 1}/4")
                    if retry_count < 3:
                        time.sleep(2 ** retry_count)
                        continue

                else:
                    # Other error - log and retry
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get('message', f'HTTP {response.status_code}')

                    self.logger.warning(f"HTTP {response.status_code} sending to {to_email}: {error_message}")
                    if retry_count < 3:
                        time.sleep(2 ** retry_count)
                        continue

            except requests.RequestException as e:
                self.logger.error(f"Network error sending to {to_email} (attempt {retry_count + 1}): {str(e)}")
                if retry_count < 3:
                    time.sleep(2 ** retry_count)
                    continue

            except Exception as e:
                self.logger.error(f"Unexpected error sending to {to_email}: {str(e)}")
                break

        # All retries failed
        return EmailResult(
            success=False,
            error_message=f"Failed after 4 attempts",
            retry_count=3
        )

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information including quota and usage."""
        try:
            response = self.session.get(self.account_url)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}"}
        except requests.RequestException as e:
            return {"error": str(e)}

    def check_daily_quota(self) -> Tuple[int, int]:
        """
        Check current daily quota usage.

        Returns:
            Tuple of (emails_sent_today, daily_limit)
        """
        try:
            # Get account info
            account_info = self.get_account_info()

            if "error" in account_info:
                self.logger.warning(f"Could not check quota: {account_info['error']}")
                return 0, self.config.email.daily_email_limit

            plan_info = account_info.get('plan', {})
            emails_sent = plan_info.get('creditsUsed', {}).get('email', 0)
            email_credits = plan_info.get('credits', {}).get('email', self.config.email.daily_email_limit)

            return emails_sent, email_credits

        except Exception as e:
            self.logger.warning(f"Error checking quota: {str(e)}")
            return 0, self.config.email.daily_email_limit

    def close(self):
        """Close the HTTP session."""
        if hasattr(self, 'session'):
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()