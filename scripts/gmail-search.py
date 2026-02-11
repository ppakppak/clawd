#!/usr/bin/env python3
"""Search Gmail messages."""

import sys
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDS_DIR = Path.home() / 'clawd' / '.credentials'
TOKEN_FILE = CREDS_DIR / 'gmail-token.pickle'

def get_credentials():
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as f:
            creds = pickle.load(f)
        if creds and creds.valid:
            return creds
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            return creds
    raise Exception("No valid credentials. Run gmail-check.py first.")

def search_mail(query, max_results=10):
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    
    results = service.users().messages().list(
        userId='me', 
        q=query,
        maxResults=max_results
    ).execute()
    
    messages = results.get('messages', [])
    
    if not messages:
        print(f"검색 결과 없음: {query}")
        return
    
    print(f"🔍 '{query}' 검색 결과 {len(messages)}개:\n")
    
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
        
        print(f"• {sender}")
        print(f"  {subject}")
        print(f"  {date[:22]}")
        print()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: gmail-search.py <query> [max_results]")
        sys.exit(1)
    query = sys.argv[1]
    max_results = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    search_mail(query, max_results)
