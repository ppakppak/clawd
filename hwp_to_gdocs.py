#!/usr/bin/env python3
"""
HWP → Google Docs 변환기
HWP 파일을 읽어서 Google Docs에 동일한 내용으로 문서 생성
"""

import os
import sys
import subprocess
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# 설정
SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]
TOKEN_PATH = Path.home() / '.credentials' / 'google_token.json'
HWP5TXT_PATH = Path.home() / '.local/bin/hwp5txt'


def get_credentials():
    """저장된 OAuth 토큰 로드"""
    if not TOKEN_PATH.exists():
        print("❌ Google 인증 필요. 먼저 google_docs.py auth 실행하세요.")
        sys.exit(1)
    
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, 'w') as f:
                f.write(creds.to_json())
        else:
            print("❌ 토큰 만료됨. google_docs.py auth 다시 실행하세요.")
            sys.exit(1)
    
    return creds


def extract_hwp_text(hwp_path):
    """HWP 파일에서 텍스트 추출"""
    hwp_path = Path(hwp_path)
    
    if not hwp_path.exists():
        print(f"❌ 파일 없음: {hwp_path}")
        sys.exit(1)
    
    if not HWP5TXT_PATH.exists():
        print(f"❌ hwp5txt 없음: {HWP5TXT_PATH}")
        print("   설치: pip3 install --user pyhwp")
        sys.exit(1)
    
    print(f"📄 HWP 읽는 중: {hwp_path.name}")
    
    result = subprocess.run(
        [str(HWP5TXT_PATH), str(hwp_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"⚠️ 경고: {result.stderr[:200]}")
    
    text = result.stdout
    
    # 기본 정리
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # 경고 메시지 제거
        if 'undefined' in line.lower() or 'defined name/values' in line:
            continue
        cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    print(f"   ✅ 추출 완료: {len(text):,} 글자")
    
    return text


def create_google_doc(creds, title, content):
    """Google Docs 문서 생성 및 내용 추가"""
    docs_service = build('docs', 'v1', credentials=creds)
    
    # 문서 생성
    print(f"\n📝 Google Docs 생성 중: {title}")
    doc = docs_service.documents().create(body={'title': title}).execute()
    doc_id = doc.get('documentId')
    
    # 내용 삽입 (끝에서부터 역순으로 삽입하면 인덱스 문제 방지)
    # Google Docs는 한 번에 너무 긴 텍스트를 넣으면 문제가 생길 수 있음
    # 청크로 나누어 삽입
    
    CHUNK_SIZE = 50000  # 약 50KB씩
    chunks = [content[i:i+CHUNK_SIZE] for i in range(0, len(content), CHUNK_SIZE)]
    
    print(f"   내용 삽입 중... ({len(chunks)} 청크)")
    
    for i, chunk in enumerate(chunks):
        requests = [{
            'insertText': {
                'location': {'index': 1},
                'text': chunk if i == len(chunks) - 1 else chunk
            }
        }]
        
        # 역순으로 삽입 (마지막 청크부터)
    
    # 전체를 한 번에 삽입 (역순)
    for i, chunk in enumerate(reversed(chunks)):
        requests = [{
            'insertText': {
                'location': {'index': 1},
                'text': chunk
            }
        }]
        
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
    
    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"   ✅ 생성 완료!")
    print(f"\n🔗 URL: {url}")
    
    return doc_id, url


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("HWP → Google Docs 변환기")
        print("=" * 60)
        print("\n사용법:")
        print("  python3 hwp_to_gdocs.py <hwp_file> [문서제목]")
        print("\n예시:")
        print("  python3 hwp_to_gdocs.py 제안서.hwp")
        print("  python3 hwp_to_gdocs.py 제안서.hwp 'AX 제안서 백업'")
        sys.exit(1)
    
    hwp_path = sys.argv[1]
    
    # 제목 결정 (인자로 주어지면 사용, 아니면 파일명)
    if len(sys.argv) > 2:
        title = sys.argv[2]
    else:
        title = Path(hwp_path).stem + " (Google Docs)"
    
    print("=" * 60)
    print("HWP → Google Docs 변환")
    print("=" * 60)
    
    # 1. 인증
    print("\n[1/3] Google 인증...")
    creds = get_credentials()
    print("   ✅ 인증 성공")
    
    # 2. HWP 텍스트 추출
    print("\n[2/3] HWP 파일 읽기...")
    content = extract_hwp_text(hwp_path)
    
    # 3. Google Docs 생성
    print("\n[3/3] Google Docs 생성...")
    doc_id, url = create_google_doc(creds, title, content)
    
    print("\n" + "=" * 60)
    print("✅ 변환 완료!")
    print("=" * 60)
    print(f"\n원본: {hwp_path}")
    print(f"복사본: {url}")


if __name__ == "__main__":
    main()
