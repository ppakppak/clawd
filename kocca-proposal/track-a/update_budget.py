#!/usr/bin/env python3
"""Tables 47+48 (사업비) 업데이트"""

import zipfile, shutil
from datetime import datetime
from lxml import etree

ODT = '/home/ppak/clawd/kocca-proposal/track-a/1-1_사업신청서_인튜웍스_실증.odt'
NS_T = 'urn:oasis:names:tc:opendocument:xmlns:table:1.0'
NS_X = 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'

def set_text(cell, text, style='바탕글'):
    for p in list(cell.iter(f'{{{NS_X}}}p')):
        p.getparent().remove(p)
    p = etree.SubElement(cell, f'{{{NS_X}}}p')
    p.set(f'{{{NS_X}}}style-name', style)
    p.text = text

def fmt(n):
    """Format number with commas."""
    if n == 0:
        return ''
    return f'{n:,}'

def get_rows(table):
    return list(table.iter(f'{{{NS_T}}}table-row'))

def get_cells(row):
    return list(row.iter(f'{{{NS_T}}}table-cell'))

# ── Budget data (단위: 원) ──
# 주관(인튜웍스): 지원금 182M, 자부담 18M, 소계 200M
# 참여(위즈데이터): 지원금 18M, 자부담 5M, 소계 23M
# 총계: 지원금 200M, 자부담 23M, 총 223M

# 7-value tuple: (주관지원, 주관자부담, 주관소계, 참여지원, 참여자부담, 참여소계, 총계)
BUDGET = {
    '보수':       (105_000_000, 15_000_000, 120_000_000,  6_000_000,  2_000_000,   8_000_000, 128_000_000),
    '상용임금':    (0, 0, 0, 0, 0, 0, 0),
    '전문가활용비': ( 5_000_000,  0,  5_000_000,  5_000_000,  0,  5_000_000,  10_000_000),
    '수수료':      (0, 0, 0, 0, 0, 0, 0),
    '공고료':      (0, 0, 0, 0, 0, 0, 0),
    '안내홍보물':   (10_000_000,  0, 10_000_000,  0,  0,  0,  10_000_000),
    '공공요금':    (40_000_000,  0, 40_000_000,  2_000_000,  0,  2_000_000,  42_000_000),
    '임차료':      (15_000_000,  0, 15_000_000,  0,  0,  0,  15_000_000),
    '일반용역비':   ( 7_000_000,  3_000_000, 10_000_000,  5_000_000,  3_000_000,  8_000_000,  18_000_000),
    '총계':       (182_000_000, 18_000_000, 200_000_000, 18_000_000,  5_000_000, 23_000_000, 223_000_000),
}

# Row index → budget key, and which cells are data
# For 7-cell rows: C0-C6 = data
# For 8-cell rows: C1-C7 = data (C0 = label)
# For R2 (9-cell): C2-C8 = data
DETAIL_MAP = [
    (2,  '보수',       'C2-C8'),   # 9 cells
    (4,  '상용임금',    'C0-C6'),   # 7 cells
    (6,  '전문가활용비', 'C0-C6'),   # 7 cells
    (8,  '수수료',      'C0-C6'),   # 7 cells
    (10, '공고료',      'C0-C6'),   # 7 cells
    (11, '안내홍보물',   'C1-C7'),   # 8 cells
    (12, '공공요금',    'C1-C7'),   # 8 cells
    (13, '임차료',      'C1-C7'),   # 8 cells
    (14, '일반용역비',   'C1-C7'),   # 8 cells
    (15, '총계',       'C1-C7'),   # 8 cells
]


def fill_data_cells(rows, row_idx, budget_key, cell_range):
    """Fill 7 data cells with budget values."""
    row = rows[row_idx]
    cells = get_cells(row)
    values = BUDGET[budget_key]
    
    if cell_range == 'C2-C8':
        start = 2
    elif cell_range == 'C1-C7':
        start = 1
    else:  # C0-C6
        start = 0
    
    for i, val in enumerate(values):
        idx = start + i
        if idx < len(cells):
            set_text(cells[idx], fmt(val))
    
    total = values[-1]
    label = budget_key
    print(f'  R{row_idx} {label}: 주관 {values[0]/1e6:.0f}M+{values[1]/1e6:.0f}M / 참여 {values[3]/1e6:.0f}M+{values[4]/1e6:.0f}M → 총 {total/1e6:.0f}M')


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

    # ═══ Table 47: Summary ═══
    print('\n[Table 47] 사업비 요약')
    tbl47 = tables[47]
    rows47 = get_rows(tbl47)
    
    # R1: 주관기관
    cells = get_cells(rows47[1])
    set_text(cells[1], '182,000,000')
    set_text(cells[2], '18,000,000')
    set_text(cells[3], '200,000,000')
    print('  주관: 지원금 182M / 자부담 18M / 소계 200M')
    
    # R2: 참여기관
    cells = get_cells(rows47[2])
    set_text(cells[1], '18,000,000')
    set_text(cells[2], '5,000,000')
    set_text(cells[3], '23,000,000')
    print('  참여: 지원금 18M / 자부담 5M / 소계 23M')
    
    # R3: 합계 (7 cells)
    cells = get_cells(rows47[3])
    set_text(cells[1], '200,000,000')
    set_text(cells[2], '(89.7%)')
    set_text(cells[3], '23,000,000')
    set_text(cells[4], '(10.3%)')
    set_text(cells[5], '223,000,000')
    set_text(cells[6], '(100%)')
    print('  합계: 지원금 200M(89.7%) / 자부담 23M(10.3%) / 총 223M')

    # ═══ Table 48: Detail ═══
    print('\n[Table 48] 사업비 상세')
    tbl48 = tables[48]
    rows48 = get_rows(tbl48)
    
    for row_idx, key, cell_range in DETAIL_MAP:
        fill_data_cells(rows48, row_idx, key, cell_range)

    # ═══ Verify totals ═══
    print('\n[검증]')
    intu_g = sum(v[0] for v in BUDGET.values() if v != BUDGET['총계'])
    intu_s = sum(v[1] for v in BUDGET.values() if v != BUDGET['총계'])
    wiz_g = sum(v[3] for v in BUDGET.values() if v != BUDGET['총계'])
    wiz_s = sum(v[4] for v in BUDGET.values() if v != BUDGET['총계'])
    print(f'  인튜 지원금: {intu_g/1e6:.0f}M (expected 182M) {"✓" if intu_g == 182_000_000 else "✗"}')
    print(f'  인튜 자부담: {intu_s/1e6:.0f}M (expected 18M) {"✓" if intu_s == 18_000_000 else "✗"}')
    print(f'  위즈 지원금: {wiz_g/1e6:.0f}M (expected 18M) {"✓" if wiz_g == 18_000_000 else "✗"}')
    print(f'  위즈 자부담: {wiz_s/1e6:.0f}M (expected 5M) {"✓" if wiz_s == 5_000_000 else "✗"}')
    print(f'  총계: {(intu_g+intu_s+wiz_g+wiz_s)/1e6:.0f}M (expected 223M)')

    # Write back
    new_xml = etree.tostring(root, xml_declaration=True, encoding='UTF-8')
    with zipfile.ZipFile(ODT, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('content.xml', new_xml)
        for name, data in all_files.items():
            zout.writestr(name, data)

    print(f'\n✅ 업데이트 완료: {ODT}')


if __name__ == '__main__':
    main()
