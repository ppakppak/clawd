#!/usr/bin/env python3
"""KPI (Tables 37,38,36-R9) + 일자리 (Table 41) 업데이트"""

import zipfile, shutil
from datetime import datetime
from lxml import etree

ODT = '/home/ppak/clawd/kocca-proposal/track-a/1-1_사업신청서_인튜웍스_실증.odt'
NS_T = 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'
NS_X = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'


def set_cell_text(cell, text, style=None):
    """Replace all text in cell with single paragraph."""
    for p in list(cell.iter(f'{{{NS_X}}}p')):
        p.getparent().remove(p)
    p = etree.SubElement(cell, f'{{{NS_X}}}p')
    if style:
        p.set(f'{{{NS_X}}}style-name', style)
    else:
        p.set(f'{{{NS_X}}}style-name', '바탕글')
    p.text = text


def set_cell_multiline(cell, lines, style='바탕글'):
    """Replace cell content with multiple paragraphs."""
    for p in list(cell.iter(f'{{{NS_X}}}p')):
        p.getparent().remove(p)
    for line in lines:
        p = etree.SubElement(cell, f'{{{NS_X}}}p')
        p.set(f'{{{NS_X}}}style-name', style)
        p.text = line


def get_cell(table, row_idx, cell_idx):
    rows = list(table.iter(f'{{{NS_T}}}table-row'))
    row = rows[row_idx]
    cells = list(row.iter(f'{{{NS_T}}}table-cell'))
    return cells[cell_idx]


