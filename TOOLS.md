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
| pipe-inspect | samtel | ~/projects/pipe-inspect | ppakppak/pipe-inspect |
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

## 🗂️ 기타

### TTS
- Preferred voice: (미설정)

### Cameras
- (미설정)

---

Add whatever helps you do your job. This is your cheat sheet.
