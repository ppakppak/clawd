# TOOLS.md - Local Notes

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

---

## 🔧 원격 개발 환경

### SSH 호스트
| 이름 | IP | 사용자 | 용도 |
|------|-----|--------|------|
| Mac | 192.168.0.18 | ppak | 주식 실운영 |
| xavier | 192.168.0.29 | ppak | 승강기 엣지 추론 |
| samtel | 192.168.0.32 | intu | 관로점검 |

### Git 레포지토리
| 프로젝트 | 호스트 | 경로 | GitHub |
|---------|--------|------|--------|
| stock | Mac | ~/개발/stock | ppakppak/stock |
| elevator | xavier | ~/projects/elevator | ppakppak/elevator |
| pipe-inspector-electron | samtel | ~/projects/pipe-inspector-electron | ppakppak/pipe-inspect |
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

## 💬 카카오톡 공유 폴더
- 경로: `/home/ppak/Documents/katok_talk`
- 용도: 업무 관련 카톡 내용 저장 → 분석/정리 요청 시 참조
- 형식: 카톡 내보내기 txt 파일 또는 메모

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
- (미설정)

---

Add whatever helps you do your job. This is your cheat sheet.
