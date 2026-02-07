# HEARTBEAT.md

## 📝 일일 대화 기록 동기화
- 시간: 21:00 ~ 23:59 (하루 1회)
- 조건: 오늘 memory/YYYY-MM-DD.md가 있으면
- 작업: clawd-logs에 복사 및 커밋
- 스크립트: `~/clawd/clawd-logs/scripts/sync-daily.sh`
- 상태 파일: `~/clawd/clawd-logs/.last-sync`

### 체크 방법
```bash
# 마지막 동기화 날짜 확인
cat ~/clawd/clawd-logs/.last-sync 2>/dev/null || echo "없음"

# 오늘이면 스킵, 아니면 동기화 실행
```
