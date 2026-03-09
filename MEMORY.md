# MEMORY.md - 정아의 장기기억

*마지막 업데이트: 2026-03-03*

---

## 📈 주식 자동매매 규칙 (SimpleDeepBuy)

> 2026-02-20에 대폭 개선. 상세 커밋은 `memory/2026-02-20.md` 참조.

### 핵심 매매 로직
- **매수 우선 정책**: 매수/매도 동시 충족 시 → 매도 스킵, 매수 실행
- **고정매도**: 평단가 × 1.02 (매도가 아닌 평단가 기준) — 2026-02-25 변경 (1.5%→2.5%→2.0%)
- **신고가매도**: 최소 수익률 +3.0% 이상일 때만 (PEAK_SELL_MIN_PCT)
- **매수 조건** (2026-02-27 변경):
  - 매도 기록 있으면 → 항상 매도가 기준 (수익/손실 구분 제거)
  - 매도 기록 없으면 → 평단가 기준
  - 매도가 기준: 현재가 ≤ 매도가 × 0.985 (-1.5%)
  - 평단가 기준: 현재가 ≤ 평단가 × 0.99 (-1%)
- **매도가 기준 매수 시**: 현재가-평단가 갭 ≤ 0.2% → 스킵 (평단 낮추는 효과 없음)
- **매도가 로드**: 마지막 매수 > 마지막 매도면 새 포지션 → 매도가 무시
- **직전 매수가 체크**: 현재가 < 직전 매수가일 때만 매수 (확실한 물타기만)
- **매수 수량**: 보유수량의 10~30% (**평단가 대비** 낙폭에 비례: -1%→10%, -2%→20%, -3%+→30%)
  - 2026-02-27: 수량 계산을 매도가→평단가 기준으로 분리 (과다매수 방지)
  - 수익 중 매수량 50% 축소 유지

### 낙폭매수 (DipBuyStrategy)
- **기준**: 이틀 연속 하락 (전일 하락 + 오늘 ≤-1% + 이틀 합산 ≤-2%)
- **대상**: 코스피200 상위 40종목
- **간격**: 10분마다 스캔
- 코스피 지수 의존 제거 → 상승장에서도 소외된 우량주 포착

### 최소 보유 종목 (SAMSUNG_CODES)
`["005930", "005935", "005380", "066570"]` — 삼성전자, 삼성전자우, 현대차, LG전자
→ 최소 1주 보유 유지

### 수익률 2% 미만 시 직전매도가 자동 리셋 (2026-03-05)
- fixed/virtual/trailing 전 모드 적용
- 서버 재시작 시에도 유지: `평단가×1.02 < 매도가`이면 로드 후 무효화
- 직전매수가: 매도 성공 시 자동 리셋, DB 로드 비활성화 (재시작 시 빈 상태)

### virtual 매도 모드 비활성화 (2026-03-05)
- `set_mode("virtual")` 거부, DB에 virtual이면 fixed로 강제변환
- 사용 가능 모드: trailing, fixed만

### 주문가능금액 < 총자산 10% 시 매수 차단 (2026-03-05)
- `buy_blocked_by_cash` 플래그, 매도는 영향 없음

### 낙폭매수/동반매수 기본값 OFF (2026-02-24)
- `_dip_buy_enabled` 기본값: **False** (simple_deep_buy.py)
- `InstitutionalBuyStrategyService.ENABLED` 기본값: **False** (institutional_buy_strategy_service.py)
- 서버 재기동해도 신규종목 매수 안 함. 수동 ON 필요.
- 3번 사고 후 근본 수정 (커밋 258e5e0)

### 수동 매수 시 직전매수가 자동 업데이트 (2026-02-24)
- `/buy` API에서 매수 성공 시 `last_buy_prices` 자동 업데이트
- 시장가 주문은 캐시된 현재가로 대체
- `POST /deep-buy/last-buy-price` 수동 세팅 API 추가

### 낙폭매수(DipBuy) 개별 ON/OFF (2026-02-24)
- API: `GET /dip-buy/status`, `POST /dip-buy/toggle?enabled=true/false`
- 킬스위치와 별도로 DipBuy만 제어 가능

### 매매 인터벌 UI 드롭다운 (2026-03-05)
- 기본값: `CHECK_INTERVAL = 0.5` (30초), UI에서 30초~10분 선택 가능
- API: `GET/POST /api/trading/deep-buy/interval`
- `SELL_COOLDOWN_SEC = CHECK_INTERVAL * 60` (동기화)
- 매수/매도 수량: `_calc_quantity()` → 항상 1주 고정

