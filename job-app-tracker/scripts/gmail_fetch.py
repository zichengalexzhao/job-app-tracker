# gmail_fetch.py
"""Gmail API integration for fetching job-related emails."""

import base64
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Configuration paths (can be overridden via environment variables)
TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH', 'config/token.json')
CREDS_PATH = os.getenv('GMAIL_CREDS_PATH', 'config/gmail_credentials.json')

# Constants
MAX_RESULTS_PER_PAGE = 500
MAX_CONTENT_LENGTH = 4000


def get_gmail_service():
    """
    Authenticate and return Gmail API service.

    Returns:
        Gmail API service resource.

    Raises:
        FileNotFoundError: If authentication files are missing.
        Exception: If authentication fails.
    """
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    else:
        logger.warning(f"No token found at {TOKEN_PATH}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired, attempting to refresh...")
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                raise
        elif os.path.exists(CREDS_PATH):
            logger.info("No valid token; running local auth (not suitable for CI)...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
        else:
            raise FileNotFoundError(
                f"Authentication failed: No valid token at {TOKEN_PATH} "
                f"and no credentials at {CREDS_PATH}"
            )

    return build('gmail', 'v1', credentials=creds)


def fetch_emails(since_hours: Optional[int] = 1) -> list[dict[str, Any]]:
    """
    Fetch emails from Gmail inbox.

    Args:
        since_hours: Only fetch emails from the last N hours. None for all emails.

    Returns:
        List of message objects with 'id' and 'threadId' fields.
    """
    try:
        service = get_gmail_service()
    except Exception as e:
        logger.error(f"Failed to get Gmail service: {e}")
        return []

    query = ""
    if since_hours is not None:
        time_threshold = (datetime.now() - timedelta(hours=since_hours)).strftime('%Y/%m/%d')
        query = f"after:{time_threshold}"
    logger.info(f"Gmail query: '{query}'")

    all_messages = []
    try:
        response = service.users().messages().list(
            userId='me',
            labelIds=['INBOX'],
            q=query,
            maxResults=MAX_RESULTS_PER_PAGE
        ).execute()

        messages = response.get('messages', [])
        logger.info(f"Initial page: {len(messages)} emails")
        all_messages.extend(messages or [])

        page_count = 1
        while 'nextPageToken' in response:
            page_count += 1
            page_token = response['nextPageToken']
            response = service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q=query,
                pageToken=page_token,
                maxResults=MAX_RESULTS_PER_PAGE
            ).execute()
            messages = response.get('messages', [])
            logger.info(f"Page {page_count}: {len(messages)} emails")
            all_messages.extend(messages or [])

    except HttpError as e:
        logger.error(f"Gmail API error while fetching emails: {e}")
        return all_messages

    logger.info(f"Total emails fetched: {len(all_messages)}")
    return all_messages


def get_email_snippet(message_id: str) -> str:
    """
    Get a short preview snippet of an email.

    Args:
        message_id: The Gmail message ID.

    Returns:
        The email snippet text, or empty string on error.
    """
    try:
        service = get_gmail_service()
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='minimal'
        ).execute()
        return message.get('snippet', '')
    except HttpError as e:
        logger.error(f"Failed to get snippet for message {message_id}: {e}")
        return ''


def get_email_content(message_id: str) -> dict[str, str]:
    """
    Get full email content including headers and body.

    Args:
        message_id: The Gmail message ID.

    Returns:
        Dictionary with 'content' (truncated to MAX_CONTENT_LENGTH) and 'date' fields.
    """
    try:
        service = get_gmail_service()
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
    except HttpError as e:
        logger.error(f"Failed to get content for message {message_id}: {e}")
        return {"content": "", "date": "Unknown"}

    payload = message.get('payload', {})
    parts = payload.get('parts', [])
    body = ""

    # Extract body from message parts
    if parts:
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                body += part.get('body', {}).get('data', '')
    else:
        body = payload.get('body', {}).get('data', '')

    # Decode base64 body
    if body:
        try:
            body = base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"Failed to decode email body: {e}")
            body = message.get('snippet', '')
    else:
        body = message.get('snippet', '')

    # Extract headers
    headers = payload.get('headers', [])
    from_header = next((h['value'] for h in headers if h['name'] == 'From'), '')
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
    full_content = f"From: {from_header}\nSubject: {subject}\n\n{body}"

    # Truncate content if too long
    if len(full_content) > MAX_CONTENT_LENGTH:
        logger.debug(f"Truncating email content from {len(full_content)} to {MAX_CONTENT_LENGTH} chars")
        full_content = full_content[:MAX_CONTENT_LENGTH]

    # Extract date
    internal_date = int(message.get('internalDate', 0)) / 1000
    email_date = datetime.fromtimestamp(internal_date).strftime('%Y-%m-%d') if internal_date else 'Unknown'

    return {"content": full_content, "date": email_date}
