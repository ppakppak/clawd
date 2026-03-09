#!/usr/bin/env python3
"""
KOCCA Track A 사업신청서 ODT 자동 채우기
ODT = ZIP(content.xml) → XML 텍스트 치환 → 재압축
"""

import zipfile
import shutil
import os
from pathlib import Path

# 경로 설정
SRC = Path("/home/ppak/clawd/kocca-proposal/track-a/1-1_실증.odt")
OUT = Path("/home/ppak/clawd/kocca-proposal/track-a/1-1_사업신청서_인튜웍스_실증.odt")
WORK = Path("/tmp/odt_fill_work")

# 치환 매핑 (원본 텍스트 → 채울 텍스트)
# 주의: ODT XML에서 정확한 텍스트 매칭 필요
REPLACEMENTS = {
    # === 신청서 표지/기본사항 ===
    # 과제명 (사업개요 섹션)
    "(인공지능 기술 ~) 기반 (~ 플랫폼/설루션) 실증 (~ 콘텐츠) 제작  * e나라도움 사업명과 통일, 30자 이내로":
        "AI 화풍변환 기반 ToonStyle AI 플랫폼 실증 콘텐츠 제작",

    # 과제 진척도
    "00%": "15%",

    # === 과제 내용 ===
    # AI 기술 요약
    "플랫폼/설루션 제작에 핵심이 되는 인공지능 기술 요약(2줄 이내)":
        "Stable Diffusion XL + LoRA 미세조정 기반 작가별 화풍 학습 엔진. ControlNet·IP-Adapter 통합으로 원본 구조 보존하며 화풍만 변환하는 자체 개발 AI 파이프라인",

    # 플랫폼 명칭
    "플랫폼/설루션 명칭": "ToonStyle AI",

    # 플랫폼 내용
    "플랫폼/설루션의 핵심 기능, 콘텐츠 활용·제작 공정 내 역할 등 (2줄 이내)":
        "사진 업로드 → 7080 만화작가 화풍 선택 → AI 변환 결과물 생성. 웹 기반 SaaS로 일반 사용자·크리에이터·기업이 한국 고유 화풍 콘텐츠를 즉시 제작할 수 있는 플랫폼",

    # 실증 대상
    "B2B(콘텐츠 제작사, 스튜디오 등), B2C(일반 이용자, 크리에이터 등), B2B+B2C 병행 등":
        "B2B+B2C 병행 (B2C: SNS 크리에이터·일반 이용자, B2B: 콘텐츠 제작사·마케팅 에이전시·문화기관)",

    # 실증 방법
    "파일럿 적용, PoC, 베타 서비스, 현장 적용 등":
        "PoC 완료 후 클로즈드 베타 → 오픈 베타 서비스 → 콘텐츠 제작 현장 적용 (3건 이상)",

    # 실증 콘텐츠 형태
    "ex) 인터랙티브 VR 콘서트, 실감형 미디어아트 영상, AI 웹툰 등":
        "AI 화풍변환 이미지 콘텐츠 (캐릭터 프로필, SNS 콘텐츠, 굿즈 디자인, 전시 체험용 이미지)",

    # 실증 콘텐츠 내용
    "플랫폼/설루션이 콘텐츠 제작·활용에 어떻게 쓰였는지 작성":
        "① SNS 크리에이터 협업: 화풍 변환 콘텐츠 시리즈 제작·공개 ② 기업 마케팅: 캐릭터 굿즈·프로필 이미지 제작 ③ 문화기관: 7080 만화 전시·체험 콘텐츠 제작",

    # 실증 콘텐츠 분량
    "결과물을 수치(정량화)로 작성(A 콘텐츠 0분X0화(편), 0종 등)":
        "AI 화풍변환 이미지 10,000건 이상, 실증 사례 콘텐츠 3종, 작가 화풍 모델 5종",

    # === 사업계획서 본문 부분 ===
    # 과제에 기반이 되는 인공지능 기술 요약
    "과제에 기반이 되는 인공지능 기술 요약(2줄 이내), 자체 개발한 솔루션/플랫폼일 경우 명시":
        "SDXL + LoRA 미세조정 기반 작가별 화풍 학습 엔진 (자체 개발). ControlNet·IP-Adapter 통합으로 원본 구조 보존 화풍 변환 파이프라인",
}


def fill_odt():
    # 1. 작업 디렉토리 준비
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    
    extract_dir = WORK / "extracted"
    
    # 2. ODT 압축 해제
    with zipfile.ZipFile(SRC, 'r') as z:
        z.extractall(extract_dir)
    
    # 3. content.xml 읽기
    content_path = extract_dir / "content.xml"
    content = content_path.read_text(encoding='utf-8')
    
    # 4. 텍스트 치환
    replaced_count = 0
    for old_text, new_text in REPLACEMENTS.items():
        if old_text in content:
            content = content.replace(old_text, new_text)
            replaced_count += 1
            print(f"  ✅ 치환: {old_text[:50]}...")
        else:
            print(f"  ⚠️ 미발견: {old_text[:50]}...")
    
    # 5. content.xml 저장
    content_path.write_text(content, encoding='utf-8')
    
    # 6. ODT 재압축
    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for root, dirs, files in os.walk(extract_dir):
            for f in files:
                file_path = Path(root) / f
                arcname = file_path.relative_to(extract_dir)
                # mimetype은 압축하지 않아야 함
                if str(arcname) == 'mimetype':
                    zout.write(file_path, arcname, compress_type=zipfile.ZIP_STORED)
                else:
                    zout.write(file_path, arcname)
    
    print(f"\n✅ 완료: {OUT}")
    print(f"   치환 {replaced_count}/{len(REPLACEMENTS)}개")


if __name__ == "__main__":
    fill_odt()
