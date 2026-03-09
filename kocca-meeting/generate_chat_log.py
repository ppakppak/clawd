#!/usr/bin/env python3
"""
KOCCA 사업 검토 대화 로그를 PDF로 생성 (카톡/메신저 캡쳐 스타일)
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Korean font ──
for fp, fname in [
    ('/usr/share/fonts/truetype/nanum/NanumGothic.ttf', 'NanumGothic'),
    ('/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf', 'NanumGothicBold'),
]:
    if os.path.exists(fp):
        pdfmetrics.registerFont(TTFont(fname, fp))

FONT = 'NanumGothic'
FONT_B = 'NanumGothicBold'

# Colors
USER_BG = HexColor('#FFF9C4')  # 연노랑
AI_BG = HexColor('#E3F2FD')    # 연파랑
USER_BORDER = HexColor('#F9A825')
AI_BORDER = HexColor('#1565C0')
GRAY = HexColor('#9e9e9e')
DARK = HexColor('#212121')

OUT = Path(os.path.expanduser("~/clawd/kocca-meeting"))
PDF_PATH = OUT / "KOCCA_검토_대화로그.pdf"

# ── Styles ──
title_s = ParagraphStyle('Title', fontName=FONT_B, fontSize=16, leading=22,
                         textColor=HexColor('#1a237e'), alignment=TA_CENTER, spaceAfter=4)
subtitle_s = ParagraphStyle('Sub', fontName=FONT, fontSize=10, leading=14,
                            textColor=GRAY, alignment=TA_CENTER, spaceAfter=16)
time_s = ParagraphStyle('Time', fontName=FONT, fontSize=8, leading=10,
                        textColor=GRAY, alignment=TA_CENTER, spaceAfter=8, spaceBefore=12)
user_name_s = ParagraphStyle('UName', fontName=FONT_B, fontSize=9, leading=12,
                             textColor=HexColor('#E65100'))
ai_name_s = ParagraphStyle('AName', fontName=FONT_B, fontSize=9, leading=12,
                           textColor=HexColor('#1565C0'))
msg_s = ParagraphStyle('Msg', fontName=FONT, fontSize=9.5, leading=14.5,
                       textColor=DARK)
msg_small = ParagraphStyle('MsgSm', fontName=FONT, fontSize=8.5, leading=13,
                           textColor=DARK)


def chat_bubble(sender, text, time_str=None, small=False):
    """Create a chat bubble as a table."""
    is_user = (sender == "방기")
    bg = USER_BG if is_user else AI_BG
    border = USER_BORDER if is_user else AI_BORDER
    name_style = user_name_s if is_user else ai_name_s
    s = msg_small if small else msg_s

    # Build content
    parts = []
    parts.append(Paragraph(f"{'👤 방기' if is_user else '🤖 정아'}" + (f"  <font size=7 color='#9e9e9e'>{time_str}</font>" if time_str else ""), name_style))
    
    # Handle multiline text
    for line in text.split('\n'):
        if line.strip():
            # Escape XML special chars
            line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            # Re-add our formatting tags
            line = line.replace('**', '')  # strip markdown bold for now
            parts.append(Paragraph(line, s))
        else:
            parts.append(Spacer(1, 4))

    # Wrap in table for bubble effect
    inner = Table([[p] for p in parts], colWidths=[440])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('BOX', (0, 0), (-1, -1), 1.2, border),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ]))
    return inner


# ═══════════════════════════════════════
# Conversation data
# ═══════════════════════════════════════
conversation = [
    ("time", "2026년 2월 23일 (월)  —  KOCCA 사업 검토 대화"),

    ("time", "14:52"),
    ("방기", "'/home/ppak/Documents/카카오톡 받은 파일/[중소기업기술정보진흥원]「2026년 도메인특화AI모델개발사업」명(요약) 및 32개 후보품목 현황.pdf'\n→ 여기에 내가 낄 자리 있을끼?"),
    ("정아", """쭉 읽어봤어요. 32개 품목 기준으로 방기씨 역량이랑 매칭해볼게요.

🎯 끼어볼 만한 품목

#29. 설비의 이상을 예측 및 탐지하는 AI ⭐ 가장 유력
- 승강기 엣지 추론 프로젝트(xavier)가 정확히 여기에 해당
- 센서 데이터 기반 고장 예측, 이상 탐지, 예지보전
- 핵심기술: 시계열 예측, 이상 탐지, IoT 센서 분석

