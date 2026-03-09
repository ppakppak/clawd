#!/usr/bin/env python3
"""ToonStyle AI 파이프라인 도식화 — 제안서 삽입용 인포그래픽."""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

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

fig, ax = plt.subplots(1, 1, figsize=(14, 9), dpi=200)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax.set_xlim(0, 14)
ax.set_ylim(0, 9)
ax.axis('off')

def draw_box(x, y, w, h, color, border_color, text_lines, title=None, title_color='white'):
    """Draw a rounded box with optional title bar."""
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                          facecolor=color, edgecolor=border_color, linewidth=2)
    ax.add_patch(box)
    if title:
        # Title bar
        title_box = FancyBboxPatch((x, y+h-0.6), w, 0.6, boxstyle="round,pad=0.1",
                                    facecolor=border_color, edgecolor=border_color, linewidth=0)
        ax.add_patch(title_box)
        ax.text(x + w/2, y + h - 0.3, title, ha='center', va='center',
                fontsize=14, fontweight='bold', color=title_color)
        text_y = y + (h - 0.6) / 2
    else:
        text_y = y + h / 2

    for i, line in enumerate(text_lines):
        offset = (len(text_lines) - 1) / 2 - i
        ax.text(x + w/2, text_y + offset * 0.35, line, ha='center', va='center',
                fontsize=12, color=DARK)

def draw_arrow(x1, y1, x2, y2, color=ARROW_COLOR):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                             arrowstyle='->', mutation_scale=20,
                             color=color, linewidth=2.5)
    ax.add_patch(arrow)

# ══════════════════════════════════════════════
# SECTION 1: 사용자 파이프라인 (상단)
# ══════════════════════════════════════════════
ax.text(7, 8.6, 'ToonStyle AI — 인공지능 기술 활용 방안', ha='center', va='center',
        fontsize=22, fontweight='bold', color=DARK)

# 구분선
ax.plot([0.5, 13.5], [8.25, 8.25], color='#E2E8F0', linewidth=1)

# 섹션 제목
ax.text(0.8, 7.85, '■ 사용자 변환 파이프라인', fontsize=15, fontweight='bold', color=PRIMARY)

# 상단 박스 레이아웃: 균일한 간격, 균형 잡힌 폭
# Box1(2.5) + gap(0.7) + Box2(3.0) + gap(0.7) + Box3(3.0) + gap(0.7) + Box4(2.2) = 12.8
# starts at 0.6, ends at 13.4

# ── 사용자 입력 ──
draw_box(0.6, 5.8, 2.5, 1.8, LIGHT_GRAY, GRAY,
         ['사진 업로드', '작가 선택', '파라미터 조절'],
         title='사용자 입력')

# ── Arrow → Pass 1 ──
draw_arrow(3.25, 6.7, 3.95, 6.7, PRIMARY)

# ── Pass 1 ──
draw_box(4.0, 5.8, 3.0, 1.8, PRIMARY_L, PRIMARY,
         ['SDXL + LoRA (작가별)', '+ ControlNet (Canny, 선택)'],
         title='Pass 1: 화풍 변환')

# ── Arrow → Pass 2 ──
draw_arrow(7.15, 6.7, 7.85, 6.7, SECONDARY)

# ── Pass 2 ──
draw_box(7.9, 5.8, 3.0, 1.8, SECONDARY_L, SECONDARY,
         ['IP-Adapter (원본 참조)', '정체성 복원 + 스타일 유지'],
         title='Pass 2: 얼굴 복원')

# ── Arrow → 출력 ──
draw_arrow(11.05, 6.7, 11.75, 6.7, ACCENT)

# ── 출력 ──
draw_box(11.8, 5.8, 1.8, 1.8, ACCENT_L, ACCENT,
         ['변환 이미지', '다운로드', '갤러리 저장'],
         title='출력')

# ── 변환 시간 표시 ──
ax.text(7, 5.35, '변환 속도: ~4초/장 (1024px, 2-pass, GPU fp16)', ha='center', va='center',
        fontsize=13, color=GRAY, style='italic')

# ══════════════════════════════════════════════
# SECTION 2: 모델 학습 파이프라인 (하단)
# ══════════════════════════════════════════════
ax.plot([0.5, 13.5], [4.8, 4.8], color='#E2E8F0', linewidth=1)
ax.text(0.8, 4.4, '■ 모델 학습 파이프라인', fontsize=15, fontweight='bold', color=ACCENT)

# ── 원화 ──
draw_box(0.5, 2.5, 2.5, 1.6, LIGHT_GRAY, GRAY,
         ['작가 원화', '50~100장/작가'],
         title='IP 데이터')

# ── Arrow ──
draw_arrow(3.15, 3.3, 3.85, 3.3, ARROW_COLOR)

# ── 전처리 ──
draw_box(3.9, 2.5, 2.8, 1.6, PRIMARY_L, PRIMARY,
         ['이미지 선별/정제', 'BLIP-2 자동 캡셔닝'],
         title='자동 전처리')

# ── Arrow ──
draw_arrow(6.85, 3.3, 7.55, 3.3, ARROW_COLOR)

# ── 학습 ──
draw_box(7.6, 2.5, 2.8, 1.6, SECONDARY_L, SECONDARY,
         ['dim=32, alpha=16', '~40분/작가'],
         title='SDXL LoRA 학습')

# ── Arrow ──
draw_arrow(10.55, 3.3, 11.25, 3.3, ARROW_COLOR)

# ── 모델 ──
draw_box(11.3, 2.5, 2.4, 1.6, ACCENT_L, ACCENT,
         ['작가 화풍 모델', '(.safetensors)', '프리셋 등록'],
         title='산출물')

# ── 하단 범례 ──
ax.plot([0.5, 13.5], [2.0, 2.0], color='#E2E8F0', linewidth=1)

legend_items = [
    (PRIMARY, '자체 개발 기술'),
    (SECONDARY, '오픈소스 연동'),
    (ACCENT, '결과물/산출물'),
    (GRAY, '입력/데이터'),
]
for i, (color, label) in enumerate(legend_items):
    x = 2.0 + i * 3
    rect = FancyBboxPatch((x, 1.25), 0.5, 0.35, boxstyle="round,pad=0.05",
                           facecolor=color, edgecolor=color, linewidth=0)
    ax.add_patch(rect)
    ax.text(x + 0.65, 1.42, label, fontsize=11, color=DARK, va='center')

ax.text(7, 0.7, '※ 외부 엔진(SDXL/ControlNet/IP-Adapter)은 오픈소스 활용, 2-pass 파이프라인·프리셋·학습 자동화는 자체 개발',
        ha='center', va='center', fontsize=10.5, color=GRAY, style='italic')

plt.tight_layout(pad=0.5)
out = '/home/ppak/clawd/kocca-proposal/track-a/4-2_ai_pipeline_diagram.png'
fig.savefig(out, dpi=200, bbox_inches='tight', facecolor=BG)
plt.close()
print(f'✅ 저장: {out}')
