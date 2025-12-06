"""OpenAI-based email classification for job applications."""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv(dotenv_path='config/.env')

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class EmailClassifier:
    """Classify emails using OpenAI."""

    def __init__(self):
        self.client = None
        if OPENAI_API_KEY:
            self.client = OpenAI(api_key=OPENAI_API_KEY)

    def is_configured(self) -> bool:
        """Check if OpenAI is configured."""
        return self.client is not None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError,))
    )
    def is_job_related(self, snippet: str) -> bool:
        """
        Quick check if email snippet is job-related.

        Args:
            snippet: Email preview text.

        Returns:
            True if likely job-related.
        """
        if not self.client:
            return False

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Determine if this email snippet is related to a job application "
                            "(e.g., application confirmation, rejection, interview invite, offer). "
                            "Return only 'Yes' or 'No'."
                        )
                    },
                    {"role": "user", "content": snippet}
                ],
                max_tokens=10
            )
            result = response.choices[0].message.content.strip().lower()
            return result == 'yes'
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError,))
    )
    def classify_email(self, email_content: str) -> Optional[dict]:
        """
        Extract job application details from email.

        Args:
            email_content: Full email content.

        Returns:
            Dictionary with company, job_title, location, status, or None if not job-related.
        """
        if not self.client:
            return None

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at analyzing job application emails.
Analyze this email and extract job application details.

If this is NOT a job application email, respond with exactly: NOT_JOB_EMAIL

If it IS job-related, respond in this exact format:
Company: [company name or "Unknown"]
Job Title: [job title or "Unknown"]
Location: [location or "Remote" or "Unknown"]
Status: [one of: Applied, Screening, Interviewing, Offer, Declined, Withdrawn]

Status definitions:
- Applied: Application received/confirmed
- Screening: Phone screen or initial review scheduled
- Interviewing: Interview scheduled or completed
- Offer: Job offer received
- Declined: Rejection received
- Withdrawn: You withdrew the application"""
                    },
                    {"role": "user", "content": email_content}
                ],
                max_tokens=200
            )

            result = response.choices[0].message.content.strip()

            if result == "NOT_JOB_EMAIL":
                return None

            # Parse the response
            details = {}
            for line in result.splitlines():
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    details[key] = value.strip()

            # Normalize status
            status_map = {
                'applied': 'applied',
                'screening': 'screening',
                'interviewing': 'interviewing',
                'offer': 'offer',
                'declined': 'declined',
                'rejected': 'declined',
                'withdrawn': 'withdrawn'
            }

            if 'status' in details:
                raw_status = details['status'].lower()
                for key, value in status_map.items():
                    if key in raw_status:
                        details['status'] = value
                        break

            return details if details.get('company') else None

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return None


# Singleton instance
classifier = EmailClassifier()
