# gmail_fetch.py
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    token_path = 'config/token.json'
    creds_path = 'config/gmail_credentials.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    else:
        print(f"Warning: No token found at {token_path}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired, attempting to refresh...")
            creds.refresh(Request())
        elif os.path.exists(creds_path):
            print("No valid token; running local auth (not suitable for CI)...")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        else:
            raise FileNotFoundError(
                f"Authentication failed: No valid token at {token_path} and no credentials at {creds_path}"
            )

    return build('gmail', 'v1', credentials=creds)


def fetch_emails(since_hours=1):
    service = get_gmail_service()
    
    query = ""
    if since_hours is not None:
        time_threshold = (datetime.now() - timedelta(hours=since_hours)).strftime('%Y/%m/%d')
        query = f"after:{time_threshold}"
    print(f"Query: '{query}'")
    
    all_messages = []
    response = service.users().messages().list(userId='me', labelIds=['INBOX'], q=query, maxResults=500).execute()
    messages = response.get('messages', [])
    print(f"Initial page: {len(messages)} emails")
    all_messages.extend(messages or [])
    
    page_count = 1
    while 'nextPageToken' in response:
        page_count += 1
        page_token = response['nextPageToken']
        response = service.users().messages().list(
            userId='me', labelIds=['INBOX'], q=query, pageToken=page_token, maxResults=500
        ).execute()
        messages = response.get('messages', [])
        print(f"Page {page_count}: {len(messages)} emails")
        all_messages.extend(messages or [])
    
    print(f"Total emails fetched: {len(all_messages)}")
    return all_messages

def get_email_snippet(message_id):
    service = get_gmail_service()
    message = service.users().messages().get(userId='me', id=message_id, format='minimal').execute()
    return message.get('snippet', '')

def get_email_content(message_id):
    service = get_gmail_service()
    message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    payload = message.get('payload', {})
    parts = payload.get('parts', [])
    body = ""
    if parts:
        for part in parts:
            if part['mimeType'] == 'text/plain':
                body += part.get('body', {}).get('data', '')
    else:
        body = payload.get('body', {}).get('data', '')

    if body:
        import base64
        body = base64.urlsafe_b64decode(body).decode('utf-8', errors='ignore')
    else:
        body = message.get('snippet', '')

    headers = message.get('payload', {}).get('headers', [])
    from_header = next((h['value'] for h in headers if h['name'] == 'From'), '')
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
    full_content = f"From: {from_header}\nSubject: {subject}\n\n{body}"

    internal_date = int(message.get('internalDate', 0)) / 1000
    email_date = datetime.fromtimestamp(internal_date).strftime('%Y-%m-%d') if internal_date else 'Unknown'

    return {"content": full_content[:4000], "date": email_date}