"""Google Calendar integration for interview scheduling."""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Calendar API requires additional scope
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

TOKEN_PATH = os.getenv('GOOGLE_TOKEN_PATH', 'config/token.json')
CREDS_PATH = os.getenv('GOOGLE_CREDS_PATH', 'config/gmail_credentials.json')


class CalendarService:
    """Google Calendar API service wrapper."""

    def __init__(self):
        self.service = None

    def is_configured(self) -> bool:
        """Check if Calendar API credentials are configured."""
        return os.path.exists(TOKEN_PATH) or os.path.exists(CREDS_PATH)

    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API.

        Returns:
            True if authentication successful.
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
                logger.info("Running OAuth flow for Calendar...")
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
            self.service = build('calendar', 'v3', credentials=creds)
            return True
        except Exception as e:
            logger.error(f"Failed to build Calendar service: {e}")
            return False

    def create_event(
        self,
        title: str,
        description: str,
        location: str,
        start_time: datetime,
        duration_minutes: int = 60,
        reminder_minutes: int = 30
    ) -> Optional[str]:
        """
        Create a calendar event.

        Returns:
            Event ID if successful, None otherwise.
        """
        if not self.service:
            if not self.authenticate():
                return None

        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/New_York',  # TODO: Make configurable
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/New_York',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': reminder_minutes},
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                ],
            },
        }

        try:
            result = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            logger.info(f"Created calendar event: {result.get('id')}")
            return result.get('id')
        except HttpError as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None

    def update_event(
        self,
        event_id: str,
        title: str,
        description: str,
        location: str,
        start_time: datetime,
        duration_minutes: int = 60
    ) -> bool:
        """Update an existing calendar event."""
        if not self.service:
            if not self.authenticate():
                return False

        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            'summary': title,
            'location': location,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/New_York',
            },
        }

        try:
            self.service.events().update(
                calendarId='primary',
                eventId=event_id,
                body=event
            ).execute()
            logger.info(f"Updated calendar event: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to update calendar event: {e}")
            return False

    def delete_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        if not self.service:
            if not self.authenticate():
                return False

        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()
            logger.info(f"Deleted calendar event: {event_id}")
            return True
        except HttpError as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return False

    def add_application_event(
        self,
        company: str,
        job_title: str,
        applied_date: datetime
    ) -> Optional[str]:
        """Add a calendar event for when an application was submitted."""
        return self.create_event(
            title=f"Applied: {company} - {job_title}",
            description=f"Job application submitted to {company} for {job_title} position.",
            location="",
            start_time=applied_date,
            duration_minutes=30,
            reminder_minutes=0
        )


# Singleton instance
calendar_service = CalendarService()
