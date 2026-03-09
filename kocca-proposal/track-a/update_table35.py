#!/usr/bin/env python3
"""Table-35 (5. 상용화 계획/전략) 업데이트 — 비즈니스모델, 목표소비층, 목표시장, 홍보/마케팅"""

import zipfile, shutil, os, copy
from datetime import datetime
from lxml import etree

ODT = '/home/ppak/clawd/kocca-proposal/track-a/1-1_사업신청서_인튜웍스_실증.odt'
NS = {
    'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
    'text':  'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'office':'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
}

# ── Content definitions ──

ROW0_BIZ_MODEL = [
    ("바탕글", "ㅇ B2C 구독형 SaaS: 월정액(월 9,900~29,900원, 변환 크레딧제) + 건별 결제(건당 1,000~3,000원). 무료 체험 3회 제공으로 진입 장벽 최소화"),
    ("바탕글", "- B2B API 라이선스: 콘텐츠 제작사·마케팅 에이전시 대상, 월 100만~500만원(호출량 기반)"),
    ("바탕글", "- IP 라이선싱: 위즈데이터 보유 7080 만화작가 IP 기반 변환 결과물 상업 이용권(별도 협의)"),
    ("바탕글", "- 굿즈/파생 상품: 화풍 변환 기반 프로필, 엽서, 포스터, NFT 등(건당 5,000~50,000원)"),
    ("바탕글", "ㅇ 투자유치 전략: 2026 하반기 시드 투자 3~5억원 유치 목표"),
    ("바탕글", "- KOCCA AI 콘텐츠 페스티벌, 대전창조경제혁신센터 IR 데모데이 참가"),
    ("바탕글", "- 베타 서비스 MAU 1,000명·변환 10,000건 실적 기반 VC/엔젤 피칭"),
]

ROW1_TARGET_CONSUMER = [
    ("바탕글", "ㅇ B2C 1차 타깃 — 7080 세대 향수를 가진 30~50대"),
    ("바탕글", "- 어린 시절 만화에 대한 감성적 기억 보유, 본인·가족 사진을 추억의 화풍으로 변환하는 '레트로 셀피' 수요. 높은 구매력(가구 평균 소득 최상위 연령대)과 결합하여 안정적 매출 기반"),
    ("바탕글", "ㅇ B2C 2차 타깃 — SNS 크리에이터(20~30대)"),
    ("바탕글", "- 차별화된 프로필/콘텐츠 소재로 활용, '내 사진 만화 변환' 바이럴 확산력 기대. 인스타그램·틱톡 중심"),
    ("바탕글", "ㅇ B2C 3차 타깃 — K-콘텐츠 글로벌 팬"),
    ("바탕글", "- 한국 만화 스타일 체험 수요, 다국어(영·일) 지원 시 해외 MAU 확보 가능"),
    ("바탕글", "ㅇ B2B — 콘텐츠 제작사(웹툰·애니 스튜디오), 마케팅 에이전시(캠페인 소재), 문화기관(미술관·박물관 기획전), 교육기관"),
    ("바탕글", "- 정식 IP 라이선싱이라는 법적·윤리적 안전성이 B2B 고객의 핵심 구매 요인"),
]

ROW2_TARGET_MARKET = [
    ("바탕글", "ㅇ 국내 시장"),
    ("바탕글", "- AI 이미지 생성 시장: 2024년 약 300억원 → 2028년 연 800억원 전망(연평균 28% 성장)"),
    ("바탕글", "- 7080 향수 콘텐츠 시장: 해당 세대 인구 3,000만명+, '응답하라' 시리즈 이후 레트로 콘텐츠 소비 지속 증가세"),
    ("바탕글", "- 국내 진입 전략: ① 정식 IP 라이선싱(법적 안전) 차별점으로 B2B 기업 고객 선점 → ② SNS 바이럴을 통한 B2C 대중 확산"),
    ("바탕글", "ㅇ 해외 시장"),
    ("바탕글", "- K-콘텐츠 글로벌 시장: 한류 콘텐츠 수출 2025년 150억달러 돌파, 동남아·미주 한류 팬덤 2억명+"),
    ("바탕글", "- 해외 진입 전략: 2027년 영문·일문 버전 출시, 'K-style 만화 변환'이라는 고유 가치로 글로벌 AI 이미지 서비스와 차별화"),
    ("바탕글", "- K-만화(한국 특유의 만화 화풍)는 웹툰의 글로벌 확산으로 이미 인지도 확보 → 진입 비용 최소화"),
]

