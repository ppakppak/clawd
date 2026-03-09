#!/usr/bin/env python3
"""
KOCCA Track A 사업신청서 ODT 자동 채우기 v2
XML 파싱 기반 — span으로 쪼개진 텍스트도 처리
"""

import zipfile
import shutil
import os
import re
from pathlib import Path
from xml.etree import ElementTree as ET

SRC = Path("/home/ppak/clawd/kocca-proposal/track-a/1-1_실증.odt")
OUT = Path("/home/ppak/clawd/kocca-proposal/track-a/1-1_사업신청서_인튜웍스_실증.odt")
WORK = Path("/tmp/odt_fill_v2")

# 치환 매핑: (검색 키워드, 새 텍스트)
# 키워드가 포함된 <p> 요소의 전체 텍스트를 교체
REPLACEMENTS = [
    # (키워드 (이 텍스트가 포함된 paragraph를 찾음), 새 텍스트)
    ("e나라도움 사업명과 통일", 
     "AI 화풍변환 기반 ToonStyle AI 플랫폼 실증 콘텐츠 제작"),
    
    ("핵심이 되는 인공지능 기술 요약",
     "SDXL + LoRA 미세조정 기반 작가별 화풍 학습 엔진 (자체 개발). ControlNet·IP-Adapter 통합으로 원본 구조 보존 화풍 변환 AI 파이프라인"),
    
    ("핵심 기능, 콘텐츠 활용",
     "사진 업로드 → 7080 만화작가 화풍 선택 → AI 변환 결과물 생성. 웹 기반 SaaS로 일반 사용자·크리에이터·기업이 한국 고유 화풍 콘텐츠를 즉시 제작"),

    ("B2B+B2C 병행 등",
     "B2B+B2C 병행 (B2C: SNS 크리에이터·일반 이용자, B2B: 콘텐츠 제작사·마케팅 에이전시·문화기관)"),

    ("PoC, 베타 서비스, 현장 적용",
     "PoC 완료 → 클로즈드 베타(8월) → 오픈 베타 서비스(9월) → 콘텐츠 제작 현장 적용 3건"),

    ("인터랙티브 VR 콘서트",
     "AI 화풍변환 이미지 콘텐츠 (캐릭터 프로필, SNS 콘텐츠, 굿즈 디자인, 전시 체험용)"),

    ("어떻게 쓰였는지 작성",
     "① SNS 크리에이터 협업: 화풍 변환 콘텐츠 시리즈 제작 ② 기업 마케팅: 캐릭터 굿즈·프로필 제작 ③ 문화기관: 7080 만화 전시·체험 콘텐츠"),

    ("정량화)로 작성",
     "AI 화풍변환 이미지 10,000건 이상, 실증 콘텐츠 3종, 작가 화풍 모델 5종"),

    ("기반이 되는 인공지능 기술 요약",
     "SDXL + LoRA 미세조정 기반 작가별 화풍 학습 엔진. ControlNet·IP-Adapter 통합 화풍 변환 파이프라인 (자체 개발)"),
]


def get_full_text(elem):
    """요소의 전체 텍스트 (자식 span 포함)"""
    return ''.join(elem.itertext())


def replace_paragraph_text(elem, new_text, ns_map):
    """paragraph 요소의 텍스트를 새 텍스트로 교체 (첫 번째 span 스타일 유지)"""
    # 첫 번째 span의 스타일을 기억
    first_span = None
    for child in elem:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'span':
            first_span = child
            break
    
    # 모든 자식 요소 제거
    for child in list(elem):
        elem.remove(child)
    
    # 기존 tail 제거
    elem.text = None
    
    if first_span is not None:
        # span 스타일 유지하면서 새 텍스트
        ns_text = None
        for prefix, uri in ns_map.items():
            if 'text' in uri.lower() and 'opendocument' in uri.lower():
                ns_text = uri
                break
        
        if ns_text:
            new_span = ET.SubElement(elem, f'{{{ns_text}}}span')
            style_attr = None
            for attr_name in first_span.attrib:
                if 'style-name' in attr_name:
                    style_attr = attr_name
                    break
            if style_attr:
                new_span.set(style_attr, first_span.get(style_attr))
            new_span.text = new_text
        else:
            elem.text = new_text
    else:
        elem.text = new_text


def fill_odt():
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    
    extract_dir = WORK / "extracted"
    
    with zipfile.ZipFile(SRC, 'r') as z:
        z.extractall(extract_dir)
    
    content_path = extract_dir / "content.xml"
    
    # XML 파싱 (namespace 보존)
    ET.register_namespace('', 'urn:oasis:names:tc:opendocument:xmlns:office:1.0')
    tree = ET.parse(content_path)
    root = tree.getroot()
    
    # namespace map 추출
    ns_map = {}
    for event, elem in ET.iterparse(str(content_path), events=['start-ns']):
        ns_map[elem[0]] = elem[1]
    
    # 다시 파싱
    tree = ET.parse(content_path)
    root = tree.getroot()
    
    replaced = 0
    
    # 모든 paragraph 요소 순회
    for elem in root.iter():
        tag_local = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag_local in ('p', 'h'):
            full_text = get_full_text(elem)
            
            for keyword, new_text in REPLACEMENTS:
                if keyword in full_text:
                    old_preview = full_text[:80]
                    replace_paragraph_text(elem, new_text, ns_map)
                    print(f"  ✅ [{old_preview}...] → [{new_text[:60]}...]")
                    replaced += 1
                    break  # 하나의 paragraph에는 하나의 치환만
    
    # 저장
    tree.write(content_path, encoding='unicode', xml_declaration=True)
    
    # ODT 재압축 (mimetype 먼저, 압축 없이)
    with zipfile.ZipFile(OUT, 'w') as zout:
        mimetype_path = extract_dir / 'mimetype'
        if mimetype_path.exists():
            zout.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)
        
        for root_dir, dirs, files in os.walk(extract_dir):
            for f in files:
                file_path = Path(root_dir) / f
                arcname = file_path.relative_to(extract_dir)
                if str(arcname) != 'mimetype':
                    zout.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED)
    
    print(f"\n✅ 완료: {OUT}")
    print(f"   치환 {replaced}/{len(REPLACEMENTS)}개")
    print(f"   파일 크기: {OUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    fill_odt()
