# HEARTBEAT.md

상태 파일: `~/clawd/memory/heartbeat-state.json`

---

## 💾 대화 자동 기록 (매 heartbeat)
**최우선 작업** - 다른 체크 전에 먼저 수행!

1. 이번 세션에서 나눈 대화 중 중요한 내용 확인:
   - 새 프로젝트/경로 정보 → `PROJECTS.yaml` 업데이트
   - 결정사항, 설정 변경 → `memory/YYYY-MM-DD.md`에 기록
   - 할일, 약속 → 기록 또는 cron 등록
2. 기록 안 된 중요 정보가 있으면 바로 저장
3. 사소한 잡담은 기록 안 해도 됨

**원칙:** 대화에서 나온 정보는 기억에 의존하지 말고 **파일에 써라**!

---

## ☀️ 모닝 브리핑
- 시간: 08:00 ~ 10:00 (하루 1회)
- 내용:
  - 🇺🇸 지난밤 미국 증시 (S&P500, 나스닥, 다우)
  - 오늘 캘린더 일정
  - 읽지 않은 중요 메일 요약
  - 날씨 (외출 예정 있으면)
- 조건: 주말엔 10:00 이후로

## 📬 메일 체크
- 간격: 3시간마다 (08:00 ~ 22:00)
- 내용: 새로운 읽지 않은 메일
- 알림 조건:
  - 국세청, 은행, 중요 발신자 → 즉시 알림
  - 일반 메일 → 3개 이상이면 요약

## 📅 일정 리마인더
- 조건: 2시간 이내 일정 있으면
- 내용: 일정명, 시간, 장소

## 📈 주식 백엔드 체크
- 시간: 장중 (09:00 ~ 15:30)
- 간격: heartbeat마다
- 명령: `ssh ppak@192.168.0.18 "curl -s http://127.0.0.1:8000/health"`
- 조건: 응답 없거나 에러면 알림 + 재시작 제안

## 📝 일일 대화 기록 동기화
- 시간: 21:00 ~ 23:59 (하루 1회)
- 조건: 오늘 memory/YYYY-MM-DD.md가 있으면
- 작업: clawd-logs에 복사 및 커밋
- 스크립트: `~/clawd/clawd-logs/scripts/sync-daily.sh`
- 상태 파일: `~/clawd/clawd-logs/.last-sync`

---

## 🔇 조용한 시간
- 23:00 ~ 08:00: 긴급한 것만 알림
- 긴급 = 국세청, 은행, 카드사, 시스템 장애

## 체크 명령어
```bash
# 미국 증시 (Yahoo Finance)
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/^GSPC" | python3 -c "import json,sys; d=json.load(sys.stdin); m=d['chart']['result'][0]['meta']; print(f\"S&P500: {m['regularMarketPrice']:,.2f} ({(m['regularMarketPrice']/m['previousClose']-1)*100:+.2f}%)\")"

# 캘린더
gcalcli agenda --nocolor

# 메일
/home/ppak/miniconda3/bin/python ~/clawd/scripts/gmail-check.py 10

# 날씨
curl -s "wttr.in/Daejeon?format=3"
```
