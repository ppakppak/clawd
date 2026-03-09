#!/usr/bin/env python3
"""
KOCCA 인공지능 콘텐츠 제작지원(진입형) 사업 검토 회의자료 PDF 생성
"""
import os
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Korean font setup ──
font_paths = [
    ('/usr/share/fonts/truetype/nanum/NanumGothic.ttf', 'NanumGothic'),
    ('/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf', 'NanumGothicBold'),
]
for fp, fname in font_paths:
    if os.path.exists(fp):
        pdfmetrics.registerFont(TTFont(fname, fp))

FONT = 'NanumGothic'
FONT_BOLD = 'NanumGothicBold'

# Colors
PRIMARY = HexColor('#1a237e')
ACCENT = HexColor('#0d47a1')
LIGHT_BG = HexColor('#e3f2fd')
HEADER_BG = HexColor('#1565c0')
ROW_ALT = HexColor('#f5f5f5')
GREEN = HexColor('#2e7d32')
RED = HexColor('#c62828')
ORANGE = HexColor('#e65100')
GRAY = HexColor('#757575')

# ── Output ──
OUT = Path(os.path.expanduser("~/clawd/kocca-meeting"))
OUT.mkdir(exist_ok=True)
PDF_PATH = OUT / "KOCCA_AI콘텐츠_진입형_검토_회의자료.pdf"

# ── Styles ──
styles = getSampleStyleSheet()

def make_style(name, parent='Normal', fontName=FONT, fontSize=10, leading=14,
               textColor=black, alignment=TA_LEFT, spaceAfter=4, spaceBefore=0,
               bold=False, leftIndent=0):
    fn = FONT_BOLD if bold else fontName
    parent_style = styles[parent] if isinstance(parent, str) else parent
    return ParagraphStyle(name, parent=parent_style, fontName=fn, fontSize=fontSize,
                         leading=leading, textColor=textColor, alignment=alignment,
                         spaceAfter=spaceAfter, spaceBefore=spaceBefore,
                         leftIndent=leftIndent)

title_style = make_style('TitleK', fontSize=22, leading=28, textColor=PRIMARY, alignment=TA_CENTER, bold=True, spaceAfter=6)
subtitle_style = make_style('SubtitleK', fontSize=12, leading=16, textColor=GRAY, alignment=TA_CENTER, spaceAfter=20)
h1_style = make_style('H1K', fontSize=16, leading=22, textColor=PRIMARY, bold=True, spaceBefore=16, spaceAfter=8)
h2_style = make_style('H2K', fontSize=13, leading=18, textColor=ACCENT, bold=True, spaceBefore=12, spaceAfter=6)
h3_style = make_style('H3K', fontSize=11, leading=15, textColor=HexColor('#333333'), bold=True, spaceBefore=8, spaceAfter=4)
body_style = make_style('BodyK', fontSize=10, leading=15, spaceAfter=4)
body_indent = make_style('BodyIndentK', fontSize=10, leading=15, spaceAfter=4, leftIndent=15)
small_style = make_style('SmallK', fontSize=9, leading=12, textColor=GRAY)
cell_style = make_style('CellK', fontSize=9, leading=13)
cell_bold = make_style('CellBoldK', fontSize=9, leading=13, bold=True)
cell_center = make_style('CellCenterK', fontSize=9, leading=13, alignment=TA_CENTER)
cell_header = make_style('CellHeaderK', fontSize=9, leading=13, textColor=white, bold=True, alignment=TA_CENTER)
bullet_style = make_style('BulletK', fontSize=10, leading=15, spaceAfter=3, leftIndent=15)
warn_style = make_style('WarnK', fontSize=11, leading=16, textColor=RED, bold=True, spaceBefore=8)


def make_table(data, col_widths=None, header_rows=1):
    """Create a styled table."""
    t = Table(data, colWidths=col_widths, repeatRows=header_rows)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, header_rows - 1), HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, header_rows - 1), white),
        ('FONTNAME', (0, 0), (-1, header_rows - 1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, header_rows), (-1, -1), FONT),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#bdbdbd')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]
    # Alternate row colors
    for i in range(header_rows, len(data)):
        if i % 2 == 0:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), ROW_ALT))
    t.setStyle(TableStyle(style_cmds))
    return t


