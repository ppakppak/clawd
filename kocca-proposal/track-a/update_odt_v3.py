#!/usr/bin/env python3
"""ODT 업데이트 스크립트 v3 — txt2img + ControlNet + FaceID 파이프라인 반영.

2026-02-27: img2img→txt2img, 2-pass→단일패스, IP-Adapter→FaceID 전면 전환.
"""

import shutil
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

NS = {
    'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0',
}

for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

EXTRA_NS = {
    'draw': 'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0',
    'svg': 'urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0',
    'xlink': 'http://www.w3.org/1999/xlink',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'meta': 'urn:oasis:names:tc:opendocument:xmlns:meta:1.0',
    'number': 'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0',
    'presentation': 'urn:oasis:names:tc:opendocument:xmlns:presentation:1.0',
    'chart': 'urn:oasis:names:tc:opendocument:xmlns:chart:1.0',
    'dr3d': 'urn:oasis:names:tc:opendocument:xmlns:dr3d:1.0',
    'math': 'http://www.w3.org/1998/Math/MathML',
    'form': 'urn:oasis:names:tc:opendocument:xmlns:form:1.0',
    'script': 'urn:oasis:names:tc:opendocument:xmlns:script:1.0',
    'config': 'urn:oasis:names:tc:opendocument:xmlns:config:1.0',
    'ooo': 'http://openoffice.org/2004/office',
    'ooow': 'http://openoffice.org/2004/writer',
    'oooc': 'http://openoffice.org/2004/calc',
    'dom': 'http://www.w3.org/2001/xml-events',
    'xforms': 'http://www.w3.org/2002/xforms',
    'xsd': 'http://www.w3.org/2001/XMLSchema',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'rpt': 'http://openoffice.org/2005/report',
    'of': 'urn:oasis:names:tc:opendocument:xmlns:of:1.2',
    'xhtml': 'http://www.w3.org/1999/xhtml',
    'grddl': 'http://www.w3.org/2003/g/data-view#',
    'tableooo': 'http://openoffice.org/2009/table',
    'drawooo': 'http://openoffice.org/2010/draw',
    'calcext': 'urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0',
    'loext': 'urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0',
    'field': 'urn:openoffice:names:experimental:ooo-ms-interop:xmlns:field:1.0',
    'formx': 'urn:openoffice:names:experimental:ooxml-odf-interop:xmlns:form:1.0',
    'css3t': 'http://www.w3.org/TR/css3-text/',
}
for prefix, uri in EXTRA_NS.items():
    ET.register_namespace(prefix, uri)


def cell_text(cell):
    txt = []
    for p in cell.findall('.//text:p', NS):
        parts = []
        for t in p.iter():
            if t.text:
                parts.append(t.text)
        line = ''.join(parts).strip()
        if line:
            txt.append(line)
    return '\n'.join(txt)


def set_cell_text(cell, lines: list[str]):
    paragraphs = cell.findall('text:p', NS)
    if not paragraphs:
        return
    first_p = paragraphs[0]
    p_style = first_p.attrib.get(f"{{{NS['text']}}}style-name", "바탕글")
    first_span = first_p.find('text:span', NS)
    span_style = first_span.attrib.get(f"{{{NS['text']}}}style-name") if first_span is not None else None
    for p in paragraphs:
        cell.remove(p)
    for line in lines:
        p = ET.SubElement(cell, f"{{{NS['text']}}}p")
        p.set(f"{{{NS['text']}}}style-name", p_style)
        if span_style:
            span = ET.SubElement(p, f"{{{NS['text']}}}span")
            span.set(f"{{{NS['text']}}}style-name", span_style)
            span.text = line
        else:
            p.text = line


def get_table(body, style_name):
    for el in body:
        if el.tag == f"{{{NS['table']}}}table":
            if el.attrib.get(f"{{{NS['table']}}}style-name") == style_name:
                return el
    return None


def get_row_cell(table, row_idx, col_idx):
    rows = table.findall('table:table-row', NS)
    if row_idx >= len(rows):
        return None
    cells = rows[row_idx].findall('table:table-cell', NS)
    if col_idx >= len(cells):
        return None
    return cells[col_idx]


