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

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH', 'config/token.json')
CREDS_PATH = os.getenv('GMAIL_CREDS_PATH', 'config/gmail_credentials.json')


class GmailService:
    """Gmail API service wrapper."""

    def __init__(self):
        self.service = None

    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API.

        Returns:
            True if authentication successful, False otherwise.
        """
        creds = None

        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired token...")
                try:
                    creds.refresh(Request())
                    with open(TOKEN_PATH, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    return False
            elif os.path.exists(CREDS_PATH):
                logger.info("Running OAuth flow...")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
                    creds = flow.run_local_server(port=0)
                    with open(TOKEN_PATH, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logger.error(f"OAuth flow failed: {e}")
                    return False
            else:
                logger.error(f"No credentials found at {CREDS_PATH}")
                return False

        try:
            self.service = build('gmail', 'v1', credentials=creds)
            return True
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            return False

    def is_configured(self) -> bool:
        """Check if Gmail credentials are configured."""
        return os.path.exists(TOKEN_PATH) or os.path.exists(CREDS_PATH)

    def fetch_messages(self, since_hours: int = 24, max_results: int = 100) -> list[dict[str, Any]]:
        """
        Fetch messages from inbox.

        Args:
            since_hours: Only fetch emails from the last N hours.
            max_results: Maximum number of messages to return.

        Returns:
            List of message objects with 'id' and 'threadId'.
        """
        if not self.service:
            if not self.authenticate():
                return []

        time_threshold = (datetime.now() - timedelta(hours=since_hours)).strftime('%Y/%m/%d')
        query = f"after:{time_threshold}"

        try:
            response = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                q=query,
                maxResults=max_results
            ).execute()

            messages = response.get('messages', [])
            logger.info(f"Fetched {len(messages)} messages from Gmail")
            return messages

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []

    def get_message_content(self, message_id: str) -> dict[str, Any]:
        """
        Get full message content.

        Args:
            message_id: Gmail message ID.

        Returns:
            Dictionary with 'snippet', 'subject', 'from', 'body', 'date', 'thread_id'.
        """
        if not self.service:
            return {}

        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            payload = message.get('payload', {})
            headers = payload.get('headers', [])

            # Extract headers
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            from_addr = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')

            # Extract body
            body = self._extract_body(payload)

            # Parse date
            internal_date = int(message.get('internalDate', 0)) / 1000
            email_date = datetime.fromtimestamp(internal_date) if internal_date else None

            return {
                'id': message_id,
                'thread_id': message.get('threadId', ''),
                'snippet': message.get('snippet', ''),
                'subject': subject,
                'from': from_addr,
                'body': body[:4000] if body else '',  # Truncate for API limits
                'date': email_date
            }

        except HttpError as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            return {}

    def _extract_body(self, payload: dict) -> str:
        """Extract plain text body from message payload."""
        parts = payload.get('parts', [])
        body = ""

        if parts:
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            data = payload.get('body', {}).get('data', '')
            if data:
                body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        return body


# Singleton instance
gmail_service = GmailService()