def build_pdf():
    doc = SimpleDocTemplate(
        str(PDF_PATH), pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
    )
    story = []
    W = doc.width

    # ═══════════════════════════════════
    # COVER
    # ═══════════════════════════════════
    story.append(Spacer(1, 60))
    story.append(Paragraph("KOCCA 인공지능 콘텐츠 제작지원", title_style))
    story.append(Paragraph("(진입형) 사업 신청 검토", title_style))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="60%", thickness=2, color=PRIMARY))
    story.append(Spacer(1, 15))
    story.append(Paragraph("내부 회의자료", subtitle_style))
    story.append(Paragraph("2026년 2월 23일", subtitle_style))
    story.append(Spacer(1, 40))

    # 참여사 요약 박스
    cover_data = [
        [Paragraph("구분", cell_header), Paragraph("기관명", cell_header), Paragraph("역할", cell_header)],
        [Paragraph("AI 기술", cell_bold), Paragraph("인튜웍스 (IntuWorks)", cell_style), Paragraph("AI 화풍 변환 파이프라인 개발", cell_style)],
        [Paragraph("화백 IP", cell_bold), Paragraph("위즈데이터 (wizdata)", cell_style), Paragraph("7080 화백 IP 보유 (이정문, 신문수 등)", cell_style)],
        [Paragraph("웹툰 제작", cell_bold), Paragraph("(협의 중)", cell_style), Paragraph("네이버 웹툰 연재, 콘텐츠 제작", cell_style)],
    ]
    story.append(make_table(cover_data, col_widths=[W*0.18, W*0.38, W*0.44]))
    story.append(Spacer(1, 30))

    story.append(Paragraph("⚠️  마감: 2026. 3. 6 (금) 11:00 — e나라도움 접수", warn_style))
    story.append(PageBreak())

    # ═══════════════════════════════════
    # 1. 사업 개요
    # ═══════════════════════════════════
    story.append(Paragraph("1. 사업 개요", h1_style))

    overview_data = [
        [Paragraph("항목", cell_header), Paragraph("내용", cell_header)],
        [Paragraph("사업명", cell_bold), Paragraph("2026년 인공지능 콘텐츠 제작지원 (진입형)", cell_style)],
        [Paragraph("주관기관", cell_bold), Paragraph("한국콘텐츠진흥원 (KOCCA)", cell_style)],
        [Paragraph("사업목적", cell_bold), Paragraph("AI 기반 콘텐츠 제작 역량을 보유한 중소기업의 장르별 초기시장 진입 및 도약 지원", cell_style)],
        [Paragraph("사업기간", cell_bold), Paragraph("2026. 4. 15 ~ 2026. 11. 30 (7.5개월)", cell_style)],
        [Paragraph("지원규모", cell_bold), Paragraph("과제당 국고 2억원 이내 × 유형별 8개 과제 (총 24개 과제)", cell_style)],
        [Paragraph("자부담", cell_bold), Paragraph("총사업비의 10% 이상 (현금만 인정) — 2억 기준 약 2,300만원", cell_style)],
        [Paragraph("접수마감", cell_bold), Paragraph("2026. 3. 6 (금) 11:00까지 (e나라도움)", cell_style)],
        [Paragraph("선정절차", cell_bold), Paragraph("1단계 서면(40%) → 2단계 발표(60%) → 최종선정", cell_style)],
    ]
    story.append(make_table(overview_data, col_widths=[W*0.2, W*0.8]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1-1. 지원 유형 (3개)", h2_style))

    type_data = [
        [Paragraph("유형", cell_header), Paragraph("내용", cell_header), Paragraph("과제수", cell_header), Paragraph("결과물", cell_header)],
        [Paragraph("① 장르 융합", cell_bold),
         Paragraph("기존 장르(방송·영상, 캐릭터, 웹툰, 음악 등) + AI 기술", cell_style),
         Paragraph("8개", cell_center),
         Paragraph("기존 문화 장르 콘텐츠\n(게임·애니·영화 제외)", cell_style)],
        [Paragraph("② 신기술 융합", cell_bold),
         Paragraph("신기술 장르(XR, VR, AR, 인터랙티브 등) + AI 기술", cell_style),
         Paragraph("8개", cell_center),
         Paragraph("기술 기반 실감형 콘텐츠", cell_style)],
        [Paragraph("③ 플랫폼/솔루션\n   실증 제작", cell_bold),
         Paragraph("AI 콘텐츠 제작 플랫폼/솔루션 개발 + 실증", cell_style),
         Paragraph("8개", cell_center),
         Paragraph("플랫폼/솔루션 + 콘텐츠\n활용 결과물 모두 포함", cell_style)],
    ]
    story.append(make_table(type_data, col_widths=[W*0.17, W*0.38, W*0.1, W*0.35]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1-2. 핵심 조건", h2_style))
    conditions = [
        "주관기관: <b>중소기업만</b> 가능 (법인사업자, 중소기업확인서 필요)",
        "참여기관: 중소기업, 대기업, 중견기업, 비영리법인 가능 (단, 국고는 중소기업만)",
        "AI 기술: <b>자체 개발·고도화한 AI 제작 파이프라인</b> 필수 — 범용 AI 단순 활용 지양",
        "IP: 컨소시엄(주관 또는 참여기관)이 직접 기획하고 보유해야 함",
        "협약기간 내 콘텐츠 제작 완료 + 공개 필수",
        "IR 피칭 1회 이상 필수 수행",
        "일반용역비: 총사업비의 30% 이하",
        "1기업 1과제 수행 원칙 (복수 신청 가능, 둘 다 선정 시 1개만 수행)",
    ]
    for c in conditions:
        story.append(Paragraph(f"• {c}", bullet_style))

    story.append(PageBreak())

    # ═══════════════════════════════════
    # 2. 평가기준 분석
    # ═══════════════════════════════════
    story.append(Paragraph("2. 평가기준 분석", h1_style))

    story.append(Paragraph("2-1. 서면평가 (1단계, 40%)", h2_style))
    eval1_data = [
        [Paragraph("구분", cell_header), Paragraph("세부지표", cell_header), Paragraph("배점", cell_header), Paragraph("우리 전략", cell_header)],
        [Paragraph("수행기관\n(10점)", cell_bold), Paragraph("기관 전문성 (5)\n관리 체계성 (5)", cell_style), Paragraph("10", cell_center),
         Paragraph("AI 콘텐츠 제작 경험 → LoRA PoC 결과 + 웹툰 연재 실적", cell_style)],
        [Paragraph("참여인력\n(5점)", cell_bold), Paragraph("인력 구성, 유사과제 수행경험", cell_style), Paragraph("5", cell_center),
         Paragraph("AI 엔지니어 + 웹툰 작가 조합 어필", cell_style)],
        [Paragraph("과제 기획력\n(45점)", cell_bold), Paragraph("AI기술 융합성 (20)\n사업 이해도 (15)\n경쟁력 (10)", cell_style), Paragraph("45", cell_center),
         Paragraph("★ 최대 배점 — 자체 LoRA 파이프라인(20점)\n진입형 목적 부합(15점)\n화백 IP 차별성(10점)", cell_style)],
        [Paragraph("기대성과\n(30점)", cell_bold), Paragraph("시장성 (15)\n투자유치 가능성 (15)", cell_style), Paragraph("30", cell_center),
         Paragraph("네이버 웹툰 연재 = 유통채널 확보(15점)\nAI 웹툰 시장 투자 트렌드 활용(15점)", cell_style)],
        [Paragraph("사업비\n(10점)", cell_bold), Paragraph("규모 적정성 (5)\n조달계획 (5)", cell_style), Paragraph("10", cell_center),
         Paragraph("2억 적정 편성 + 자부담 인건비 편성", cell_style)],
    ]
    story.append(make_table(eval1_data, col_widths=[W*0.13, W*0.25, W*0.07, W*0.55]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2-2. 발표평가 (2단계, 60%)", h2_style))
    eval2_data = [
        [Paragraph("구분", cell_header), Paragraph("세부지표", cell_header), Paragraph("배점", cell_header)],
        [Paragraph("수행기관 (15)", cell_bold), Paragraph("기관 전문성(5) + 관리 체계성(5) + 추진 의지(5)", cell_style), Paragraph("15", cell_center)],
        [Paragraph("과제 기획력 (50)", cell_bold), Paragraph("AI기술 융합성(20) + 사업 이해도(15) + 경쟁력(15)", cell_style), Paragraph("50", cell_center)],
        [Paragraph("기대성과 (33)", cell_bold), Paragraph("시장성(13) + 투자유치(10) + 품질 경쟁력(10)", cell_style), Paragraph("33", cell_center)],
        [Paragraph("ESG (2)", cell_bold), Paragraph("일자리 창출(1) + 지역균형(1, 비수도권)", cell_style), Paragraph("2", cell_center)],
    ]
    story.append(make_table(eval2_data, col_widths=[W*0.2, W*0.65, W*0.15]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("※ 대전 소재 기업 = 지역균형 가산점 1점 확보", small_style))

    story.append(PageBreak())

    # ═══════════════════════════════════
    # 3. 2트랙 신청 전략
    # ═══════════════════════════════════
    story.append(Paragraph("3. 2트랙 신청 전략", h1_style))

    story.append(Paragraph(
        "인튜웍스가 두 가지 컨소시엄으로 동시 신청하고, 둘 다 선정 시 유리한 쪽을 선택하는 전략.",
        body_style))

    story.append(Paragraph("3-1. 트랙 A: 플랫폼/솔루션 실증 (인튜웍스 + 위즈데이터)", h2_style))

    trackA_data = [
        [Paragraph("항목", cell_header), Paragraph("내용", cell_header)],
        [Paragraph("유형", cell_bold), Paragraph("③ 콘텐츠 플랫폼/솔루션 실증 제작", cell_style)],
        [Paragraph("주관기관", cell_bold), Paragraph("인튜웍스 — AI 화풍 변환 플랫폼 개발, 과제 총괄", cell_style)],
        [Paragraph("참여기관", cell_bold), Paragraph("위즈데이터 — 화백 IP 제공, 원화 데이터, 콘텐츠 기획", cell_style)],
        [Paragraph("과제명(안)", cell_bold), Paragraph("'한국 만화 화백 화풍 AI 변환 플랫폼 개발 및 콘텐츠 제작 실증'", cell_style)],
        [Paragraph("결과물", cell_bold), Paragraph("① AI 화풍 변환 웹 플랫폼 (SaaS)\n② 플랫폼 활용 콘텐츠 제작물 (삽화, 캐릭터 굿즈 등)", cell_style)],
        [Paragraph("강점", cell_bold), Paragraph("• 인튜웍스 주도권 확보\n• 플랫폼 개발에 집중 가능\n• 화백 IP 직접 활용", cell_style)],
        [Paragraph("약점", cell_bold), Paragraph("• 콘텐츠 유통 채널 부재\n• 시장성 입증이 상대적으로 약함", cell_style)],
    ]
    story.append(make_table(trackA_data, col_widths=[W*0.18, W*0.82]))
    story.append(Spacer(1, 15))

    story.append(Paragraph("3-2. 트랙 B: 장르 융합 — 웹툰 + AI (웹툰회사 + 인튜웍스)", h2_style))

    trackB_data = [
        [Paragraph("항목", cell_header), Paragraph("내용", cell_header)],
        [Paragraph("유형", cell_bold), Paragraph("① 장르 융합 (기존 장르 + AI 기술)", cell_style)],
        [Paragraph("주관기관", cell_bold), Paragraph("(친구 웹툰회사) — 웹툰 기획·제작·연재, 과제 총괄", cell_style)],
        [Paragraph("참여기관", cell_bold), Paragraph("인튜웍스 — AI 화풍 변환 기술 개발·적용", cell_style)],
        [Paragraph("IP 협력", cell_bold), Paragraph("위즈데이터 — 화백 IP 라이선싱 계약 (컨소시엄 외부)", cell_style)],
        [Paragraph("과제명(안)", cell_bold), Paragraph("'한국 거장 만화 화백 화풍 AI 활용 신규 웹툰 제작'", cell_style)],
        [Paragraph("결과물", cell_bold), Paragraph("① AI 화풍 변환 기술로 제작한 웹툰 (네이버 웹툰 연재)\n② 화백 화풍 활용 콘텐츠 (캐릭터, 삽화 등)", cell_style)],
        [Paragraph("강점", cell_bold), Paragraph("• 네이버 웹툰 연재 = 시장성 즉시 입증 ★\n• 웹툰 제작 전문성 + AI 기술 조합\n• 평가 고배점 항목(기획력+시장성) 강함", cell_style)],
        [Paragraph("약점", cell_bold), Paragraph("• 인튜웍스 참여기관 = 주도권 제한\n• 웹툰회사 동의/참여 확정 필요", cell_style)],
    ]
    story.append(make_table(trackB_data, col_widths=[W*0.18, W*0.82]))
    story.append(Spacer(1, 15))

    story.append(Paragraph("3-3. 트랙 비교", h2_style))
    comp_data = [
        [Paragraph("비교항목", cell_header), Paragraph("트랙 A (인튜+위즈)", cell_header), Paragraph("트랙 B (웹툰+인튜)", cell_header)],
        [Paragraph("유형", cell_bold), Paragraph("③ 플랫폼/솔루션 실증", cell_style), Paragraph("① 장르 융합 (웹툰+AI)", cell_style)],
        [Paragraph("인튜웍스 역할", cell_bold), Paragraph("주관기관 (주도권 ◎)", cell_style), Paragraph("참여기관 (기술 집중)", cell_style)],
        [Paragraph("AI 기술 융합성\n(20점)", cell_bold), Paragraph("◎ 동일 (자체 LoRA 파이프라인)", cell_style), Paragraph("◎ 동일", cell_style)],
        [Paragraph("시장성\n(15점/13점)", cell_bold), Paragraph("△ 플랫폼 사용자 확보 필요", cell_style), Paragraph("◎ 네이버 웹툰 연재 실적", cell_style)],
        [Paragraph("투자유치 가능성\n(15점/10점)", cell_bold), Paragraph("○ SaaS 플랫폼 투자", cell_style), Paragraph("◎ AI 웹툰 시장 트렌드", cell_style)],
        [Paragraph("결과물 부담", cell_bold), Paragraph("높음 (플랫폼+콘텐츠 둘 다)", cell_style), Paragraph("보통 (웹툰 제작에 집중)", cell_style)],
        [Paragraph("예상 경쟁력", cell_bold), Paragraph("★★★☆☆", cell_style), Paragraph("★★★★☆", cell_style)],
    ]
    story.append(make_table(comp_data, col_widths=[W*0.2, W*0.4, W*0.4]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("※ 공고 조건: 2개 동시 신청 가능, 둘 다 선정 시 1개만 수행", small_style))

    story.append(PageBreak())

    # ═══════════════════════════════════
    # 4. 보유 기술 현황 (PoC 결과)
    # ═══════════════════════════════════
    story.append(Paragraph("4. 보유 AI 기술 현황 (PoC 결과)", h1_style))

    story.append(Paragraph(
        "인튜웍스는 이미 SDXL + LoRA 기반 만화 화백 화풍 변환 AI 파이프라인을 자체 구축하고, "
        "2명의 화백 데이터로 학습 및 테스트를 완료한 상태입니다.",
        body_style))

    story.append(Paragraph("4-1. 기술 스택", h2_style))
    tech_data = [
        [Paragraph("구분", cell_header), Paragraph("내용", cell_header)],
        [Paragraph("Base Model", cell_bold), Paragraph("Stable Diffusion XL (SDXL) 1.0", cell_style)],
        [Paragraph("Fine-tuning", cell_bold), Paragraph("LoRA (Low-Rank Adaptation) — kohya sd-scripts", cell_style)],
        [Paragraph("추론", cell_bold), Paragraph("img2img Pipeline (Hugging Face Diffusers)", cell_style)],
        [Paragraph("GPU", cell_bold), Paragraph("NVIDIA RTX 4090 (24GB VRAM)", cell_style)],
        [Paragraph("학습 파라미터", cell_bold), Paragraph("dim=32, alpha=16, lr=1e-4, AdamW8bit, cosine_with_restarts, bf16", cell_style)],
        [Paragraph("핵심 차별점", cell_bold), Paragraph("범용 AI 서비스가 아닌 특정 화백의 고유 화풍을 학습한 자체 모델\n화백당 50~100장의 원화만으로 화풍 학습 가능", cell_style)],
    ]
    story.append(make_table(tech_data, col_widths=[W*0.2, W*0.8]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4-2. 학습 결과", h2_style))
    train_data = [
        [Paragraph("화백", cell_header), Paragraph("학습 이미지", cell_header), Paragraph("총 Steps", cell_header),
         Paragraph("학습 시간", cell_header), Paragraph("최종 Loss", cell_header)],
        [Paragraph("이정문 화백", cell_bold), Paragraph("51장", cell_center), Paragraph("5,100", cell_center),
         Paragraph("~31분", cell_center), Paragraph("0.0319", cell_center)],
        [Paragraph("신문수 화백", cell_bold), Paragraph("90장", cell_center), Paragraph("5,400", cell_center),
         Paragraph("~42분", cell_center), Paragraph("0.0846", cell_center)],
    ]
    story.append(make_table(train_data, col_widths=[W*0.2, W*0.2, W*0.2, W*0.2, W*0.2]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4-3. 화풍 변환 테스트 결과 (신문수 화백)", h2_style))
    test_data = [
        [Paragraph("Strength", cell_header), Paragraph("SSIM", cell_header), Paragraph("PSNR (dB)", cell_header),
         Paragraph("Histogram Sim", cell_header), Paragraph("평가", cell_header)],
        [Paragraph("50%", cell_center), Paragraph("0.50 / 0.66", cell_center), Paragraph("19.7 / 21.6", cell_center),
         Paragraph("0.98 / 0.66", cell_center), Paragraph("변환 부족", cell_style)],
        [Paragraph("65% ★", cell_bold), Paragraph("0.37 / 0.55", cell_center), Paragraph("15.8 / 18.4", cell_center),
         Paragraph("0.97 / 0.67", cell_center), Paragraph("최적 밸런스", cell_style)],
        [Paragraph("80%", cell_center), Paragraph("0.28 / 0.38", cell_center), Paragraph("12.8 / 13.8", cell_center),
         Paragraph("0.96 / 0.57", cell_center), Paragraph("원본 훼손", cell_style)],
    ]
    story.append(make_table(test_data, col_widths=[W*0.12, W*0.2, W*0.2, W*0.2, W*0.28]))
    story.append(Paragraph("※ 각 셀 = 사진1 / 사진2 결과. Strength 65%가 화풍 변환과 원본 유지의 최적 균형점.", small_style))

    story.append(PageBreak())

    # ═══════════════════════════════════
    # 5. 사업비 편성 (안)
    # ═══════════════════════════════════
    story.append(Paragraph("5. 사업비 편성 (안)", h1_style))

    story.append(Paragraph("5-1. 트랙 A 사업비 (인튜웍스 + 위즈데이터)", h2_style))
    budgetA_data = [
        [Paragraph("항목", cell_header), Paragraph("인튜웍스\n(주관)", cell_header), Paragraph("위즈데이터\n(참여)", cell_header), Paragraph("합계", cell_header)],
        [Paragraph("인건비", cell_bold), Paragraph("60,000", cell_center), Paragraph("40,000", cell_center), Paragraph("100,000", cell_center)],
        [Paragraph("클라우드/GPU", cell_bold), Paragraph("25,000", cell_center), Paragraph("5,000", cell_center), Paragraph("30,000", cell_center)],
        [Paragraph("일반수용비\n(AI 구독, 홍보)", cell_bold), Paragraph("15,000", cell_center), Paragraph("8,000", cell_center), Paragraph("23,000", cell_center)],
        [Paragraph("일반용역비\n(디자인, 테스트)", cell_bold), Paragraph("30,000", cell_center), Paragraph("17,000", cell_center), Paragraph("47,000", cell_center)],
        [Paragraph("국고 소계", cell_bold), Paragraph("130,000", cell_center), Paragraph("70,000", cell_center), Paragraph("200,000", cell_center)],
        [Paragraph("자부담 (인건비)", cell_bold), Paragraph("13,000", cell_center), Paragraph("10,000", cell_center), Paragraph("23,000", cell_center)],
        [Paragraph("총사업비", cell_bold), Paragraph("143,000", cell_center), Paragraph("80,000", cell_center), Paragraph("223,000", cell_center)],
    ]
    story.append(make_table(budgetA_data, col_widths=[W*0.25, W*0.25, W*0.25, W*0.25]))
    story.append(Paragraph("(단위: 천원) ※ 일반용역비 47,000천원 = 총사업비의 21% (30% 이내 충족)", small_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph("5-2. 트랙 B 사업비 (웹툰회사 + 인튜웍스)", h2_style))
    budgetB_data = [
        [Paragraph("항목", cell_header), Paragraph("웹툰회사\n(주관)", cell_header), Paragraph("인튜웍스\n(참여)", cell_header), Paragraph("합계", cell_header)],
        [Paragraph("인건비", cell_bold), Paragraph("55,000", cell_center), Paragraph("45,000", cell_center), Paragraph("100,000", cell_center)],
        [Paragraph("클라우드/GPU", cell_bold), Paragraph("5,000", cell_center), Paragraph("25,000", cell_center), Paragraph("30,000", cell_center)],
        [Paragraph("일반수용비\n(AI 구독, 홍보)", cell_bold), Paragraph("20,000", cell_center), Paragraph("5,000", cell_center), Paragraph("25,000", cell_center)],
        [Paragraph("일반용역비\n(외주, 후반작업)", cell_bold), Paragraph("35,000", cell_center), Paragraph("10,000", cell_center), Paragraph("45,000", cell_center)],
        [Paragraph("국고 소계", cell_bold), Paragraph("115,000", cell_center), Paragraph("85,000", cell_center), Paragraph("200,000", cell_center)],
        [Paragraph("자부담 (인건비)", cell_bold), Paragraph("13,000", cell_center), Paragraph("10,000", cell_center), Paragraph("23,000", cell_center)],
        [Paragraph("총사업비", cell_bold), Paragraph("128,000", cell_center), Paragraph("95,000", cell_center), Paragraph("223,000", cell_center)],
    ]
    story.append(make_table(budgetB_data, col_widths=[W*0.25, W*0.25, W*0.25, W*0.25]))
    story.append(Paragraph("(단위: 천원)", small_style))

    story.append(PageBreak())

    # ═══════════════════════════════════
    # 6. 추진 일정
    # ═══════════════════════════════════
    story.append(Paragraph("6. 추진 일정", h1_style))

    story.append(Paragraph("6-1. 신청 준비 일정 (D-11)", h2_style))
    prep_data = [
        [Paragraph("기간", cell_header), Paragraph("내용", cell_header), Paragraph("담당", cell_header)],
        [Paragraph("2/23 (월)", cell_bold), Paragraph("사업 검토 회의, 컨소시엄 구조 확정", cell_style), Paragraph("전원", cell_center)],
        [Paragraph("2/24~25", cell_bold), Paragraph("웹툰회사 참여 의향 확인\n과제 컨셉 합의 (화백/웹툰 방향)", cell_style), Paragraph("방기", cell_center)],
        [Paragraph("2/26~28", cell_bold), Paragraph("사업신청서 초안 작성\n사업비 세부산출내역서 작성", cell_style), Paragraph("전원", cell_center)],
        [Paragraph("3/1~2", cell_bold), Paragraph("참여인력 이력서, 증빙서류 준비\n위즈데이터 IP 라이선싱 의향서", cell_style), Paragraph("각 기관", cell_center)],
        [Paragraph("3/3~4", cell_bold), Paragraph("최종 검토 및 보완\ne나라도움 시스템 테스트", cell_style), Paragraph("전원", cell_center)],
        [Paragraph("3/5 (수)", cell_bold), Paragraph("e나라도움 최종 접수 (마감 전일)", cell_style), Paragraph("주관기관", cell_center)],
        [Paragraph("3/6 11:00", cell_bold), Paragraph("★ 접수 마감", cell_style), Paragraph("-", cell_center)],
    ]
    story.append(make_table(prep_data, col_widths=[W*0.18, W*0.6, W*0.22]))
    story.append(Spacer(1, 15))

    story.append(Paragraph("6-2. 사업 수행 일정 (선정 시)", h2_style))
    exec_data = [
        [Paragraph("기간", cell_header), Paragraph("내용", cell_header)],
        [Paragraph("4~5월", cell_bold), Paragraph("추가 화백 데이터 확보, IP 라이선싱 체결\nControlNet + IP-Adapter 도입 (얼굴 유사도 향상)", cell_style)],
        [Paragraph("6~7월", cell_bold), Paragraph("웹 플랫폼 개발 (트랙A) / AI 활용 웹툰 제작 착수 (트랙B)", cell_style)],
        [Paragraph("8~9월", cell_bold), Paragraph("콘텐츠 제작 및 실증\n중간점검 (예산집행 부문) → 2차 지원금 수령", cell_style)],
        [Paragraph("10~11월", cell_bold), Paragraph("시장 검증, IR 피칭 수행 (1회 이상 필수)\n결과물 공개, 최종 보고", cell_style)],
    ]
    story.append(make_table(exec_data, col_widths=[W*0.15, W*0.85]))

    story.append(PageBreak())

    # ═══════════════════════════════════
    # 7. 논의사항
    # ═══════════════════════════════════
    story.append(Paragraph("7. 논의 필요 사항", h1_style))

    items = [
        ("컨소시엄 구조 확정", "2트랙 동시 신청 vs 1트랙 집중? 트랙 B 진행 시 웹툰회사 참여 의향 확인 필요"),
        ("과제 컨셉", "어떤 화백의 화풍으로 할 것인지? 웹툰 장르/주제는?"),
        ("위즈데이터 참여 형태", "트랙 A: 참여기관 / 트랙 B: IP 라이선싱 계약만 (컨소 외부)"),
        ("웹툰회사 정보", "회사명, 대표자, 연재 실적, 중소기업 확인서 발급 가능 여부"),
        ("화백 IP 라이선싱", "위즈데이터와 IP 사용 계약/의향서 준비 일정"),
        ("자부담금", "각 기관 현금 자부담 가능 금액 확인 (총 ~2,300만원)"),
        ("e나라도움 접수", "사업자등록증, 중소기업확인서 등 행정서류 준비 상태"),
    ]
    for i, (title, desc) in enumerate(items, 1):
        story.append(Paragraph(f"<b>{i}. {title}</b>", body_style))
        story.append(Paragraph(f"→ {desc}", body_indent))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    story.append(Spacer(1, 10))
    story.append(Paragraph("본 자료는 내부 검토용이며, 공고문 원문은 KOCCA 홈페이지 및 e나라도움을 참고하시기 바랍니다.", small_style))
    story.append(Paragraph("문의: AI융복합콘텐츠팀 ☎ 061-900-6356, 6357", small_style))

    # Build
    doc.build(story)
    print(f"✅ PDF 생성 완료: {PDF_PATH}")
    print(f"   파일 크기: {PDF_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == '__main__':
    build_pdf()