### 고정매도 직전매도가 필터 (2026-02-24)
- fixed 매도 조건(+1.5%) 충족해도 **현재가 > 직전매도가**일 때만 매도
- UI에 `직전매도 ⛔ 블록` 표시

### 신고가매도 직전매도 블록 (2026-02-25 수정, 커밋 cdc1865)
- **버그**: 직전매도 블록이 고정매도(`_check_fixed_sell`)에만 적용, 신고가매도(`_sell_one_share_on_peak`)는 우회 가능했음
- **수정**: 신고가매도 트리거를 `max(last_peak_sell_price, last_sell_price)`로 강화
- **수정**: `_sell_one_share_on_peak()` 내부에 `current_price <= last_sell_price` 가드 추가
- **수정**: 모든 매도 경로(고정/트레일링/신고가)에서 `trailing_state[code]["last_peak_sell_price"]` 동기화

### 이중매도 방지
- `_check_fixed_sell` → 매도 수량 리턴
- `_run_cycle`에서 `adjusted_qty = qty - sold_in_cycle`로 신고가매도에 전달

### 매도가(last_sell_prices) 관리
- 서버 시작 시: 보유 종목의 가장 최근 매도가를 무조건 로드 (매수/매도 순서 무관)
- `send_order()` 내부에서 매도 성공 시 자동 업데이트 (CLI/수동 매도 포함)
- UI에서도 portfolio_update WebSocket으로 동적 갱신

---

## 🛠️ 기술/스킬

### HWPX 편집 (2026-02-17)
한컴 문서를 프로그래밍으로 직접 편집하는 방법 터득!

**구조:**
- HWPX = ZIP 파일 (application/hwp+zip)
- `Contents/section0.xml` = 본문
- `BinData/` = 이미지
- `<hp:t>` 태그 = 텍스트 내용

**핵심 팁:**
- `<hp:linesegarray/>`는 **반드시 비워두기** (글자 겹침 방지)
- 한글이 자동으로 레이아웃 계산함

**워크플로우:**
```
압축 해제 → xmllint 포맷팅 → XML 수정 → 재압축
```

**작업 디렉토리:** `~/clawd/hwpx-analysis/`

---

## 👤 방기씨에 대해

- 주식 자동매매 시스템 운영 (삼성전자 등)
- 여러 개발 프로젝트: stock, elevator, pipe-inspector
- 삼텔랩스 관련 과제 진행 중 (관로 진단 AI - iPipeCheck)
- 대전 거주

---

## 📝 진행 중인 것들

### pipe-inspector (iPipeCheck) — K-water 영상판독 관상태 평가
- **용역명**: "영상판독 기반의 관상태 평가 기술 개발" (K-water 학술용역)
- **기간**: 2025.08 ~ 2027.12 (3년)
- **역할**: 인튜웍스 = 대표사 (AI/SW 개발 담당)
- **제안서**: `/home/ppak/nas2/Synol_Share/kwater/최종_정성적평가 제안서.pdf`
- **6대 핵심 과업**:
  1. 오토라벨링 솔루션 (속도 33fps, 정확도 95%+)
  2. AI 결함 탐지 — Instance Segmentation (mAP 85%+, IoU 70%+)
  3. 결함 크기/면적 산출 — 소실점+Depth Estimation (오차 25% 이내)
  4. 관내부 평면 도식화 — 곡면→평면 전개도 (오차 20% 이내)
  5. 관상태 평가 알고리즘 — 등급 자동 판정 (기술자 대비 85%+ 정합성)
  6. 진단 레포트 자동 생성 — PDF (진단시간 80% 단축)
- **현재 진행 상태 (2026-03-03 기준)**:
  - 어노테이션 웹 시스템 운영 중 (samtel, 721건 축적)
  - 오토라벨링/크기 산출/평면 도식화/등급 평가/레포트 = 미착수
  - AI 모델은 qwen3-vl 실험 수준, YOLO/Mask R-CNN 전환 필요
- **연차 로드맵**: 1차=데이터+AI모델 / 2차=도식화+면적+실증 / 3차=종합평가+레포트+최종실증

### 주식 시스템 미해결 이슈
- Gmail 토큰 만료 (2/16~) — 수동 재인증 필요
- launchd 재시작 불안정 (포트 바인딩 충돌)
- LG전자 재매수 검토 필요 (이중매도 버그로 0주 됨)
- 삼성전자우(005935) 미매도 조사 중 (2/25): 고정매도 트리거 초과인데 매도 안 됨 → `_check_fixed_sell()` 코드 디버깅 필요
- `com.ppak.stock-backend` launchd 미등록 — 현재 nohup으로만 기동
- Mac에 npm/node가 PATH에 없음 → `PATH="/Applications/Cursor.app/.../helpers:$PATH"` 또는 nvm 사용
- 백엔드 재시작 시 반드시 `venv/bin/python3` 사용 (시스템 python3는 3.9)