#28. 근로 현장 안전사고 예방 AI ⭐ 차선
- 승강기 현장 CCTV + 컴퓨터 비전 → 안전 감시

#30. 환경오염·배출 모니터링 AI △ 가능
- iPipeCheck(관로 CCTV 진단)를 수도관 환경 모니터링으로 확장 해석
- 다만 품목 취지가 탄소배출/에너지 중심이라 약간 억지

❌ ToonStyle AI(만화 화풍 변환) → 32개 품목에 해당 없음
- 이건 AI 바우처 쪽이 맞음

💡 현실적 판단:
- 예산: 과제당 25억 (정부 75%, 민간 25% = 약 6.25억 자부담)
- 구조: 공급기업(주관) + SI기업(공동) + 수요기업 3개 이상
- #29(설비 이상 예측)에 승강기 프로젝트로 가는 게 가장 자연스러움
- 공동기관(SI 역할)으로 참여하는 게 진입 장벽이 낮을 수 있음"""),

    ("time", "15:17"),
    ("방기", "이 문서 공고문은 어디에 있을까?"),
    ("정아", """smtech.go.kr(중기부 종합관리시스템) 현재 공고 목록에는 아직 안 올라와 있어요.

PDF 첫 장에 이렇게 적혀있었어요:
"본 자료는 후보품목에 대한 의견수렴을 위한 자료이며, 목적 외 무단배포를 금합니다."

즉, 이건 정식 공고 전 단계 — 후보품목 의견수렴용 사전 자료예요.

공고 나오면 볼 곳:
- smtech.go.kr → R&D 사업공고
- IRIS (범부처통합연구지원시스템)
- 중소기업기술정보진흥원(TIPA) 홈페이지"""),

    ("time", "15:41"),
    ("방기", "'/home/ppak/SynologyDrive/ykpark/wizdata/붙임2. 신청양식_26제작지원_진입형'\n→ 폴더 내의 공고문을 참고로 어떤 전략으로 제안서를 작성해야 할지 고민해줘."),
    ("정아", """공고 쭉 분석했어요. 이거 ToonStyle AI에 딱 맞는 사업이에요! 🎯

📋 사업 요약
- 사업명: 2026년 인공지능 콘텐츠 제작지원 (진입형)
- 주관: 한국콘텐츠진흥원 (KOCCA)
- 국고: 과제당 최대 2억원 (자부담 10% = ~2,300만원)
- 기간: 2026.4.15 ~ 11.30 (7.5개월)
- ⚠️ 마감: 2026.3.6(금) 11:00 — 11일 남음!

🎯 추천 유형: ③ 플랫폼/솔루션 실증 제작
- 결과물 = AI 화풍 변환 웹 플랫폼(SaaS) + 실제 콘텐츠 제작물
- 이미 LoRA 학습 + img2img 파이프라인 PoC 있음

💪 강점:
1. AI 기술 자체 개발 (범용 AI 단순 활용 아님)
2. 문화적 가치 + 차별성 (화백 화풍 보존)
3. 이미 PoC 완료 (이정문 Loss 0.032, 신문수 Loss 0.085)
4. 대전 소재 → 지역가산점 1점

⚠️ 약점:
- 웹 플랫폼 아직 없음
- 화백 IP 계약 미체결
- KOCCA 수행실적 없음
- 투자유치 계획 미비"""),

    ("time", "15:48"),
    ("방기", "내 친한 인텔 동료가 퇴직하고, 네이버 웹툰에 연재하는 웹툰 회사를 하고 있는데…\n① 장르 융합 (기존장르+AI) 로 컨소 가능할까?"),
    ("정아", """이거 완벽한 조합이에요! 😮

✅ 컨소시엄 가능합니다.

추천 구조 (A안): 웹툰 회사 = 주관 / 방기씨 = 참여 ⭐
- 주관: 친구 웹툰 회사 → 웹툰 기획·제작·연재, 과제 총괄
- 참여: 방기씨 회사 → AI 화풍 변환 파이프라인 개발·운영

이 구조가 좋은 이유:
- "기관 전문성" 평가 = AI 기술 기반 콘텐츠 제작 경험 → 주관기관이 실제 웹툰 연재 실적 보유
- 네이버 웹툰 연재중 = 시장성 입증 (15점 배점)
- 방기씨는 AI 기술에 집중 가능

