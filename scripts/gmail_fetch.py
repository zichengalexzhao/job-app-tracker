# scripts/gmail_fetch.py
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define the Gmail API scope (read-only in this case)
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """
    Authenticates and returns a Gmail service instance.
    Checks for a saved token and, if not found or invalid, starts the OAuth flow.
    """
    creds = None
    # Check if token.json exists in the config folder
    if os.path.exists('config/token.json'):
        creds = Credentials.from_authorized_user_file('config/token.json', SCOPES)
    
    # If there are no valid credentials available, initiate the OAuth flow
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('config/gmail_credentials.json', SCOPES)
        creds = flow.run_local_server(port=8080)
        # Save the credentials for the next run
        with open('config/token.json', 'w') as token:
            token.write(creds.to_json())
    
    # Build and return the Gmail API service object
    return build('gmail', 'v1', credentials=creds)

def fetch_emails():
    """
    Fetches all email metadata (IDs and thread IDs) from the user's INBOX.
    Handles pagination to retrieve more than 100 messages if available.
    """
    service = get_gmail_service()
    all_messages = []
    response = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    messages = response.get('messages', [])
    all_messages.extend(messages)

    # Continue fetching if there's a nextPageToken
    while 'nextPageToken' in response:
        page_token = response['nextPageToken']
        response = service.users().messages().list(
            userId='me', 
            labelIds=['INBOX'], 
            pageToken=page_token
        ).execute()
        messages = response.get('messages', [])
        all_messages.extend(messages)

    return all_messages

def get_email_content(message_id):
    """
    Retrieves the full email content (or snippet) for a given message ID.
    Here we use the 'snippet' field for simplicity.
    """
    service = get_gmail_service()
    message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    return message.get('snippet', '')

if __name__ == '__main__':
    msgs = fetch_emails()
    print(f"Found {len(msgs)} messages")
    print("Messages:", msgs)
