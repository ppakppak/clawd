#!/usr/bin/env python3
"""ODT 업데이트 스크립트 — 2-1 과제개요 ~ 4. AI기술 활용 계획까지 반영."""

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

# Register all namespaces to avoid ns0/ns1 mangling
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)
# Additional namespaces from HWP-exported ODT
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
    """Extract plain text from a cell."""
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
    """Replace all <text:p> in cell with new lines, preserving first span style."""
    paragraphs = cell.findall('text:p', NS)
    if not paragraphs:
        return

    # Get first paragraph's style
    first_p = paragraphs[0]
    p_style = first_p.attrib.get(f"{{{NS['text']}}}style-name", "바탕글")

    # Get first span style if exists
    first_span = first_p.find('text:span', NS)
    span_style = first_span.attrib.get(f"{{{NS['text']}}}style-name") if first_span is not None else None

    # Remove all existing paragraphs
    for p in paragraphs:
        cell.remove(p)

    # Create new paragraphs
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
    """Find table by style name."""
    for el in body:
        if el.tag == f"{{{NS['table']}}}table":
            if el.attrib.get(f"{{{NS['table']}}}style-name") == style_name:
                return el
    return None


def get_row_cell(table, row_idx, col_idx):
    """Get cell at (row_idx, col_idx), 0-based."""
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

    # Read ODT
    with zipfile.ZipFile(src) as z:
        content_xml = z.read('content.xml')
        all_files = z.namelist()

    root = ET.fromstring(content_xml)
    body = root.find('office:body', NS).find('office:text', NS)
    children = list(body)

    # ─────────────────────────────────────────────
    # Table-26: 2-1 과제 개요 (index 95)
    # ─────────────────────────────────────────────
    t26 = get_table(body, 'Table-26')
    if t26 is not None:
        print("✏️  Table-26 (2-1 과제 개요) 업데이트...")

        # R2: 사업목적 및 기획방향 → col 1
        c = get_row_cell(t26, 1, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 7080 만화작가 IP(이정문, 신문수 등)의 고유 화풍을 AI로 학습·재현하여 사진 기반 콘텐츠 제작을 자동화하는 플랫폼을 실증한다.",
                "- 자체 개발 2-pass AI 파이프라인(Pass 1: SDXL-LoRA 화풍변환 → Pass 2: IP-Adapter 얼굴복원)에 ControlNet을 결합해 원본 구조 보존과 화풍 재현도를 동시 확보하고, 웹 SaaS 형태로 구현하여 실제 콘텐츠 제작 현장에서 사업성을 검증한다.",
                "- 이미 웹 기반 프로토타입을 구축·검증 완료(2026.02)하여 기술적 실현 가능성을 확인한 상태이며, 본 과제를 통해 상용 수준의 SaaS 플랫폼으로 고도화한다.",
            ])

        # R3: 과제 주요내용 → col 1
        c = get_row_cell(t26, 2, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 7080 만화작가 화풍 학습 모델을 구축하고, 사용자가 사진 업로드→작가 선택→변환까지 수행 가능한 웹 기반 AI 플랫폼(ToonStyle AI)을 개발·실증한다.",
                "- SDXL-LoRA 미세조정 + ControlNet + IP-Adapter 통합 2-pass 파이프라인으로 화풍 재현/원본 보존 성능을 고도화하고, 작가 5인 이상 모델 확보 및 실증 3건 이상(크리에이터·기업 마케팅·문화/교육) 수행을 목표로 한다.",
                "- 프로토타입 단계에서 이미 웹 서비스 동작, 2인 작가 모델(이정문·신문수) 탑재, 68건 이상 변환 테스트 완료, ~4초/장 변환 성능 확인.",
            ])

        # R4: 차별성-기술수준 → col 2
        c = get_row_cell(t26, 3, 2)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 자체 개발 2-pass 파이프라인(화풍변환+얼굴복원)으로 특정 작가 화풍을 50~100장 원화만으로 정밀 재현. 범용 AI(Midjourney 등)는 특정 작가 화풍 학습 불가.",
                "- ControlNet+IP-Adapter 통합으로 원본 얼굴/포즈 보존율 SSIM 0.7072 달성(4조합 파라미터 튜닝 검증 완료).",
                "- 정식 IP 라이선싱으로 저작권 리스크 제로.",
            ])

        # R5: 제작·활용방식 → col 1
        c = get_row_cell(t26, 4, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 웹에서 사진 업로드 → 작가/파라미터 선택 → 2-pass AI 변환(화풍+얼굴복원) → 결과 다운로드/갤러리 저장. 프리셋 시스템으로 최적 파라미터 저장·불러오기 지원.",
                "- 기존 만화 작가 직접 작화 대비 시간 99.9% 단축(수 시간→~4초). API 연동으로 B2B 파트너 자동화 가능.",
            ])

        # R6: 활용 범위 → col 1
        c = get_row_cell(t26, 5, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ SNS/유튜브 크리에이터 콘텐츠, 기업 마케팅·브랜딩, 전시·교육 체험형 콘텐츠, 출판/디자인 시안 제작 등으로 확장 가능.",
                "- 작가 IP 추가에 따라 활용 분야를 지속 확대. 비율 보존 모드·프리셋 시스템으로 다양한 콘텐츠 형식 대응.",
            ])

        # R7: 사업성 → col 1
        c = get_row_cell(t26, 6, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ B2C 구독형(월 9,900~29,900원) + B2B API 라이선스(월 100만~500만원) + IP 라이선싱 연계의 복합 수익모델 적용.",
                "- 국내 레트로 콘텐츠 수요와 K-콘텐츠 글로벌 확산 흐름을 기반으로 초기 시장 진입 후 확장성이 높음. 위즈데이터 IP 정식 라이선싱으로 저작권 리스크 제로.",
            ])

        # R8: 기대효과 → col 1
        c = get_row_cell(t26, 7, 1)
        if c is not None:
            set_cell_text(c, [
                "① 한국 고유 만화 IP의 디지털 전환 및 재사업화 촉진",
                "② AI 기반 콘텐츠 제작 생태계 확장, 창작자 친화적 생성형 AI 활용 모델 제시",
                "③ 제작시간·비용 절감에 따른 창작 효율 향상(수 시간→~4초/장)",
                "④ 신규 일자리 창출(AI 엔지니어, 콘텐츠 기획) 및 후속 투자 연계",
            ])
    else:
        print("⚠️  Table-26 not found")

    # ─────────────────────────────────────────────
    # Table-30: 3. 세부 제작계획 (index 102)
    # ─────────────────────────────────────────────
    t30 = get_table(body, 'Table-30')
    if t30 is not None:
        print("✏️  Table-30 (3. 세부 제작계획) 업데이트...")

        # R1: 플랫폼/솔루션 → col 1
        c = get_row_cell(t30, 0, 1)
        if c is not None:
            set_cell_text(c, [
                "플랫폼/설루션",
            ])
        c = get_row_cell(t30, 0, 2)
        if c is not None:
            set_cell_text(c, [
                "ㅇ ToonStyle AI 웹 플랫폼 구축 — 프로토타입 구동 검증 완료(2026.02). 사진 업로드→작가/파라미터 선택→2-pass AI 변환(화풍변환+얼굴복원)→갤러리 관리까지 웹 UI 동작 확인. 현재 2인 작가 모델(이정문·신문수) 탑재, 본 과제에서 5인 이상으로 확장.",
                "- FastAPI 백엔드 + Tailwind CSS 프론트엔드 + GPU 추론 인프라. 프리셋 시스템(작가별 최적 파라미터 저장/불러오기), 변환 이력 갤러리, B2B API 제공. 변환 속도 ~4초/장(1024px, 2-pass 기준).",
            ])

        # R2: 실증 콘텐츠 → col 1
        c = get_row_cell(t30, 1, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 실증 3트랙: ① SNS/유튜브 크리에이터 협업 화풍 변환 콘텐츠 시리즈 ② 기업 마케팅용 캐릭터 굿즈·프로필·홍보 이미지 ③ 7080 만화 전시·체험 콘텐츠.",
                "- PoC 단계에서 이미 68건 이상 변환 테스트 완료. 실증기간 중 10,000건 이상 생성, 분야별 적용사례 리포트(전/후 비교, 파라미터 최적화 결과, 사용자 피드백) 작성.",
            ])

        # R3: 콘텐츠 품질 개선 요소 → col 1
        c = get_row_cell(t30, 2, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 자체 개발 2-pass 파이프라인으로 \"화풍 재현\"과 \"얼굴 정체성 보존\"을 동시 달성 — Pass 1에서 LoRA 기반 화풍 변환, Pass 2에서 IP-Adapter로 원본 얼굴 정보 주입하여 정체성 복원.",
                "- 정량 평가 체계 구축 완료: 4조합 파라미터 튜닝 → SSIM 1위 조합(0.7072) 도출. ControlNet(Canny) 연동으로 구조 보존 옵션 제공. 프리셋 기반 품질 일관성 유지.",
            ])
    else:
        print("⚠️  Table-30 not found")

    # ─────────────────────────────────────────────
    # Table-31: 4. AI 기술 활용 계획 (index 105)
    # ─────────────────────────────────────────────
    t31 = get_table(body, 'Table-31')
    if t31 is not None:
        print("✏️  Table-31 (4. AI 기술 활용 계획) 업데이트...")

        # R1: 인공지능 기술 설명 → col 1
        c = get_row_cell(t31, 0, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 자체 개발 2-pass AI 화풍 변환 파이프라인을 핵심 엔진으로 구축. 단순 LoRA 적용이 아닌, 화풍 변환(Pass 1)과 얼굴 복원(Pass 2)을 분리하여 품질과 정체성을 동시 확보하는 구조를 설계·검증 완료.",
                "- Pass 1: SDXL + LoRA 미세조정으로 작가 화풍 적용 (strength/guidance/steps 파라미터 최적화)",
                "- Pass 2: IP-Adapter로 원본 사진의 얼굴 특징을 결과물에 주입, 정체성 복원 (ip_adapter_scale 조절)",
                "- 옵션: ControlNet(Canny edge) 연동으로 윤곽선/포즈 구조 보존 강화",
                "- 작가 화풍 학습: 50~100장 원화로 SDXL LoRA 학습(dim=32, alpha=16). 이정문·신문수 2인 학습 완료, 본 과제에서 5인 이상 확장",
            ])

        # R2: 인공지능 활용 효과 → col 1
        c = get_row_cell(t31, 1, 1)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 기존 만화 작가 직접 작화 시 1컷당 수 시간~수일 소요 → AI 변환으로 ~4초/장으로 단축 (제작시간 99.9% 이상 절감).",
                "- 기존 범용 AI(Midjourney, ChatGPT 등)로는 특정 작가 고유 화풍을 재현할 수 없음. 본 기술은 50~100장 원화만으로 작가별 화풍을 정밀 학습하여, 정식 라이선스 기반의 작가 특화 변환을 가능하게 함.",
                "- 2-pass 파이프라인 도입 전에는 화풍 변환 시 얼굴 정체성이 소실되는 한계가 있었으나, IP-Adapter 기반 Pass 2 도입으로 화풍 재현과 인물 유사도를 동시에 확보하는 문제를 해결.",
            ])
    else:
        print("⚠️  Table-31 not found")

    # ─────────────────────────────────────────────
    # Table-32: (4-1) AI 기술 기능 상세 (index 108)
    # ─────────────────────────────────────────────
    t32 = get_table(body, 'Table-32')
    if t32 is not None:
        print("✏️  Table-32 (4-1 AI 기술 기능 상세) 업데이트...")
        c = get_row_cell(t32, 0, 0)
        if c is not None:
            set_cell_text(c, [
                "ㅇ 자체 개발 2-pass AI 화풍 변환 파이프라인을 핵심 엔진으로, Pass 1(화풍변환) + Pass 2(얼굴복원)의 분리 설계로 품질·정체성 동시 확보",
                "- 기존 작가 직접 작화(수 시간/건) → AI 변환(~4초/건)으로 콘텐츠 제작 시간 99.9% 단축. 50~100장 원화로 작가 화풍 학습 가능",
                "",
                "기술 내역 | 콘텐츠 제작 단계 | 활용 방식 | 주요 내용",
                "SDXL + LoRA 엔진(자체 개발) | AI 모델 학습/화풍 변환 추론 | 작가별 화풍 학습 및 Pass 1 변환 | 원화 50~100장으로 학습. 최적 strength 0.65 도출(PoC 검증)",
                "IP-Adapter 얼굴 복원 | Pass 2 정체성 복원 | 원본 사진을 참조이미지로 주입 | scale 0.68로 얼굴 유사도 보존. 2-pass 설계로 화풍↔정체성 분리 제어",
                "ControlNet(Canny) | 구조 보존(선택) | 엣지맵 기반 윤곽선/포즈 유지 | control_strength 0.85에서 SSIM 0.7072 달성",
                "자동 캡셔닝 + 품질 평가 | 데이터 전처리/결과물 검증 | 원화 캡션 자동 생성 + 품질 스코어링 | BLIP-2/CogVLM 캡셔닝. SSIM·LPIPS·FID 자동 평가",
            ])
    else:
        print("⚠️  Table-32 not found")

    # ─────────────────────────────────────────────
    # Table-34: (4-2) AI 기술 도식화 (index 112)
    # ─────────────────────────────────────────────
    t34 = get_table(body, 'Table-34')
    if t34 is not None:
        print("✏️  Table-34 (4-2 AI 기술 도식화) 업데이트...")
        c = get_row_cell(t34, 0, 0)
        if c is not None:
            set_cell_text(c, [
                "[사용자] → [ToonStyle AI 플랫폼] → [출력]",
                "",
                "사진 업로드 ──▶ Pass 1: 화풍 변환",
                "작가 선택         SDXL + LoRA(작가별)",
                "파라미터 조절     + ControlNet(Canny, 선택)",
                "                         ▼",
                "                  Pass 2: 얼굴 복원 ──▶ 변환 이미지",
                "                  IP-Adapter(원본 참조)    다운로드/공유",
                "                  정체성 복원 + 스타일 유지  갤러리 저장",
                "",
                "[모델 학습 파이프라인]",
                "작가 원화(50~100장) → 자동 전처리/캡셔닝(선별, BLIP-2) → SDXL LoRA 학습(dim=32, ~40분/작가) → 작가 화풍 모델(.safetensors) → 프리셋 등록",
            ])
    else:
        print("⚠️  Table-34 not found")

    # ─────────────────────────────────────────────
    # Write back
    # ─────────────────────────────────────────────
    new_content = ET.tostring(root, encoding='unicode', xml_declaration=False)
    # Prepend XML declaration
    new_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + new_content

    out = src  # overwrite
    with zipfile.ZipFile(src, 'r') as zin:
        with zipfile.ZipFile(str(out) + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename == 'content.xml':
                    zout.writestr(item, new_content.encode('utf-8'))
                else:
                    zout.writestr(item, zin.read(item.filename))

    # Replace original
    Path(str(out) + '.tmp').replace(out)
    print(f"\n✅ ODT 업데이트 완료: {out}")
    print(f"📦 백업: {bak}")


if __name__ == '__main__':
    main()
