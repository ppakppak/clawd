#!/usr/bin/env python3
"""
KOCCA Track A 사업신청서 ODT 자동 채우기 v3
초안 v2 기반 — 전체 섹션 채우기
"""

import zipfile
import shutil
import os
from pathlib import Path
from xml.etree import ElementTree as ET

SRC = Path("/home/ppak/clawd/kocca-proposal/track-a/1-1_실증.odt")
OUT = Path("/home/ppak/clawd/kocca-proposal/track-a/1-1_사업신청서_인튜웍스_실증.odt")
WORK = Path("/tmp/odt_fill_v3")

# ── 인덱스 기반 치환 맵 ──
# (paragraph_index, new_text) — 1-indexed, 해당 인덱스의 paragraph 전체 텍스트를 교체
INDEX_REPLACEMENTS = {
    # === Ⅰ. 사업신청서 [표지] ===
    # 1. 기본사항 — 주관기관
    # 기관명 칸 (현재 빈칸 or placeholder)
    # 대표자
    163: "박영기",
    # 사업자번호 (아직 미확인)
    165: "(확인 필요)",
    # 설립일자
    167: "(확인 필요)",

    # 2. 사업개요
    # 과제명
    66: "AI 화풍변환 콘텐츠 플랫폼 \"ToonStyle AI\" 실증 제작",
    # 과제 진척도
    69: "30%",
    # AI 기술
    71: "SDXL + LoRA 미세조정 기반 작가별 화풍 학습 엔진(자체 개발). ControlNet·IP-Adapter 통합으로 원본 구조 보존 화풍 변환 AI 파이프라인 구축",
    # 플랫폼 명칭
    74: "ToonStyle AI",
    # 플랫폼 내용
    76: "사진 업로드 → 7080 만화작가 화풍 선택 → AI 변환 결과물 즉시 생성. 웹 기반 SaaS로 일반 사용자·크리에이터·기업이 한국 고유 화풍 콘텐츠를 제작",
    # 실증 대상
    78: "B2B+B2C 병행 (B2C: SNS 크리에이터·일반 이용자 / B2B: 콘텐츠 제작사·마케팅 에이전시·문화기관)",
    # 실증 방법
    80: "PoC 완료(이정문·신문수 화백 2인) → 클로즈드 베타(8월) → 오픈 베타 서비스(9월) → 콘텐츠 제작 현장 적용 3건",
    # 콘텐츠 형태
    82: "AI 화풍변환 이미지 콘텐츠 (캐릭터 프로필, SNS 콘텐츠, 굿즈 디자인, 전시 체험용 콘텐츠)",
    # 콘텐츠 내용
    84: "① SNS 크리에이터 협업: 7080 화풍 변환 콘텐츠 시리즈 제작  ② 기업 마케팅: 캐릭터 굿즈·프로필 이미지 제작  ③ 문화기관: 7080 만화 전시·체험 콘텐츠",
    # 분량·규격
    86: "AI 화풍변환 이미지 10,000건 이상, 실증 콘텐츠 3종, 작가 화풍 모델 5종 이상",
    # 기반 AI기술 (2번째)
    88: "SDXL + LoRA 미세조정 기반 작가별 화풍 학습 엔진. ControlNet·IP-Adapter 통합 화풍 변환 파이프라인(자체 개발)",

    # 3. 과제 성과목표(KPI) — 매출액
    101: "50,000천원",
    # 매출 및 투자유치 방안 
    102: "B2C 구독(월 9,900~29,900원) + B2B API 라이선스 + 굿즈 제작. 시드 투자 3~5억원 목표",
    # 총 직원 수
    106: "(확인 필요)",
    # 참여인력 수
    109: "6인",
    # 투자유치액
    111: "300,000천원",
    # 신규 일자리
    114: "2인",
    # 자체 성과목표
    116: "① 특허출원 1건(화풍변환 AI 파이프라인) ② 위즈데이터 IP 라이선싱 계약 1건 ③ 콘텐츠 실증 MOU 2건 ④ 플랫폼 MAU 1,000명 ⑤ 화풍 변환 10,000건",

    # 4. 사업비 — 주관기관
    128: "182,000,000",
    129: "18,000,000",
    130: "200,000,000",
    # 참여기관
    133: "18,000,000",
    134: "5,000,000",
    135: "23,000,000",

    # 서명란
    146: "2026년  02월  00일",
    147: "주식회사 인튜웍스의 장",
    148: "박영기",
    150: "위즈데이터의 장",
    151: "(확인 필요)",

    # === Ⅱ. 사업계획서 ===
    # 1. 수행기관 개요 — 주관기관
    # 주요연혁
    174: "ㅇ2025 AI 바우처 공급기업(과기부), 시장대응형 R&D 상수도관로 AI(중기부 공동기관)",
    175: "ㅇ2024 디딤돌 창업성장 기술개발(중기부 주관기관), 산학연 Collabo R&D 2단계(주관기관), 데이터바우처 공급기업",
    176: "ㅇ2023 산학연 Collabo R&D 1단계(주관기관), 창업도약패키지(주관기관), AI융합 지역특화산업(공급기업)",

    # 참여기관 주요연혁
    201: "ㅇ2025 7080 화백 IP 디지털 콘텐츠 사업화 추진",
    202: "ㅇ2024 이정문·신문수 등 만화작가 IP 라이선싱 계약 확대",
    203: "ㅇ2023 7080 만화 캐릭터 IP 사업 시작",

    # 2. 참여인력 — 주관기관
    # 과제책임자
    225: "박영기",
    226: "대표",
    227: "인튜웍스 / AI 솔루션 기업 대표",
    228: "AI 모델 개발 총괄, 과제 관리",
    229: "50%",
    230: "7.5개월",
    # 개발총괄
    233: "AI 엔진 개발, 기술 리드",
    234: "책임",
    # 기획
    237: "사업 관리, 콘텐츠 기획",

    # 3. 수행실적 — 주관기관 실적 1
    255: "과학기술정보통신부",
    256: "AI 바우처 지원사업",
    257: "산업안전 AI 관제 시스템 공급",
    258: "2021.4월 ~ 2021.10월",
    259: "300,000천원",
    261: "산업현장 실시간 AI 안전관리시스템(RASS) — 객체감지, 이상행동 탐지 VMS 솔루션 공급",
    # 실적 2
    262: "과학기술정보통신부",
    263: "AI융합 지역특화산업 지원사업",
    264: "AI 기술 공급(기업배정 5.76억)",
    265: "2022.5월 ~ 2023.12월",
    266: "576,000천원",
    268: "AI융합 지역특화산업 AI 기술 공급기업으로 참여, 컴퓨터비전·데이터 전처리 기술 제공",
    # 실적 3
    269: "중소벤처기업부",
    270: "산학연 Collabo R&D 1단계",
    271: "AI 기술개발 주관",
    272: "2023.5월 ~ 2023.12월",
    273: "30,000천원",
    275: "주관기관으로 AI 기반 기술개발 과제 수행",

    # 4. 콘텐츠 제작 경험 — ①콘텐츠 제작
    304: "2026",
    306: "ToonStyle AI PoC — 이정문·신문수 화백 화풍 변환",
    308: "이정문 화백(51장), 신문수 화백(90장) 원화를 SDXL LoRA로 학습하여 사진→만화풍 변환 PoC 개발. 최적 Denoising Strength 65% 도출",
    310: "‧SDXL + LoRA 미세조정으로 작가별 화풍 학습 (dim=32, alpha=16)",
    311: "‧img2img 파이프라인으로 사진 → 만화풍 변환, SSIM/PSNR 정량 평가",

    # ②플랫폼/솔루션 — 실적 1
    329: "2025",
    331: "iPipeCheck — 상수도관로 AI 자동진단 시스템",
    333: "‧ 상수도관로 CCTV 영상을 AI로 분석하여 부식·퇴적물·침입수 등 결함 자동 진단. 수자원기술(주) 공동 과제",
    335: "‧ YOLOv8 기반 결함 탐지 모델 학습·배포",
    336: "‧ 웹 기반 어노테이션 플랫폼 + 자동 리포트 생성",
    337: "‧ 관로 CCTV 영상 프레임 추출 → AI 추론 → 등급 판정 파이프라인",

    # 실적 2
    339: "2021",
    341: "RASS — 실시간 산업안전 AI 관제 시스템 (AI 바우처)",
    343: "‧ 산업현장 CCTV 실시간 AI 분석, 이상행동 탐지(낙상·폭력 등), 화상인증 특허(제10-1038706호) 적용",

    # 실적 3
    344: "2025",
    346: "CattleWatch AI — 소 발정탐지 AI 솔루션",
    348: "‧ YOLOv8 + Object Tracking + Behavior Classification. Jetson AGX Orin 엣지 추론. 승가 감지율 71.4%",

    # === 세부사업계획 ===
    # 2-1. 과제 개요
    # 과제명
    356: "AI 화풍변환 콘텐츠 플랫폼 \"ToonStyle AI\" 실증 제작",

    # 사업목적 및 기획방향 (예시 텍스트 교체)
    362: "ㅇ 한국 7080세대 대표 만화작가(이정문, 신문수 등)의 고유 화풍을 AI로 학습하여, 일반 사진을 해당 화풍으로 변환하는 콘텐츠 플랫폼 \"ToonStyle AI\"를 개발하고 실증한다.",
    363: "- SDXL 기반 LoRA 미세조정 파이프라인을 자체 개발·고도화하여, 작가별 화풍 특징을 정밀 재현하는 AI 엔진을 구축하고, ControlNet·IP-Adapter 통합으로 원본 구조를 보존하면서 화풍만 변환하는 기술을 완성한다. 이를 웹 기반 SaaS 플랫폼으로 서비스화하여, 콘텐츠 제작 현장에서 3건 이상의 실증을 수행하고 시장 진입 기반을 확보한다.",

    # 타 플랫폼 차별성 — 기술 수준
    369: "자체 개발 LoRA 미세조정 파이프라인으로 특정 작가 화풍을 50~100장 원화만으로 정밀 재현. 범용 AI(Midjourney 등)는 특정 작가 화풍 학습 불가. ControlNet+IP-Adapter 통합으로 원본 얼굴/포즈 보존율 SSIM 0.7 이상",
    # 제작·활용 방식
    371: "사진 업로드 → 작가 선택 → 강도 조절 → 즉시 변환. 기존 만화 제작(작가 직접 작화) 대비 시간 99% 단축(수 시간→수 초). API 연동으로 B2B 파트너 자동화 가능",
    # 활용 범위
    373: "SNS 크리에이터 콘텐츠, 기업 마케팅(캐릭터 굿즈/프로필), 교육/문화(전시 체험), 출판(표지 디자인) 등. 작가 IP 확장 시 활용 범위 무한 확대",
    # 사업성
    375: "B2C 구독(월 9,900~29,900원) + B2B API 라이선스(월 100만~500만원) + IP 라이선싱. 7080 세대 향수 + 글로벌 K-콘텐츠 수요로 높은 시장성. 위즈데이터 IP 정식 라이선싱으로 저작권 리스크 제로",
    # 기대효과
    377: "① 한국 고유 만화 IP의 디지털 콘텐츠화로 문화자산 가치 극대화 ② AI 콘텐츠 제작 도구 생태계 확대 ③ 7080 만화작가 IP의 글로벌 시장 진출 기반 마련 ④ 신규 일자리 창출(AI 엔지니어, 콘텐츠 기획)",

    # 수행관리체계 — 조직도 텍스트
    384: "대표",
    385: "박영기",
    386: "과제책임",
    387: "박영기",
    388: "AI 모델 개발팀",
    389: "플랫폼 개발팀",
    390: "사업관리/기획팀",
    391: "콘텐츠/IP팀(위즈데이터)",
    392: "• LoRA 파이프라인 고도화",
    393: "• ControlNet/IP-Adapter 통합",
    394: "• 웹 프론트엔드/백엔드",
    395: "• GPU 클라우드 인프라",
    396: "• 콘텐츠 기획/실증 코디",
    397: "• 사업비 관리/행정",
    398: "• IP 라이선싱 관리",
    399: "• 원화 큐레이션/품질 검수",

    # 컨소시엄 구성
    406: "주식회사 인튜웍스",
    407: "‧ 자체 개발 LoRA 미세조정 기반 화풍 변환 AI 엔진 개발",
    408: "‧ 웹 SaaS 플랫폼(Next.js + FastAPI) 구축 및 운영",
    409: "‧ ETRI 투자 설립 AI 전문 기업, 화상인증 특허 보유",
    410: "‧ AI 바우처·데이터바우처 공급기업 다수 수행",
    412: "‧ 7080 만화작가 원화 IP 제공 및 라이선싱 관리",
    413: "‧ 콘텐츠 기획·품질 검수·유통/마케팅 연계",
    414: "",
    415: "‧ 이정문, 신문수 등 7080 만화작가 IP 보유",
    416: "‧ 만화 캐릭터 IP 라이선싱 전문",

    # 지원금 관리 체계
    418: "ㅇ 인튜웍스 대표(박영기) 직접 지원금 관리 총괄, 복지혜 차장이 행정·회계 전담",
    419: "- 내부 결재: 대표 → 사업관리담당 2단계 결재. 월별 사업비 집행 내역 보고서 작성. 부정수급 방지를 위한 계좌분리 운영(사업비 전용계좌)",

    # 자부담금 조달 계획
    427: "ㅇ 인튜웍스 자부담금 18,000천원: 대표자(박영기) 인건비로 편성, 자체 자금으로 조달",
    428: "- 위즈데이터 자부담금 5,000천원: IP 라이선싱 관련 현물 출자 및 자체 자금 조달",

    # 3. 세부 제작계획 — 최종 결과물
    433: "ㅇ ToonStyle AI 웹 플랫폼: 사진 업로드→작가 화풍 선택→AI 변환→다운로드. 5인 이상 작가 화풍 모델 탑재",
    434: "- Next.js 프론트엔드 + FastAPI 백엔드 + GPU 클라우드 추론 인프라. B2B API 제공",
    # 실증 콘텐츠
    437: "ㅇ 실증1: SNS 크리에이터 협업 화풍 변환 콘텐츠 시리즈 / 실증2: 기업 마케팅용 캐릭터 굿즈·프로필 / 실증3: 7080 만화 전시·체험 콘텐츠",
    438: "- 총 10,000건 이상 화풍 변환 이미지 생성, 실증 사례 보고서 3건",
    # 품질 개선
    441: "ㅇ LoRA 미세조정으로 작가 고유 화풍 재현도 극대화 (범용 AI 대비 SSIM +0.15 향상)",
    442: "- ControlNet으로 원본 얼굴/포즈 구조 보존, IP-Adapter로 화풍 일관성 강화. 자동 품질 스코어링(SSIM, LPIPS, FID)으로 결과물 품질 관리",

    # 4. AI 기술 활용 계획
    # (4-1) 기술 테이블
    456: "ㅇ 자체 개발 SDXL LoRA 미세조정 파이프라인을 핵심 엔진으로, ControlNet·IP-Adapter 통합으로 원본 보존 화풍 변환 구현",
    457: "- 기존 작가 직접 작화(수 시간/건) → AI 변환(수 초/건)으로 콘텐츠 제작 시간 99% 단축. 50~100장 원화로 작가 화풍 학습 가능",
    462: "SDXL + LoRA 미세조정 엔진 (자체 개발)",
    463: "AI 모델 학습, 화풍 변환 추론",
    464: "작가별 원화 50~100장으로 화풍 학습(dim=32, alpha=16). Denoising Strength 조절로 변환 강도 제어. 최적값 65% 도출 (PoC 검증 완료)",
    465: "ControlNet + IP-Adapter 통합 모듈",
    466: "구조 보존 및 스타일 가이드",
    467: "얼굴 윤곽·포즈·깊이 정보를 유지하면서 화풍만 변환. 참조 이미지 기반 화풍 일관성 강화",
    468: "자동 캡셔닝 + 품질 평가 AI",
    469: "학습 데이터 전처리 + 결과물 검증",
    470: "BLIP-2/CogVLM 기반 원화 자동 캡션 생성. SSIM·LPIPS·FID 기반 자동 품질 스코어링",

    # 5. 상용화 계획
    477: "ㅇ B2C: 월정액 SaaS(월 9,900~29,900원, 변환 크레딧제) + 건별 결제(건당 1,000~3,000원)",
    478: "- B2B: 기업용 API 라이선스(월 100만~500만원). IP 라이선싱: 변환 결과물 상업 이용권(별도 협의). 굿즈 제작(건당 5,000~50,000원)",
    # 목표 소비층
    483: "ㅇ B2C: 7080 세대 향수를 가진 30~50대 + SNS 크리에이터(20~30대) + K-콘텐츠 글로벌 팬",
    484: "- B2B: 콘텐츠 제작사, 마케팅 에이전시, 문화기관(미술관·박물관), 교육기관",
    # 목표시장
    488: "ㅇ 국내: 한국 향수 콘텐츠 시장(7080 세대 3,000만명), AI 이미지 생성 시장(2028년 연 800억원 전망)",
    489: "- 해외: K-콘텐츠 글로벌 시장, 동남아·미주 한류 팬덤. 2027년 해외 서비스 런칭 목표",

    # 매출 계획
    504: "50,000,000",
    506: "300,000,000",

    # 일자리
    537: "2인",
    549: "주관기관(인튜웍스)",
    550: "정규직",
}

