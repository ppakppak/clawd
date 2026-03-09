#!/usr/bin/env python3
"""Table 42 (3. 자체 성과목표) 업데이트"""

import zipfile, shutil
from datetime import datetime
from lxml import etree

ODT = '/home/ppak/clawd/kocca-proposal/track-a/1-1_사업신청서_인튜웍스_실증.odt'
NS_T = 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'
NS_X = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'


def set_cell_multiline(cell, lines, style='바탕글'):
    for p in list(cell.iter(f'{{{NS_X}}}p')):
        p.getparent().remove(p)
    for line in lines:
        p = etree.SubElement(cell, f'{{{NS_X}}}p')
        p.set(f'{{{NS_X}}}style-name', style)
        p.text = line


def main():
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    bak = ODT.replace('.odt', f'_bak_{ts}.odt')
    shutil.copy2(ODT, bak)
    print(f'백업: {bak}')

    with zipfile.ZipFile(ODT, 'r') as z:
        content_xml = z.read('content.xml')
        all_files = {n: z.read(n) for n in z.namelist() if n != 'content.xml'}

    root = etree.fromstring(content_xml)
    tables = list(root.iter(f'{{{NS_T}}}table'))

    tbl42 = tables[42]
    rows = list(tbl42.iter(f'{{{NS_T}}}table-row'))
    cell = list(rows[0].iter(f'{{{NS_T}}}table-cell'))[0]

    # Verify
    old = ''.join(''.join(p.itertext()).strip() for p in cell.iter(f'{{{NS_X}}}p'))
    assert '자율' in old, f'Expected 자율 기술, got: {old}'
    print(f'Table 42 확인: "{old}"')

    set_cell_multiline(cell, [
        "ㅇ 자체 성과목표 (2026년 11월 기준)",
        "",
        "① 플랫폼 월간 활성 사용자(MAU): 1,000명 이상",
        "   - 측정: Google Analytics 웹 분석",
        "   - 근거: 오픈 베타(9월) 후 2개월간 자연 유입 + SNS 마케팅 효과",
        "",
        "② 화풍 변환 누적 건수: 10,000건 이상",
        "   - 측정: 시스템 변환 로그(자동 집계)",
        "   - 근거: MAU 1,000명 × 평균 10회/월 변환 추정",
        "",
        "③ 탑재 작가 모델 수: 5인 이상",
        "   - 측정: 학습 완료 LoRA 모델 수",
        "   - 현재: 2인(이정문·신문수) → 사업 종료 시 5인+",
        "",
        "④ 변환 품질(구조 유사도 SSIM): 0.70 이상",
        "   - 측정: 원본 대비 변환 이미지 자동 SSIM 평가",
        "   - 현재 PoC 실적: SSIM 0.7072 (신문수 프리셋 최적 파라미터)",
        "",
        "⑤ 콘텐츠 실증 사례: 3건 이상",
        "   - 유형: B2B 기업 협업 실증, 문화기관 전시 활용, 교육 콘텐츠 제작 등",
        "   - 각 사례별 결과 보고서 작성 및 제출",
        "",
        "⑥ 협약 및 MOU: 2건 이상",
        "   - 대상: IP 보유사(위즈데이터 외 추가), 콘텐츠 유통사, 문화기관 등",
        "   - 실증 결과를 기반으로 정식 협약 체결",
        "",
        "⑦ B2B API PoC 계약: 1건 이상",
        "   - 대상: 콘텐츠 제작사 또는 마케팅 에이전시",
        "   - API 연동 테스트 완료 및 유상 계약 체결",
    ])
    print('  자체 성과목표 7개 항목 입력 완료')

    new_xml = etree.tostring(root, xml_declaration=True, encoding='UTF-8')
    with zipfile.ZipFile(ODT, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('content.xml', new_xml)
        for name, data in all_files.items():
            zout.writestr(name, data)

    print(f'\n✅ 업데이트 완료: {ODT}')


if __name__ == '__main__':
    main()
