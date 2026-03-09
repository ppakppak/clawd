# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

---

## 🔧 원격 개발 환경

### SSH 호스트
| 이름 | IP | 사용자 | 용도 |
|------|-----|--------|------|
| Mac | 192.168.0.18 | ppak | 주식 실운영 (⚠️ venv: ~/개발/stock/venv/bin/python3, Python 3.10) |
| xavier | 192.168.0.29 | ppak | 승강기 엣지 추론 |
| samtel | 192.168.0.32 | intu | 관로점검 |
| wasvr | 100.72.127.29 (Tailscale) | lmj | 수자원기술 서버 |

### Git 레포지토리
| 프로젝트 | 호스트 | 경로 | GitHub |
|---------|--------|------|--------|
| stock | Mac | ~/개발/stock | ppakppak/stock |
| elevator | xavier | ~/projects/elevator | ppakppak/elevator |
| pipe-inspector-electron | samtel | ~/projects/pipe-inspector-electron | ppakppak/pipe-inspect |

### pipe-inspector 개발 원칙
- **반드시 staging에서 개발/테스트 → 검증 후 production 배포**
- Production (`pipe-inspector-electron`): 포트 5003/5004 — K-water 팀 실사용 중, 직접 수정 금지
- Staging (`pipe-inspector-staging`): 포트 5005/5006 — 개발/테스트 여기서
| clawd | nex | ~/clawd | ppakppak/clawd |
| clawd-logs | nex | ~/clawd/clawd-logs | ppakppak/clawd-logs |

---

## 📝 자동 커밋 규칙

**코드 수정 시 바로 커밋!**

수정 후 실행:
```bash
# Mac (stock)
ssh ppak@192.168.0.18 "cd ~/개발/stock && git add -A && git commit -m '변경내용' && git push"

# xavier (elevator)
ssh ppak@192.168.0.29 "cd ~/projects/elevator && git add -A && git commit -m '변경내용' && git push"

# samtel (pipe-inspect)
ssh intu@192.168.0.32 "cd ~/projects/pipe-inspect && git add -A && git commit -m '변경내용' && git push"
```

---

## 📱 Telegram
- Bot: iljo (@iljo_bot)
- Chat ID: 1786192505 (Young Key Park @ppakppak)

## 💬 카카오톡 자동 분석

### 폴더
- **Wine 카톡 받은 파일**: `~/.wine/drive_c/users/ppak/Documents/`
- **카톡 대화 내보내기**: `~/Documents/katok_talk/`
- **분석 결과**: `~/clawd/katok-analysis/`

### 자동 감시 서비스
```bash
# 상태 확인
systemctl --user status katok-watcher

# 로그 확인
tail -f ~/clawd/logs/katok-watcher.log

# 수동 분석 (최근 7일 파일)
~/clawd/scripts/katok-watcher.sh test
```

### 지원 파일
- HWP → hwp5txt
- PDF → pdftotext
- TXT (카톡 대화) → 파싱 + 메시지 수 카운트

---

## 📬 Google 연동

### Gmail
```bash
/home/ppak/miniconda3/bin/python ~/clawd/scripts/gmail-check.py [개수]
```
- Credentials: `~/clawd/.credentials/google-oauth.json`
- Token: `~/clawd/.credentials/gmail-token.pickle`

### Google Calendar
```bash
gcalcli agenda          # 다가오는 일정
gcalcli list            # 캘린더 목록
gcalcli calw            # 주간 뷰
```

---

## 🗂️ 기타

### TTS
- Preferred voice: (미설정)

### Cameras
- 승강기 네트워크 카메라: `192.168.0.72` (RTSP 554)
- 확인된 스트림 경로: `/stream1`, `/stream2`, `/h264/ch1/main/av_stream`, `/h264/ch1/sub/av_stream`
- 승강기 서비스 기본 소스(현재 적용): `rtsp://<id>:<password>@192.168.0.72:554/stream2`
- 운영 서비스(4채널):
  - `systemctl --user status elevator-ds-webcam.service`
  - `systemctl --user status elevator-ds-rtsp.service`
  - `systemctl --user status elevator-ds-video1.service`
  - `systemctl --user status elevator-ds-video2.service`
- 미리보기 서비스(포트):
  - `elevator-preview-webcam.service` → `:5000`
  - `elevator-preview-rtsp.service` → `:5001`
  - `elevator-preview-video1.service` → `:5002`
  - `elevator-preview-video2.service` → `:5003`
- 통합 대시보드: `elevator-dashboard.service` → `:7000`
  - URL: `http://192.168.0.29:7000`
  - API: `/api/events`, `/api/health`
- 참고: USB webcam(`/dev/video0`)은 단일 점유라 DeepStream(webcam 채널)과 preview 동시 사용 불가
  - 현재 운영: webcam은 preview(`:5000`) 우선, `elevator-ds-webcam.service`는 비활성

---

## 🧠 RAGFlow 장기 기억

### 접속
- **웹 UI**: http://localhost:9390
- **API**: http://localhost:9385
- **Dataset**: `clawd-memory` (ID: eca02df2075811f1b4260b2d9b7e8ea5)

### 스크립트
```bash
# 검색
~/clawd/scripts/ragflow-search.sh "검색어"

# 동기화 (새 파일 업로드 + 파싱)
~/clawd/scripts/ragflow-sync.sh

# 강제 전체 동기화
~/clawd/scripts/ragflow-sync.sh --force
```

### 자동 동기화
- Cron: 매일 22:00 자동 실행

### 인덱싱된 데이터
- `~/clawd/memory/*.md` - 일일 메모
- `~/clawd/clawd-logs/daily/*.md` - 대화 로그

---

Add whatever helps you do your job. This is your cheat sheet.
