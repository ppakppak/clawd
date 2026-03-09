#!/usr/bin/env python3
"""Table 44 (추진일정) — 간트차트 + 사업비 집행계획 + 결과물"""

import zipfile, shutil
from datetime import datetime
from lxml import etree

ODT = '/home/ppak/clawd/kocca-proposal/track-a/1-1_사업신청서_인튜웍스_실증.odt'
NS_T = 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'
NS_X = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'

# ── Schedule data ──
# (category, sub_task, active_months)
# months: 4=apr, 5=may, 6=jun, 7=jul, 8=aug, 9=sep, 10=oct, 11=nov

SCHEDULE = {
    # Group 1: AI 기술 개발 (R2-R3, 2 rows)
    'group1': [
        ('AI 기술\n개발', 'LoRA 파이프라인 고도화', [4, 5, 6]),
        (None,            'ControlNet/IP-Adapter 통합\n+ 추가 작가 모델 학습', [5, 6, 7, 8]),
    ],
    # Group 2: 플랫폼 구축 (R4-R9, 6 rows: R4 has label + 5 data rows)
    'group2': [
        ('플랫폼\n구축', '웹 프론트엔드(Next.js) 개발', [5, 6, 7, 8]),
        (None,           '백엔드 API + GPU 인프라', [5, 6, 7]),
        (None,           '구독/결제 시스템 구축', [7, 8]),
        (None,           '클로즈드 베타 운영', [8]),
        (None,           '오픈 베타 런칭', [9]),
        (None,           '', []),  # empty row
    ],
    # Group 3: 마케팅 (R10-R12, 3 rows)
    'group3': [
        ('홍보/\n마케팅', '브랜드 BI + 소셜 채널 구축', [4, 5]),
        (None,           '사전 홍보/인플루언서 시딩', [6, 7]),
        (None,           '오픈베타 광고 집행', [9, 10]),
    ],
    # Group 4: 실증/성과 (R13-R15, 3 rows)
    'group4': [
        ('실증/\n성과', '현장 실증 3건 수행', [8, 9, 10]),
        (None,          'IR 피칭 / 투자유치 활동', [10, 11]),
        (None,          '최종 보고/결과물 제출', [11]),
    ],
}

# Row assignments
GROUP_ROWS = {
    'group1': [2, 3],
    'group2': [4, 5, 6, 7, 8, 9],
    'group3': [10, 11, 12],
    'group4': [13, 14, 15],
}

def set_text(cell, text, style='바탕글'):
    for p in list(cell.iter(f'{{{NS_X}}}p')):
        p.getparent().remove(p)
    p = etree.SubElement(cell, f'{{{NS_X}}}p')
    p.set(f'{{{NS_X}}}style-name', style)
    p.text = text


def fill_row(rows, row_idx, category, sub_task, active_months):
    """Fill a schedule row.
    10-cell rows: C0=category, C1=sub_task, C2-C9=months(4-11)
    9-cell rows: C0=sub_task, C1-C8=months(4-11)
    """
    row = rows[row_idx]
    cells = list(row.iter(f'{{{NS_T}}}table-cell'))
    n = len(cells)

    if n >= 10:
        # Has category column
        if category:
            set_text(cells[0], category)
        set_text(cells[1], sub_task)
        month_start = 2  # C2=4월, C3=5월, ..., C9=11월
    else:
        # No category column (covered by rowspan)
        set_text(cells[0], sub_task)
        month_start = 1  # C1=4월, C2=5월, ..., C8=11월

    for month in range(4, 12):  # 4월~11월
        cell_idx = month_start + (month - 4)
        if cell_idx < n:
            if month in active_months:
                set_text(cells[cell_idx], '■')
            else:
                set_text(cells[cell_idx], '')


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
    tbl = tables[44]
    rows = list(tbl.iter(f'{{{NS_T}}}table-row'))

    print(f'Table 44: {len(rows)} rows')

    # Fill schedule groups
    for group_name, items in SCHEDULE.items():
        row_indices = GROUP_ROWS[group_name]
        print(f'\n[{group_name}] rows {row_indices}')
        for i, (cat, task, months) in enumerate(items):
            ri = row_indices[i]
            if task:
                fill_row(rows, ri, cat, task, months)
                month_str = ','.join(str(m) for m in months) if months else '-'
                print(f'  R{ri}: {task[:30]} → [{month_str}]')
            else:
                # Clear empty rows
                row = rows[ri]
                cells = list(row.iter(f'{{{NS_T}}}table-cell'))
                for c in cells:
                    set_text(c, '')

    # ── R16: 사업비 집행계획 ──
    print('\n[R16] 사업비 집행계획')
    r16 = rows[16]
    cells16 = list(r16.iter(f'{{{NS_T}}}table-cell'))
    # C0: label (keep), C1: 1차(4-9월), C2: 2차(10-11월)
    set_text(cells16[1], '150,000,000원\n(4~9월, 개발 집중)')
    set_text(cells16[2], '73,000,000원\n(10~11월, 실증/IR)')
    print('  1차: 1.5억(개발), 2차: 0.73억(실증)')

    # ── R17: 결과물 ──
    print('\n[R17] 결과물')
    r17 = rows[17]
    cells17 = list(r17.iter(f'{{{NS_T}}}table-cell'))
    set_text(cells17[1], '중간보고서, AI 파이프라인 v1.0,\n웹 플랫폼 베타 버전,\n작가 모델 3종 이상')
    set_text(cells17[2], '최종보고서, ToonStyle AI 플랫폼 v1.0,\n실증 사례 보고서 3건, 작가 모델 5종+,\nIR 발표자료, 성과 사례집')
    print('  중간/최종 결과물 설정')

    # Write back
    new_xml = etree.tostring(root, xml_declaration=True, encoding='UTF-8')
    with zipfile.ZipFile(ODT, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('content.xml', new_xml)
        for name, data in all_files.items():
            zout.writestr(name, data)

    print(f'\n✅ 업데이트 완료: {ODT}')


if __name__ == '__main__':
    main()