ROW3_MARKETING = [
    ("바탕글", "ㅇ 4~5월 (준비기)"),
    ("바탕글", "- 브랜드 아이덴티티(BI) 확립, ToonStyle AI 랜딩 페이지 구축"),
    ("바탕글", "- 소셜 채널 개설(인스타그램·유튜브), 7080 만화작가 소개 티저 콘텐츠 3편 제작"),
    ("바탕글", "ㅇ 6~7월 (사전 홍보)"),
    ("바탕글", "- '작가 이야기' 시리즈 콘텐츠 연재(주 2회, 인스타+블로그)"),
    ("바탕글", "- 인플루언서 시딩 10명(레트로·일러스트 분야), 클로즈드 베타 대기 신청 페이지 운영"),
    ("바탕글", "- 네이버 카페·커뮤니티(7080 향수, 만화 관련) 대상 사전 홍보"),
    ("바탕글", "ㅇ 8월 (클로즈드 베타)"),
    ("바탕글", "- 초대 코드 기반 베타 오픈(목표 500명), 얼리어답터 피드백 수집"),
    ("바탕글", "- SNS 바이럴 이벤트: '#내사진만화변환' 챌린지, 우수 변환작 시상(상품권)"),
    ("바탕글", "ㅇ 9월 (오픈 베타 런칭)"),
    ("바탕글", "- 정식 오픈, 론칭 프로모션(첫 3회 무료 변환)"),
    ("바탕글", "- 보도자료 배포(IT·문화 매체 15곳+), 네이버 블로그·유튜브 리뷰어 협업(5명+)"),
    ("바탕글", "ㅇ 10월 (확산기)"),
    ("바탕글", "- KOCCA AI 콘텐츠 페스티벌 전시·라이브 데모"),
    ("바탕글", "- B2B 기업 고객 대상 API 활용 세미나, 유튜브·인스타 광고 집행(월 300만원)"),
    ("바탕글", "ㅇ 11월 (성과 확인)"),
    ("바탕글", "- 사용자 데이터 분석 및 KPI 달성 현황 보고"),
    ("바탕글", "- IR 피칭(대전창조경제혁신센터 데모데이), VC 대상 개별 미팅, 성과 사례집 제작"),
]

UPDATES = {
    0: ROW0_BIZ_MODEL,        # R0 C1 — 비즈니스 모델
    1: ROW1_TARGET_CONSUMER,  # R1 C2 — 목표 소비층
    2: ROW2_TARGET_MARKET,    # R2 C1 — 목표시장
    3: ROW3_MARKETING,        # R3 C1 — 홍보/마케팅
}

# Which cell index to update in each row (the content cell, not the label)
ROW_CELL_IDX = {0: 1, 1: 2, 2: 1, 3: 1}

def make_para(style, text):
    """Create a <text:p> element."""
    p = etree.Element(f'{{{NS["text"]}}}p')
    p.set(f'{{{NS["text"]}}}style-name', style)
    p.text = text
    return p

def update_cell(cell, paragraphs_data):
    """Replace all <text:p> in cell with new paragraphs."""
    # Remove existing paragraphs
    for p in list(cell.iter(f'{{{NS["text"]}}}p')):
        p.getparent().remove(p)
    # Add new ones
    for style, text in paragraphs_data:
        cell.append(make_para(style, text))

def main():
    # Backup
    ts = datetime.now().strftime('%Y%m%d_%H%M')
    bak = ODT.replace('.odt', f'_bak_{ts}.odt')
    shutil.copy2(ODT, bak)
    print(f'백업: {bak}')

    # Read ODT
    with zipfile.ZipFile(ODT, 'r') as z:
        content_xml = z.read('content.xml')
        all_files = z.namelist()
        file_data = {}
        for name in all_files:
            if name != 'content.xml':
                file_data[name] = z.read(name)

    root = etree.fromstring(content_xml)
    tables = list(root.iter(f'{{{NS["table"]}}}table'))

    # Find the 비즈니스 모델 table (idx 34)
    tbl = tables[34]
    all_text = ' '.join(''.join(p.itertext()).strip() for p in tbl.iter(f'{{{NS["text"]}}}p'))
    assert '비즈니스' in all_text, f'Table 34 does not contain 비즈니스: {all_text[:100]}'
    print('Table 34 확인: 비즈니스 모델 (상용화 방안)')

    rows = list(tbl.iter(f'{{{NS["table"]}}}table-row'))
    print(f'총 {len(rows)} 행')

    for row_idx, para_data in UPDATES.items():
        row = rows[row_idx]
        cells = list(row.iter(f'{{{NS["table"]}}}table-cell'))
        cell_idx = ROW_CELL_IDX[row_idx]
        cell = cells[cell_idx]

        # Show what we're replacing
        old_text = ' '.join(''.join(p.itertext()).strip() for p in cell.iter(f'{{{NS["text"]}}}p'))[:80]
        print(f'  R{row_idx} C{cell_idx}: "{old_text}..." → {len(para_data)}줄')
        update_cell(cell, para_data)

    # Write back
    new_xml = etree.tostring(root, xml_declaration=True, encoding='UTF-8')
    with zipfile.ZipFile(ODT, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('content.xml', new_xml)
        for name, data in file_data.items():
            zout.writestr(name, data)

    print(f'\n✅ 업데이트 완료: {ODT}')

if __name__ == '__main__':
    main()
