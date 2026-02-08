#!/usr/bin/env python3
"""Check Gmail for unread messages."""

import os
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDS_DIR = Path.home() / 'clawd' / '.credentials'
CLIENT_SECRET = CREDS_DIR / 'google-oauth.json'
TOKEN_FILE = CREDS_DIR / 'gmail-token.pickle'

def get_credentials():
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as f:
            pickle.dump(creds, f)
    
    return creds

def check_unread(max_results=10):
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    
    # Get unread messages
    results = service.users().messages().list(
        userId='me', 
        q='is:unread is:inbox',
        maxResults=max_results
    ).execute()
    
    messages = results.get('messages', [])
    
    if not messages:
        print("📭 읽지 않은 메일 없음")
        return
    
    print(f"📬 읽지 않은 메일 {len(messages)}개:\n")
    
    for msg in messages:
        msg_data = service.users().messages().get(
            userId='me', 
            id=msg['id'], 
            format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()
        
        headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
        
        sender = headers.get('From', 'Unknown')
        subject = headers.get('Subject', '(제목 없음)')
        date = headers.get('Date', '')
        
        # Shorten sender
        if '<' in sender:
            sender = sender.split('<')[0].strip().strip('"')
        
        print(f"• {sender}")
        print(f"  {subject}")
        print(f"  {date[:16]}")
        print()

if __name__ == '__main__':
    import sys
    max_results = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    check_unread(max_results)