킬링 포인트:
"인텔 출신 엔지니어의 AI 기술 + 프로 웹툰 작가의 제작 역량"

과제 스토리라인:
한국 원로 만화 화백의 화풍을 AI로 학습 → 프로 웹툰 작가가 AI 보조로 새 웹툰 제작 → 네이버 웹툰에 실제 연재 → 시장 검증"""),

    ("time", "15:54"),
    ("방기", "아.. 웹툰회사는 다른 회사인데... 7080 ip 를 보유한 회사(wizdata)와는 다른 회사임."),
    ("정아", """아, 그러면 정리하면:
- 위즈데이터 (wizdata) — 7080 화백 IP 보유 (이정문, 신문수 등)
- 친구 웹툰 회사 — 네이버 웹툰 연재 중, 실제 웹툰 제작 역량
- 방기씨 회사 (인튜웍스) — AI 기술 (LoRA 파이프라인)

3사 컨소시엄도 가능하지만, 2억을 3사가 나누면 좀 빠듯.

2사 컨소시엄 구조 제안:
- 트랙A: 인튜웍스(주관) + 위즈데이터(참여) → ③ 플랫폼/솔루션 실증
- 트랙B: 웹툰회사(주관) + 인튜웍스(참여) → ① 장르 융합"""),

    ("time", "15:55"),
    ("방기", "방기는 인튜웍스 대표"),
    ("정아", "알겠어요! 기록해뒀어요.\n인튜웍스 (IntuWorks) = 방기씨 회사, AI 기술 개발 담당."),

    ("time", "15:57"),
    ("방기", "나는 인튜+위즈, 인튜+친구웹툰 이렇게 2트랙으로 신청할까 했는데..\n사업비 2억인데 셋이 나누긴 좀 작아서..."),
    ("정아", """2트랙 전략 좋아요!

트랙 A: ③ 플랫폼/솔루션 실증 — 인튜웍스(주관) + 위즈데이터(참여)
→ AI 화풍 변환 플랫폼 개발 + 콘텐츠 활용

트랙 B: ① 장르 융합 — 웹툰회사(주관) + 인튜웍스(참여)
→ AI 활용 웹툰 제작 + 네이버 연재

⚠️ 공고 조건 확인:
"1개 기업당 주관기관 또는 참여기관으로 신청 가능"
"둘 다 선정되면 1개만 수행 가능"

→ 사실상 보험 전략. A든 B든 하나 붙으면 좋고, 둘 다 붙으면 더 좋은 쪽 선택.

사업비 구조 (2사 기준):
트랙A: 인튜 ~1.3억 / 위즈 ~0.7억
트랙B: 웹툰 ~1.15억 / 인튜 ~0.85억

2사면 나눌 만하죠.

둘 다 붙으면:
→ 트랙 B 선택이 유리 (네이버 웹툰 시장성)
→ 트랙 A는 AI 바우처 쪽에서 별도 추진"""),

    ("time", "16:03"),
    ("방기", "지금까지의 콘진원 사업 관련 대화내용을 PDF로 정리해 줄수 있어?\n회의자료로 쓰게..."),
    ("정아", "지금 만들고 있어요! 📄"),
]


def build_pdf():
    doc = SimpleDocTemplate(
        str(PDF_PATH), pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm,
    )
    story = []

    # Title
    story.append(Paragraph("KOCCA 인공지능 콘텐츠 제작지원 — 검토 대화 로그", title_s))
    story.append(Paragraph("2026.02.23 방기 × 정아(AI) 대화 기록  |  내부 회의자료용", subtitle_s))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    story.append(Spacer(1, 10))

    for item in conversation:
        if item[0] == "time":
            story.append(Paragraph(f"— {item[1]} —", time_s))
        else:
            sender, text = item
            is_long = len(text) > 500
            bubble = chat_bubble(sender, text, small=is_long)
            story.append(bubble)
            story.append(Spacer(1, 8))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=GRAY))
    story.append(Paragraph("— 대화 종료 —", time_s))

    doc.build(story)
    print(f"✅ PDF 생성 완료: {PDF_PATH}")
    print(f"   파일 크기: {PDF_PATH.stat().st_size / 1024:.1f} KB")


if __name__ == '__main__':
    build_pdf()