# ── 키워드 기반 치환 (인덱스가 변할 수 있는 경우 대비) ──
KEYWORD_REPLACEMENTS = [
    ("e나라도움 사업명과 통일", "AI 화풍변환 콘텐츠 플랫폼 \"ToonStyle AI\" 실증 제작"),
    ("핵심이 되는 인공지능 기술 요약", "SDXL + LoRA 미세조정 기반 작가별 화풍 학습 엔진(자체 개발). ControlNet·IP-Adapter 통합으로 원본 구조 보존 화풍 변환 AI 파이프라인"),
    ("플랫폼/설루션 명칭", "ToonStyle AI"),
    ("핵심 기능, 콘텐츠 활용", "사진 업로드 → 7080 만화작가 화풍 선택 → AI 변환 결과물 즉시 생성. 웹 기반 SaaS 플랫폼"),
    ("기반이 되는 인공지능 기술 요약", "SDXL + LoRA 미세조정 기반 작가별 화풍 학습 엔진. ControlNet·IP-Adapter 통합 화풍 변환 파이프라인(자체 개발)"),
]


def get_full_text(elem):
    return ''.join(elem.itertext())


def replace_text(elem, new_text, ns_map):
    """paragraph 내 텍스트를 교체 (첫 번째 span 스타일 유지)"""
    first_span = None
    for child in elem:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'span':
            first_span = child
            break

    style_attr_name = None
    style_attr_val = None
    if first_span is not None:
        for attr_name in first_span.attrib:
            if 'style-name' in attr_name:
                style_attr_name = attr_name
                style_attr_val = first_span.get(attr_name)
                break

    for child in list(elem):
        elem.remove(child)
    elem.text = None

    if style_attr_name and style_attr_val:
        ns_text = None
        for prefix, uri in ns_map.items():
            if 'text' in uri.lower() and 'opendocument' in uri.lower():
                ns_text = uri
                break
        if ns_text:
            new_span = ET.SubElement(elem, f'{{{ns_text}}}span')
            new_span.set(style_attr_name, style_attr_val)
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

    # namespace 수집
    ns_map = {}
    for event, elem in ET.iterparse(str(content_path), events=['start-ns']):
        ns_map[elem[0]] = elem[1]

    tree = ET.parse(content_path)
    root = tree.getroot()

    # 인덱스 맵 구축
    paragraphs = []
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag in ('p', 'h'):
            text = get_full_text(elem).strip()
            if text:
                paragraphs.append(elem)

    replaced_idx = 0
    replaced_kw = 0

    # 1) 인덱스 기반 치환
    for idx, new_text in INDEX_REPLACEMENTS.items():
        real_idx = idx - 1  # 0-based
        if 0 <= real_idx < len(paragraphs):
            old = get_full_text(paragraphs[real_idx]).strip()[:60]
            replace_text(paragraphs[real_idx], new_text, ns_map)
            replaced_idx += 1
            if replaced_idx <= 20:
                print(f"  [idx {idx}] {old}... → {new_text[:50]}...")

    # 2) 키워드 기반 치환 (인덱스 치환으로 안 잡힌 것만)
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag in ('p', 'h'):
            full_text = get_full_text(elem)
            for keyword, new_text in KEYWORD_REPLACEMENTS:
                if keyword in full_text:
                    # 이미 인덱스로 바뀌었는지 확인
                    current = get_full_text(elem).strip()
                    if keyword in current:
                        replace_text(elem, new_text, ns_map)
                        replaced_kw += 1
                        break

    # 저장
    tree.write(content_path, encoding='unicode', xml_declaration=True)

    # ODT 재압축
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
    print(f"   인덱스 치환: {replaced_idx}/{len(INDEX_REPLACEMENTS)}개")
    print(f"   키워드 치환: {replaced_kw}/{len(KEYWORD_REPLACEMENTS)}개")
    print(f"   파일 크기: {OUT.stat().st_size:,} bytes")

    # SynologyDrive에도 복사
    syn_dest = Path("/home/ppak/SynologyDrive/ykpark/wizdata/붙임2. 신청양식_26제작지원_진입형/2. 신청양식_26제작지원_진입형_실증(플랫폼설루션)/1. 사업수행(필수)/1-1_사업신청서_인튜웍스_실증.odt")
    shutil.copy2(OUT, syn_dest)
    print(f"   📂 SynologyDrive 복사 완료: {syn_dest.name}")


if __name__ == "__main__":
    fill_odt()
