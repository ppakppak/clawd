#!/usr/bin/env python3
"""
Google Docs API - OAuth 2.0 인증
"""

import os
import sys
import json
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 스코프 정의
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

TOKEN_PATH = Path.home() / '.credentials' / 'google_token.json'
CREDENTIALS_PATH = None  # 실행 시 설정


def get_credentials():
    """OAuth 2.0 인증"""
    creds = None
    
    # 저장된 토큰 확인
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    
    # 토큰이 없거나 만료됨
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 토큰 갱신 중...")
            creds.refresh(Request())
        else:
            print("🌐 브라우저에서 Google 로그인 필요...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 토큰 저장
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        print(f"✅ 토큰 저장: {TOKEN_PATH}")
    
    return creds


def create_doc(creds, title="새 문서"):
    """Google Doc 생성"""
    service = build('docs', 'v1', credentials=creds)
    doc = service.documents().create(body={'title': title}).execute()
    doc_id = doc.get('documentId')
    print(f"✅ 문서 생성: {title}")
    print(f"   URL: https://docs.google.com/document/d/{doc_id}/edit")
    return doc_id


def read_doc(creds, doc_id):
    """Google Doc 읽기"""
    service = build('docs', 'v1', credentials=creds)
    doc = service.documents().get(documentId=doc_id).execute()
    
    # 텍스트 추출
    content = doc.get('body', {}).get('content', [])
    text = ''
    for element in content:
        if 'paragraph' in element:
            for para_element in element['paragraph'].get('elements', []):
                if 'textRun' in para_element:
                    text += para_element['textRun'].get('content', '')
    
    return {
        'title': doc.get('title'),
        'text': text,
        'doc_id': doc_id
    }


def insert_text(creds, doc_id, text, index=1):
    """텍스트 삽입"""
    service = build('docs', 'v1', credentials=creds)
    
    requests = [{
        'insertText': {
            'location': {'index': index},
            'text': text
        }
    }]
    
    service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': requests}
    ).execute()
    
    print(f"✅ 텍스트 삽입 완료 ({len(text)} 글자)")


def list_docs(creds, max_results=10):
    """Google Docs 목록"""
    drive_service = build('drive', 'v3', credentials=creds)
    
    results = drive_service.files().list(
        q="mimeType='application/vnd.google-apps.document'",
        pageSize=max_results,
        fields="files(id, name, modifiedTime)"
    ).execute()
    
    files = results.get('files', [])
    print(f"\n📄 내 Google Docs ({len(files)}개):")
    for f in files:
        print(f"  - {f['name']}")
        print(f"    ID: {f['id']}")
        print(f"    수정: {f['modifiedTime']}")
    
    return files


def main():
    global CREDENTIALS_PATH
    
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python3 google_docs_oauth.py <client_secret.json> auth      # 최초 인증")
        print("  python3 google_docs_oauth.py <client_secret.json> list      # 문서 목록")
        print("  python3 google_docs_oauth.py <client_secret.json> create <제목>  # 문서 생성")
        print("  python3 google_docs_oauth.py <client_secret.json> read <doc_id>  # 문서 읽기")
        sys.exit(1)
    
    CREDENTIALS_PATH = Path(sys.argv[1])
    if not CREDENTIALS_PATH.exists():
        print(f"❌ 파일 없음: {CREDENTIALS_PATH}")
        sys.exit(1)
    
    command = sys.argv[2] if len(sys.argv) > 2 else 'auth'
    
    print("=" * 50)
    print("Google Docs API (OAuth 2.0)")
    print("=" * 50)
    
    # 인증
    creds = get_credentials()
    print("✅ 인증 성공!")
    
    if command == 'auth':
        print("\n인증 완료! 이제 다른 명령어를 사용할 수 있습니다.")
    
    elif command == 'list':
        list_docs(creds)
    
    elif command == 'create':
        title = sys.argv[3] if len(sys.argv) > 3 else "Clawdbot 문서"
        create_doc(creds, title)
    
    elif command == 'read':
        if len(sys.argv) < 4:
            print("❌ doc_id 필요")
            sys.exit(1)
        doc_id = sys.argv[3]
        result = read_doc(creds, doc_id)
        print(f"\n📄 제목: {result['title']}")
        print(f"\n내용:\n{result['text'][:500]}...")


if __name__ == "__main__":
    main()
