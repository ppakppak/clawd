#!/usr/bin/env python3
"""ToonStyle AI 파이프라인 도식화 v3 — 단일 패스 (txt2img + ControlNet + FaceID).

폰트 크기 대폭 키움 (제안서 삽입 시 가독성 확보).
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ── 한글 폰트 설정 ──
for fname in ['NanumGothic', 'Malgun Gothic', 'NanumBarunGothic', 'DejaVu Sans']:
    try:
        matplotlib.rcParams['font.family'] = fname
        fig_test = plt.figure()
        fig_test.text(0.5, 0.5, '테스트')
        fig_test.savefig('/dev/null', format='png')
        plt.close(fig_test)
        print(f"Font: {fname}")
        break
    except:
        continue

matplotlib.rcParams['axes.unicode_minus'] = False

# ── 색상 팔레트 ──
BG = '#FFFFFF'
PRIMARY = '#4F46E5'       # indigo-600
PRIMARY_L = '#E0E7FF'     # indigo-100
SECONDARY = '#0EA5E9'     # sky-500
SECONDARY_L = '#E0F2FE'   # sky-100
ACCENT = '#10B981'        # emerald-500
ACCENT_L = '#D1FAE5'      # emerald-100
DARK = '#1E293B'          # slate-800
GRAY = '#64748B'          # slate-500
LIGHT_GRAY = '#F1F5F9'    # slate-100
ARROW_COLOR = '#475569'
WARN = '#F59E0B'          # amber-500
WARN_L = '#FEF3C7'        # amber-100

fig, ax = plt.subplots(1, 1, figsize=(16, 10), dpi=250)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis('off')


def draw_box(x, y, w, h, color, border_color, text_lines, title=None, title_color='white',
             title_size=16, text_size=14):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                          facecolor=color, edgecolor=border_color, linewidth=2.5)
    ax.add_patch(box)
    if title:
        title_box = FancyBboxPatch((x, y+h-0.7), w, 0.7, boxstyle="round,pad=0.1",
                                    facecolor=border_color, edgecolor=border_color, linewidth=0)
        ax.add_patch(title_box)
        ax.text(x + w/2, y + h - 0.35, title, ha='center', va='center',
                fontsize=title_size, fontweight='bold', color=title_color)
        text_y = y + (h - 0.7) / 2
    else:
        text_y = y + h / 2

    for i, line in enumerate(text_lines):
        offset = (len(text_lines) - 1) / 2 - i
        ax.text(x + w/2, text_y + offset * 0.4, line, ha='center', va='center',
                fontsize=text_size, color=DARK)


def draw_arrow(x1, y1, x2, y2, color=ARROW_COLOR, label=None, label_size=13):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                             arrowstyle='->', mutation_scale=25,
                             color=color, linewidth=3)
    ax.add_patch(arrow)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2 + 0.25
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=label_size, color=color, fontweight='bold')


# ══════════════════════════════════════════════
# 제목
# ══════════════════════════════════════════════
ax.text(8, 9.5, 'ToonStyle AI — 추론 파이프라인 (단일 패스)', ha='center', va='center',
        fontsize=26, fontweight='bold', color=DARK)

ax.plot([0.5, 15.5], [9.1, 9.1], color='#E2E8F0', linewidth=1.5)

# ══════════════════════════════════════════════
# SECTION 1: 단일 패스 변환 파이프라인
# ══════════════════════════════════════════════
ax.text(0.8, 8.7, '■ AI 변환 엔진 (~4초/장, 단일 패스)', fontsize=18, fontweight='bold', color=PRIMARY)

# ── 사용자 입력 ──
draw_box(0.5, 6.0, 2.6, 2.2, LIGHT_GRAY, GRAY,
         ['사진 업로드', '화백·버전 선택', '파라미터 조절'],
         title='사용자 입력', title_size=15, text_size=14)

# ── Arrow ──
draw_arrow(3.25, 7.1, 4.05, 7.1, ARROW_COLOR)

# ── 중앙: AI 변환 엔진 (큰 박스) ──
# 엔진 외곽 박스
engine_box = FancyBboxPatch((4.1, 5.6, ), 7.8, 3.0, boxstyle="round,pad=0.2",
                             facecolor='#F8FAFC', edgecolor=PRIMARY, linewidth=3, linestyle='--')
ax.add_patch(engine_box)
ax.text(8, 8.35, 'SDXL txt2img + LoRA (fuse)', ha='center', va='center',
        fontsize=17, fontweight='bold', color=PRIMARY)
ax.text(8, 7.9, 'guidance = 8.0  |  steps = 30  |  1024px', ha='center', va='center',
        fontsize=14, color=GRAY)

# ── ControlNet 서브박스 ──
draw_box(4.4, 5.9, 3.4, 1.7, PRIMARY_L, PRIMARY,
         ['Canny 엣지맵 추출', 'scale = 0.65'],
         title='ControlNet (Canny)', title_size=14, text_size=14)

# 화살표 레이블
ax.text(5.85, 5.55, '구조·윤곽 가이드', ha='center', va='center',
        fontsize=13, color=PRIMARY, style='italic')

# ── FaceID 서브박스 ──
draw_box(8.4, 5.9, 3.2, 1.7, SECONDARY_L, SECONDARY,
         ['InsightFace 512d 임베딩', 'scale = 0.40'],
         title='IP-Adapter-FaceID', title_size=14, text_size=14)

ax.text(9.8, 5.55, '얼굴 정체성 주입', ha='center', va='center',
        fontsize=13, color=SECONDARY, style='italic')

# ── Arrow → 출력 ──
draw_arrow(12.05, 7.1, 12.85, 7.1, ACCENT)

# ── 출력 ──
draw_box(12.9, 6.0, 2.6, 2.2, ACCENT_L, ACCENT,
         ['화풍 변환 이미지', '다운로드', '갤러리 저장'],
         title='출력', title_size=15, text_size=14)

# ── 핵심 설명 ──
ax.text(8, 5.05, '※ 핵심: 원본 사진 픽셀을 직접 사용하지 않음 (img2img X)',
        ha='center', va='center', fontsize=15, fontweight='bold', color='#DC2626')
ax.text(8, 4.65, 'Canny 엣지(구조)와 FaceID 임베딩(얼굴)만 추출 → LoRA 화풍 재현도 극대화',
        ha='center', va='center', fontsize=14, color=GRAY)

# ══════════════════════════════════════════════
# SECTION 2: 모델 학습 파이프라인
# ══════════════════════════════════════════════
ax.plot([0.5, 15.5], [4.15, 4.15], color='#E2E8F0', linewidth=1.5)
ax.text(0.8, 3.75, '■ 모델 학습 파이프라인', fontsize=18, fontweight='bold', color=ACCENT)

# ── 원화 ──
draw_box(0.5, 1.6, 2.8, 1.8, LIGHT_GRAY, GRAY,
         ['작가 원화', '50~100장/작가'],
         title='IP 데이터', title_size=15, text_size=14)

# ── Arrow ──
draw_arrow(3.45, 2.5, 4.25, 2.5, ARROW_COLOR)

# ── 전처리 ──
draw_box(4.3, 1.6, 3.0, 1.8, PRIMARY_L, PRIMARY,
         ['이미지 선별/정제', '자동 분석 캡셔닝'],
         title='자동 전처리', title_size=15, text_size=14)

# ── Arrow ──
draw_arrow(7.45, 2.5, 8.25, 2.5, ARROW_COLOR)

# ── 학습 ──
draw_box(8.3, 1.6, 3.2, 1.8, SECONDARY_L, SECONDARY,
         ['dim=32, alpha=16', '~40분/작가, TensorBoard'],
         title='SDXL LoRA 학습', title_size=15, text_size=14)

# ── Arrow ──
draw_arrow(11.65, 2.5, 12.45, 2.5, ARROW_COLOR)

# ── 모델 산출 ──
draw_box(12.5, 1.6, 3.0, 1.8, ACCENT_L, ACCENT,
         ['작가 화풍 모델', 'v1 / v2 / v2-strong'],
         title='산출물', title_size=15, text_size=14)

# ══════════════════════════════════════════════
# 범례
# ══════════════════════════════════════════════
ax.plot([0.5, 15.5], [1.1, 1.1], color='#E2E8F0', linewidth=1)

legend_items = [
    (PRIMARY, '자체 개발 기술'),
    (SECONDARY, '오픈소스 연동'),
    (ACCENT, '결과물/산출물'),
    (GRAY, '입력/데이터'),
]
for i, (color, label) in enumerate(legend_items):
    x = 2.5 + i * 3.2
    rect = FancyBboxPatch((x, 0.45), 0.5, 0.35, boxstyle="round,pad=0.05",
                           facecolor=color, edgecolor=color, linewidth=0)
    ax.add_patch(rect)
    ax.text(x + 0.65, 0.62, label, fontsize=13, color=DARK, va='center')

# 용어 해설은 DOCX 본문 텍스트로 삽입 (이미지 아님)

plt.tight_layout(pad=0.5)
out = '/home/ppak/clawd/kocca-proposal/track-a/pipeline_diagram_v3.png'
fig.savefig(out, dpi=250, bbox_inches='tight', facecolor=BG)
plt.close()
print(f'✅ 저장: {out}')