---

## 🖥️ 대화 주제 분리 운영 (2026-02-24~)

### Terminator 4분할 (주력)
- 실행: `terminator -l openclaw-split` 또는 `~/clawd/scripts/openclaw-terminator.sh`
- 세션: stock-window / dev-window / proposal-window / misc-window
- 설정: `~/.config/terminator/config`

### tmux 백업
- 세션: `claw-split` (`tmux attach -t claw-split`)
- F12로 mouse ON/OFF 토글, vi copy-mode
- 설정: `~/.tmux.conf`

### 모델 failover
- 전 agent 공통: GPT-5.3-codex (primary) → Claude Opus (fallback) → GPT-5.1 (fallback2)

### device token mismatch 해결법
- systemd 서비스에 `OPENCLAW_GATEWAY_TOKEN` 환경변수가 있으면 제거
- `daemon-reload` + `gateway restart`

### ToonStyle AI (7080 화백 스타일 변환)
- 프로젝트 경로: `~/projects/toon-style-transfer` (nex)
- **파이프라인 v2 (2026-02-27)**: txt2img + ControlNet(canny) + LoRA(fuse) + IP-Adapter-FaceID
  - 핵심 전환: img2img → txt2img (원본 사진 픽셀 잔류 제거 → LoRA 스타일 극대화)
  - `scripts/style_transfer.py` — ToonStyleEngine (프로덕션용)
  - `scripts/faceid_inference.py` — FaceID 실험용
  - InsightFace(buffalo_l) → 512d 얼굴 임베딩 → FaceID IP-Adapter
  - **최적 파라미터**: FaceID=0.40, ControlNet=0.65, guidance=8.0, steps=30
  - 웹서비스: `http://nex:8501` (`web/app.py`)
- **LoRA 버전 시스템**: v1(단순캡션), v2(ep6, 기본값), v2-strong(ep8)
  - v2가 잉크선/수채화/만화감 우세하나 사진마다 다름 → 셋 다 옵션으로 제공
  - 이정문 LoRA는 아직 v1만 (v2 재학습 필요)
- **LoRA 캡션 교훈**: 과도한 상세 캡션은 역효과 (스타일 자유도 제약). v1(단순) > v2(상세)
- **OOM 주의**: 추론 시 RAGFlow/ES 동시 구동하면 RAM 32GB 초과 가능 → 먼저 중지

### KOCCA 제안서 작업 (2026-02-27~)
- **DOCX 직접 수정으로 전환** (ODT → DOCX, python-docx 1.2.0)
- DOCX 경로: `/home/ppak/SynologyDrive/ykpark/wizdata/붙임2. 신청양식_26제작지원_진입형/2. 신청양식_26제작지원_진입형_실증(플랫폼설루션)/1. 사업수행(필수)/1-1.docx`
- 스크립트: `~/clawd/kocca-proposal/track-a/update_docx_v3.py`
- **DOCX 테이블 매핑**:
  - Table[25] = 2-1 과제 개요 (8행×3열)
  - Table[27] = 세부 제작계획 (5행×4열)
  - Table[28] = AI 기술 활용 계획 (2행×2열)
  - Table[29] = AI 기술 기능 상세 (1행×1열, nested table 삽입)
  - Table[30] = AI 기술 도식화 (1행×1열, matplotlib 이미지 삽입)
  - Table[31] = 상용화 계획 (4행×3열)
  - Table[33] = KPI/매출 계획 (2행×3열)
- 도식 이미지: `kocca-proposal/track-a/pipeline_diagram_v3.png`
- 초안: `kocca-proposal/track-a/사업신청서_초안.md` (v3)
- **진행상황 (2/27)**: v3 전체 반영 완료 — 5개 테이블 + nested table(4-1) + 도식 이미지(4-2)
- **마감: 2026-03-06 (금) 11:00**

---

## 💡 배운 교훈

- "나중에 기록해야지" ❌ → **지금 바로** ✅
- 텍스트 파일에 기록하지 않으면 다음 세션에서 까먹음
- 이중매도 같은 race condition은 수량 리턴값으로 후속 로직에 전달해야 함
- React StrictMode에서 cleanup 시 글로벌 상태(isConnecting 등) 반드시 리셋
- 매매 로직 수정 시 백엔드 + 프론트엔드(fetchBalance, WebSocket) 3곳 동시 반영 필수

---

*이 파일은 중요한 것만 정리. 상세 로그는 `memory/YYYY-MM-DD.md` 참조.*