def main():
    src = Path('/home/ppak/clawd/kocca-proposal/track-a/1-1_사업신청서_인튜웍스_실증.odt')
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    bak = src.with_name(f'1-1_사업신청서_인튜웍스_실증_bak_{ts}.odt')
    shutil.copy2(src, bak)
    print(f"백업: {bak}")

    with zipfile.ZipFile(src) as z:
        content_xml = z.read('content.xml')

    root = ET.fromstring(content_xml)
    body = root.find('office:body', NS).find('office:text', NS)

    updated = []

    # ═══════════════════════════════════════════════
    # Table-26: 2-1 과제 개요
    # ═══════════════════════════════════════════════
    t26 = get_table(body, 'Table-26')
    if t26 is not None:
        # R2: 사업목적 및 기획방향
        c = get_row_cell(t26, 1, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 7080 만화작가 IP(이정문, 신문수 등)의 고유 화풍을 AI로 학습·재현하여 사진 기반 콘텐츠 제작을 자동화하는 플랫폼을 실증한다.",
                "- 자체 개발 AI 파이프라인(txt2img + ControlNet(Canny) + LoRA(fuse) + IP-Adapter-FaceID)을 통해 원본 사진의 구조와 얼굴 정체성을 보존하면서 작가 고유 화풍을 정밀 재현하며, 이를 웹 SaaS로 구현하여 실제 콘텐츠 제작 현장에서 사업성을 검증한다.",
                "- 웹 기반 프로토타입 구축·운영 중(2026.02). 68건 이상 변환 실적, ~4초/장 변환 속도로 기술적 실현 가능성 확인 완료. 본 과제를 통해 상용 수준의 SaaS 플랫폼으로 고도화한다.",
            ])

        # R3: 과제 주요내용
        c = get_row_cell(t26, 2, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 7080 만화작가 화풍 학습 모델을 구축하고, 사용자가 사진 업로드→작가/버전 선택→변환까지 수행 가능한 웹 기반 AI 플랫폼(ToonStyle AI)을 개발·실증한다.",
                "- txt2img 기반 단일 패스 파이프라인으로 화풍 재현(LoRA fuse) + 구조 보존(ControlNet Canny) + 얼굴 정체성 유지(IP-Adapter-FaceID)를 동시 처리. 작가 5인 이상 모델 확보 및 실증 3건 이상 수행을 목표로 한다.",
                "- PoC 실적: 2인 작가 모델(이정문·신문수) + LoRA 다중 버전(v1/v2/v2-strong) + 웹서비스 운영 + 68건 이상 변환 테스트 완료.",
            ])

        # R4: 차별성-기술수준
        c = get_row_cell(t26, 3, 2)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 자체 개발 txt2img + ControlNet + FaceID 통합 파이프라인으로 특정 작가 화풍을 50~100장 원화만으로 정밀 재현. 범용 AI(Midjourney 등)는 특정 작가 화풍 학습 불가.",
                "- img2img 방식의 한계(원본 픽셀 잔류로 스타일 저하)를 극복한 txt2img 설계: Canny 엣지만 구조 가이드로 전달하여 LoRA 화풍 자유도 극대화.",
                "- InsightFace 512d 얼굴 임베딩 + IP-Adapter-FaceID로 화풍 변환 후에도 인물 식별 가능(화풍 9/10, 얼굴 7/10).",
                "- 정식 IP 라이선싱으로 저작권 리스크 제로. LoRA 다중 버전(v1/v2/v2-strong)으로 화풍 강도 선택 가능.",
            ])

        # R5: 제작·활용방식
        c = get_row_cell(t26, 4, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 웹에서 사진 업로드 → 작가/LoRA 버전 선택 → AI 변환(~4초, 단일 패스) → 결과 다운로드/갤러리 저장. 프리셋 5종으로 최적 파라미터 즉시 적용 가능.",
                "- 파라미터(FaceID 강도, ControlNet 강도, 가이던스 등) 직접 조절 UI 제공. 기존 만화 작가 직접 작화 대비 시간 99.9% 단축(수 시간→~4초). B2B API 연동으로 외부 서비스 자동화 가능.",
            ])

        # R6: 활용 범위
        c = get_row_cell(t26, 5, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ SNS/유튜브 크리에이터 콘텐츠, 기업 마케팅·브랜딩, 전시·교육 체험형 콘텐츠, 출판/디자인 시안 제작 등으로 확장 가능.",
                "- 작가 IP 추가에 따라 활용 분야를 지속 확대. LoRA 다중 버전(기본/밸런스/최대 화풍)으로 용도별 최적 결과 제공.",
            ])

        # R7: 사업성
        c = get_row_cell(t26, 6, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ B2C 구독형(월 9,900~29,900원) + B2B API 라이선스(월 100만~500만원) + IP 라이선싱 연계의 복합 수익모델 적용.",
                "- 글로벌 AI 이미지 생성 시장 2028년 약 80억 달러 전망(CAGR 52%). K-콘텐츠 글로벌 확산 흐름과 레트로 콘텐츠 수요 기반, 한국 고유 만화 IP 특화 서비스로 차별화된 시장 진입 가능.",
            ])

        # R8: 기대효과
        c = get_row_cell(t26, 7, 1)
        if c is not None:
            set_cell_text(c, [
                "① 한국 고유 만화 IP의 디지털 전환 및 재사업화 촉진",
                "② AI 기반 콘텐츠 제작 생태계 확장, 창작자 친화적 생성형 AI 활용 모델 제시",
                "③ 제작시간·비용 절감에 따른 창작 효율 향상(수 시간→~4초/장, 단일 패스)",
                "④ 신규 일자리 창출(AI 엔지니어, 콘텐츠 기획) 및 후속 투자 연계",
            ])
        updated.append("Table-26 (2-1 과제 개요)")
    else:
        print("⚠️  Table-26 not found")

    # ═══════════════════════════════════════════════
    # Table-30: 3. 세부 제작계획
    # ═══════════════════════════════════════════════
    t30 = get_table(body, 'Table-30')
    if t30 is not None:
        # R1: 플랫폼/솔루션
        c = get_row_cell(t30, 0, 2)
        if c is not None:
            set_cell_text(c, [
                "ㅇ ToonStyle AI 웹 플랫폼 — 프로토타입 운영 중(2026.02). 사진 업로드→작가/버전 선택→단일 패스 AI 변환(txt2img + ControlNet + FaceID)→갤러리 관리까지 웹 UI 동작 확인.",
                "- 현재 2인 작가 모델(이정문·신문수) + LoRA 3종 버전(v1/v2/v2-strong) 탑재. 본 과제에서 5인 이상으로 확장.",
                "- FastAPI 백엔드 + Tailwind CSS 프론트엔드 + GPU 추론 인프라. 프리셋 5종, FaceID/ControlNet 강도 슬라이더, 변환 이력 갤러리, B2B API. 변환 속도 ~4초/장(1024px).",
            ])

        # R2: 실증 콘텐츠
        c = get_row_cell(t30, 1, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 실증 3트랙: ① SNS/유튜브 크리에이터 협업 화풍 변환 콘텐츠 시리즈 ② 기업 마케팅용 캐릭터 굿즈·프로필·홍보 이미지 ③ 7080 만화 전시·체험 콘텐츠.",
                "- PoC 단계에서 이미 68건 이상 변환 테스트 완료. 실증기간 중 10,000건 이상 생성, 분야별 적용사례 리포트 작성.",
            ])

        # R3: 콘텐츠 품질 개선 요소
        c = get_row_cell(t30, 2, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ txt2img 기반 설계로 원본 픽셀 잔류 없이 순수 화풍 생성 — img2img 대비 스타일 재현도 대폭 향상(화풍 점수 9/10 달성).",
                "- ControlNet(Canny)으로 원본 구조(윤곽·포즈) 보존 + InsightFace FaceID로 얼굴 정체성 유지. 단일 패스로 화풍·구조·얼굴 동시 처리.",
                "- LoRA 다중 버전(v1 기본/v2 밸런스/v2-strong 최대 화풍) + 프리셋 시스템으로 품질 일관성 유지.",
            ])
        updated.append("Table-30 (3. 세부 제작계획)")
    else:
        print("⚠️  Table-30 not found")

    # ═══════════════════════════════════════════════
    # Table-31: 4. AI 기술 활용 계획
    # ═══════════════════════════════════════════════
    t31 = get_table(body, 'Table-31')
    if t31 is not None:
        # R1: AI 기술 설명
        c = get_row_cell(t31, 0, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 자체 개발 단일 패스 AI 화풍 변환 파이프라인을 핵심 엔진으로 구축. txt2img 방식으로 원본 사진 픽셀을 직접 사용하지 않고, 구조(Canny 엣지)와 얼굴(FaceID 임베딩)만 추출하여 가이드로 전달함으로써 LoRA 화풍 재현도를 극대화하는 설계.",
                "",
                "- txt2img + LoRA(fuse): 작가 화풍을 학습한 LoRA 가중치를 SDXL UNet에 직접 fuse하여 텍스트 프롬프트 기반으로 이미지 생성. 원본 픽셀에 의한 스타일 간섭 제거.",
                "- ControlNet(Canny): 원본 사진에서 Canny 엣지맵을 추출하여 구도·윤곽 가이드로 전달(scale=0.65). 사진 구조 유지와 화풍 자유도의 최적 밸런스.",
                "- IP-Adapter-FaceID: InsightFace(buffalo_l)로 512차원 얼굴 임베딩 추출 → IP-Adapter-FaceID로 생성 과정에 주입(scale=0.40). 화풍 변환 후에도 인물 식별 가능.",
                "- LoRA 버전 시스템: 작가별 v1(기본)/v2(밸런스·epoch-6)/v2-strong(최대 화풍·epoch-8) 다중 버전 제공.",
                "",
                "- 작가 화풍 학습: 50~100장 원화로 SDXL LoRA 학습(dim=32, alpha=16). 이정문·신문수 2인 학습 완료, 본 과제에서 5인 이상 확장.",
            ])

        # R2: AI 활용 효과
        c = get_row_cell(t31, 1, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 기존 만화 작가 직접 작화 시 1컷당 수 시간~수일 소요 → AI 변환으로 ~4초/장으로 단축(제작시간 99.9% 이상 절감).",
                "- 기존 범용 AI(Midjourney, ChatGPT 등)로는 특정 작가 고유 화풍을 재현할 수 없음. 본 기술은 50~100장 원화만으로 작가별 화풍을 정밀 학습하여, 정식 라이선스 기반의 작가 특화 변환을 가능하게 함.",
                "- 기존 img2img 방식의 한계(원본 픽셀 잔류로 화풍 재현 저하)를 txt2img + ControlNet 설계로 근본 해결 — LoRA 스타일 재현도 9/10 달성.",
                "- InsightFace FaceID 기반 얼굴 보존으로 화풍 변환 후에도 인물 식별 가능(얼굴 보존 7/10). 기존 IP-Adapter 스타일 참조 방식 대비 얼굴 특화 성능 향상.",
            ])
        updated.append("Table-31 (4. AI 기술 활용 계획)")
    else:
        print("⚠️  Table-31 not found")

    # ═══════════════════════════════════════════════
    # Table-32: (4-1) AI 기술 기능 상세
    # ═══════════════════════════════════════════════
    t32 = get_table(body, 'Table-32')
    if t32 is not None:
        c = get_row_cell(t32, 0, 0)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 자체 개발 단일 패스 txt2img + ControlNet + FaceID 통합 파이프라인을 핵심 엔진으로, 원본 사진 픽셀을 사용하지 않는 설계로 LoRA 화풍 재현도를 극대화하면서 구조·얼굴 보존을 동시 확보",
                "- 기존 작가 직접 작화(수 시간/건) → AI 변환(~4초/건)으로 콘텐츠 제작 시간 99.9% 단축. 50~100장 원화로 작가 화풍 학습 가능",
                "",
                "기술 내역 | 콘텐츠 제작 단계 | 활용 방식 | 주요 내용",
                "SDXL txt2img + LoRA(fuse)(자체 개발) | AI 모델 학습/화풍 변환 추론 | 작가별 화풍 학습 및 txt2img 변환 | 원화 50~100장으로 학습. LoRA를 UNet에 fuse하여 화풍 자유 생성. 다중 버전(v1/v2/v2-strong) 제공",
                "ControlNet(Canny) | 구조 가이드 | 원본 사진의 Canny 엣지맵으로 구도·윤곽 유지 | control_strength 0.65에서 최적 밸런스. 원본 픽셀 직접 사용 않음",
                "IP-Adapter-FaceID(InsightFace) | 얼굴 정체성 보존 | 512d 얼굴 임베딩을 생성 과정에 주입 | faceid_scale 0.40에서 화풍 9/10 + 얼굴 7/10 동시 달성",
                "자동 캡셔닝 + 품질 평가 | 데이터 전처리/결과물 검증 | 이미지별 자동 분석 캡션 생성 + 품질 스코어링 | 트리거 워드 방식. SSIM·LPIPS·FID 자동 평가",
            ])
        updated.append("Table-32 (4-1 AI 기술 기능 상세)")
    else:
        print("⚠️  Table-32 not found")

    # ═══════════════════════════════════════════════
    # Table-34: (4-2) AI 기술 도식화
    # ═══════════════════════════════════════════════
    t34 = get_table(body, 'Table-34')
    if t34 is not None:
        c = get_row_cell(t34, 0, 0)
        if c is not None:
            set_cell_text(c, [
                "[추론 파이프라인 — 단일 패스 변환]",
                "",
                "[사용자 입력]",
                "  사진 업로드 / 화백·버전 선택 / 파라미터 조절",
                "       │",
                "       ▼",
                "┌─── AI 변환 파이프라인 (단일 패스, ~4초) ───┐",
                "│                                           │",
                "│  원본 사진 → Canny Edge 추출               │",
                "│       └→ ControlNet (scale=0.65)          │",
                "│           구도·윤곽 가이드                  │",
                "│                    ↓                      │",
                "│  원본 얼굴 → InsightFace (buffalo_l)       │",
                "│       └→ 512d 임베딩 → FaceID (scale=0.40)│",
                "│           얼굴 정체성 주입                  │",
                "│                    ↓                      │",
                "│        SDXL txt2img + LoRA (fuse)         │",
                "│        guidance=8.0 / steps=30            │",
                "│        → 화풍 변환 이미지 생성               │",
                "└───────────────────────────────────────────┘",
                "       │",
                "       ▼",
                "[출력] 화풍 변환 이미지 다운로드 / 갤러리 저장",
                "",
                "※ 핵심: 원본 사진 픽셀을 직접 사용하지 않음(img2img ✕).",
                "  Canny 엣지(구조)와 FaceID 임베딩(얼굴)만 추출하여",
                "  가이드로 전달 → LoRA 화풍 재현도 극대화.",
                "",
                "[모델 학습 파이프라인]",
                "작가 원화(50~100장) → 이미지별 자동 분석 캡셔닝",
                "(컬러/흑백·배경·구도 분석, 트리거 워드 삽입)",
                "→ SDXL LoRA 학습(dim=32, alpha=16, ~40분/작가)",
                "→ TensorBoard 모니터링 + epoch별 과적합 검출",
                "→ 작가 화풍 모델 다중 버전(v1/v2/v2-strong)",
            ])
        updated.append("Table-34 (4-2 AI 기술 도식화)")
    else:
        print("⚠️  Table-34 not found")

    # ═══════════════════════════════════════════════
    # Write back
    # ═══════════════════════════════════════════════
    new_content = ET.tostring(root, encoding='unicode', xml_declaration=False)
    new_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + new_content

    with zipfile.ZipFile(src, 'r') as zin:
        with zipfile.ZipFile(str(src) + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == 'content.xml':
                    zout.writestr(item, new_content.encode('utf-8'))
                else:
                    zout.writestr(item, zin.read(item.filename))

    Path(str(src) + '.tmp').replace(src)

    print(f"\n✅ ODT v3 업데이트 완료!")
    print(f"📦 백업: {bak}")
    print(f"📝 반영된 테이블:")
    for t in updated:
        print(f"   ✏️  {t}")


if __name__ == '__main__':
    main()
