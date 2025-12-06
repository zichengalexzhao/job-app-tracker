# scripts/process_emails.py
"""Email processing module using OpenAI for job application classification."""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError, APIConnectionError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path='config/.env')
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")

# Initialize OpenAI client (v1.0+ API)
client = OpenAI(api_key=OPENAI_API_KEY)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying API call (attempt {retry_state.attempt_number})..."
    )
)
def is_job_application(snippet: str) -> bool:
    """
    Quick check if email is job application-related using snippet.

    Args:
        snippet: A short preview of the email content.

    Returns:
        True if the email appears to be job application-related, False otherwise.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Determine if this email snippet is related to a job application "
                        "(e.g., confirmation, rejection, interview). Return 'Yes' or 'No'."
                    )
                },
                {"role": "user", "content": snippet}
            ]
        )
        result = response.choices[0].message.content.strip().lower() == 'yes'
        logger.debug(f"Email snippet classified as job application: {result}")
        return result
    except APIError as e:
        logger.error(f"OpenAI API error in is_job_application: {e}")
        return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying API call (attempt {retry_state.attempt_number})..."
    )
)
def classify_email(email_content: str) -> str:
    """
    Extract job application details from full email content.

    Args:
        email_content: The full email content including headers and body.

    Returns:
        A formatted string with extracted job details, or "Not Job Application"
        if the email is not job-related.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert at analyzing job application emails. "
                        "Analyze this email and confirm if it's a job application-related email "
                        "(e.g., confirmation, rejection, interview invite). "
                        "If not, return only: 'Not Job Application'. "
                        "If yes, extract: "
                        "1. Company name (infer from context if not explicit, else 'Unknown'), "
                        "2. Job title (infer from context if not explicit, else 'Unknown'), "
                        "3. Location (if not found, return 'Unknown'), "
                        "4. Status (e.g., 'Applied', 'Interviewed', 'Offer', 'Declined', or 'Unknown'). "
                        "Return in this format:\n"
                        "Company: [company name]\n"
                        "Job Title: [job title]\n"
                        "Location: [location]\n"
                        "Status: [status]\n"
                    )
                },
                {"role": "user", "content": email_content}
            ]
        )
        classification = response.choices[0].message.content.strip()

        if not classification.startswith("Company:"):
            logger.debug("Email classified as not job application")
            return "Not Job Application"

        logger.debug(f"Email classified successfully: {classification[:100]}...")
        return classification

    except APIError as e:
        logger.error(f"OpenAI API error in classify_email: {e}")
        return "Not Job Application"
    except (IndexError, AttributeError) as e:
        logger.error(f"Error processing OpenAI response: {e}")
        return "Not Job Application"
