# HEARTBEAT.md

상태 파일: `~/clawd/memory/heartbeat-state.json`

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