def main():
    # Backup
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    bak = ODT.replace('.odt', f'_bak_{ts}.odt')
    shutil.copy2(ODT, bak)
    print(f'백업: {bak}')

    with zipfile.ZipFile(ODT, 'r') as z:
        content_xml = z.read('content.xml')
        all_files = {n: z.read(n) for n in z.namelist() if n != 'content.xml'}

    root = etree.fromstring(content_xml)
    tables = list(root.iter(f'{{{NS_T}}}table'))

    # ═══════════════════════════════════════
    # TABLE 37: 2026 당해년도 매출/투자유치
    # ═══════════════════════════════════════
    tbl37 = tables[37]
    print('\n[Table 37] 2026 당해년도 KPI')

    # R1 C2: 매출 예상 방안
    set_cell_multiline(get_cell(tbl37, 1, 2), [
        "베타 서비스 B2C 구독 매출(월 9,900~29,900원 × 목표 1,000 MAU)",
        "B2B API PoC 계약 1건(콘텐츠 제작사 또는 마케팅 에이전시)",
        "굿즈 제작 판매(화풍변환 엽서·프로필 등)"
    ])
    print('  R1 C2: 매출 예상 방안 ✓')

    # R2 C2: 투자유치 예상 방안
    set_cell_multiline(get_cell(tbl37, 2, 2), [
        "시드 투자 3억원 목표(VC/엔젤)",
        "KOCCA AI콘텐츠 페스티벌 IR 데모, 대전창조경제혁신센터 데모데이",
        "베타 서비스 MAU·전환율 실적 기반 피칭"
    ])
    print('  R2 C2: 투자유치 예상 방안 ✓')

    # R3: 합계
    set_cell_text(get_cell(tbl37, 3, 1), '350,000,000')
    set_cell_text(get_cell(tbl37, 3, 2), '원')
    print('  R3: 합계 350,000,000원 ✓')

    # ═══════════════════════════════════════
    # TABLE 38: 2027/2028 향후 2개년
    # ═══════════════════════════════════════
    tbl38 = tables[38]
    print('\n[Table 38] 2027/2028 향후 2개년')

    # R1: 매출액
    set_cell_text(get_cell(tbl38, 1, 1), '300,000,000원')
    set_cell_multiline(get_cell(tbl38, 1, 2), [
        "SaaS 구독 확대(MAU 5,000명 목표)",
        "B2B API 정식 라이선스 3건+",
        "IP 활용 굿즈·NFT 매출"
    ])
    set_cell_text(get_cell(tbl38, 1, 3), '1,000,000천원')
    set_cell_multiline(get_cell(tbl38, 1, 4), [
        "글로벌(영·일) 서비스 확장",
        "B2B API 10건+, 대형 IP 콜라보",
        "기업 고객 연간 계약 전환"
    ])
    print('  R1: 매출액 (2027: 3억원, 2028: 10억원) ✓')

    # R2: 투자유치액
    set_cell_text(get_cell(tbl38, 2, 1), '1,000,000,000원')
    set_cell_multiline(get_cell(tbl38, 2, 2), [
        "시리즈A 10~20억원 유치",
        "MAU·ARR 실적 기반 VC 피칭",
        "해외 진출 로드맵 제시"
    ])
    set_cell_text(get_cell(tbl38, 2, 3), '2,000,000천원')
    set_cell_multiline(get_cell(tbl38, 2, 4), [
        "시리즈B 20억원+ 유치",
        "글로벌 MAU·매출 실적 기반",
        "전략적 투자자(콘텐츠/IP 기업) 유치"
    ])
    print('  R2: 투자유치 (2027: 10억원, 2028: 20억원) ✓')

    # R3: 합계
    set_cell_text(get_cell(tbl38, 3, 1), '1,300,000,000원')
    set_cell_text(get_cell(tbl38, 3, 2), '')
    set_cell_text(get_cell(tbl38, 3, 3), '3,000,000천원')
    set_cell_text(get_cell(tbl38, 3, 4), '')
    print('  R3: 합계 (2027: 13억원, 2028: 30억원) ✓')

    # ═══════════════════════════════════════
    # TABLE 36 R9: 매출·투자유치 계획 서술
    # ═══════════════════════════════════════
    tbl36 = tables[36]
    print('\n[Table 36 R9] 매출·투자유치 계획 서술')

    narrative_cell = get_cell(tbl36, 9, 1)
    set_cell_multiline(narrative_cell, [
        "ㅇ 매출 계획",
        "- 2026년 하반기: 오픈 베타 런칭 후 B2C SaaS 구독(월 9,900~29,900원) 및 건별 결제로 5,000만원 매출 목표. B2B API PoC 계약 1건(콘텐츠 제작사) 추진",
        "- 정식 IP 라이선싱 기반이라는 법적 안전성을 B2B 기업 고객의 핵심 구매 요인으로 활용하여 시장 진입",
        "- 2027년: SaaS 구독 MAU 5,000명 확보 + B2B API 라이선스 3건으로 3억원 매출 목표",
        "ㅇ 투자유치 계획",
        "- 2026년 10~11월 IR 피칭: KOCCA AI 콘텐츠 페스티벌 전시·데모, 대전창조경제혁신센터 IR 데모데이 참가",
        "- 베타 서비스 MAU 1,000명·변환 10,000건·B2B PoC 1건 실적을 기반으로 시드 투자 3~5억원 유치 목표",
        "- VC/엔젤 투자자 대상 개별 미팅 5회 이상 추진. 정식 IP 라이선싱, 자체 개발 2-pass 파이프라인, PoC 실적을 핵심 투자 포인트로 제시"
    ])
    print('  서술 완료 ✓')

    # ═══════════════════════════════════════
    # TABLE 41: 일자리 창출 상세
    # ═══════════════════════════════════════
    tbl41 = tables[41]
    print('\n[Table 41] 일자리 창출 상세')

    # R1: 인튜웍스 정규직 — 수정
    set_cell_text(get_cell(tbl41, 1, 2), '정규직')       # 고용형태
    set_cell_text(get_cell(tbl41, 1, 3), 'AI 엔지니어\n(모델 학습/추론 최적화)')  # 수행업무
    set_cell_text(get_cell(tbl41, 1, 4), "26.5.1.~26.11.30\n(7개월)")  # 참여기간
    set_cell_text(get_cell(tbl41, 1, 5), '1명')          # 채용 인원
    set_cell_multiline(get_cell(tbl41, 1, 6), [
        "추가 작가 모델 학습(5인→10인+) 및",
        "2-pass 파이프라인 고도화에 필요.",
        "LoRA·IP-Adapter 튜닝, GPU 추론",
        "최적화 전문 인력 필수"
    ])
    print('  R1: 인튜웍스 AI엔지니어 ✓')

    # R2: 위즈데이터 계약직
    set_cell_text(get_cell(tbl41, 2, 1), '참여기관\n(위즈데이터)')
    set_cell_text(get_cell(tbl41, 2, 2), '계약직')
    set_cell_text(get_cell(tbl41, 2, 3), '콘텐츠 기획/QA')
    set_cell_text(get_cell(tbl41, 2, 4), "26.7.1.~26.11.30\n(5개월)")
    set_cell_text(get_cell(tbl41, 2, 5), '1명')
    set_cell_multiline(get_cell(tbl41, 2, 6), [
        "IP 원화 디지털화·정제 작업 및",
        "변환 결과물 품질 검수(QA) 담당.",
        "작가별 화풍 충실도 평가에 만화/",
        "일러스트 전문 지식 필요"
    ])
    print('  R2: 위즈데이터 콘텐츠기획/QA ✓')

    # R3, R4: 빈 행 유지 (필요 없으면 비워둠)

    # ═══════════════════════════════════════
    # TABLE 40 R0 C2: 목표치 확인
    # ═══════════════════════════════════════
    tbl40 = tables[40]
    set_cell_text(get_cell(tbl40, 0, 2), '2명')
    print('\n[Table 40] 목표치 2명 확인 ✓')

    # Write back
    new_xml = etree.tostring(root, xml_declaration=True, encoding='UTF-8')
    with zipfile.ZipFile(ODT, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('content.xml', new_xml)
        for name, data in all_files.items():
            zout.writestr(name, data)

    print(f'\n✅ 전체 업데이트 완료: {ODT}')


if __name__ == '__main__':
    main()
