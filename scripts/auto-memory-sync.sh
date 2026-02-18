#!/bin/bash
# 대화 기록 자동 동기화 (30분마다 실행)
# - memory/*.md → clawd-logs/daily/ 복사
# - 변경사항 있으면 git commit & push

set -e

LOGS_DIR="$HOME/clawd/clawd-logs"
MEMORY_DIR="$HOME/clawd/memory"
YEAR_MONTH=$(date +%Y-%m)
TODAY=$(date +%Y-%m-%d)
DAY=$(date +%d)
LOG_FILE="$HOME/clawd/logs/auto-memory-sync.log"

mkdir -p "$HOME/clawd/logs"
mkdir -p "$LOGS_DIR/daily/$YEAR_MONTH"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

cd "$LOGS_DIR" || exit 1

# 오늘 memory 파일 복사
if [ -f "$MEMORY_DIR/$TODAY.md" ]; then
    cp "$MEMORY_DIR/$TODAY.md" "daily/$YEAR_MONTH/$DAY.md"
fi

# 변경사항 있으면 커밋
if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -m "🔄 자동 동기화 $(date '+%H:%M')"
    git push origin main 2>/dev/null || true
    log "✅ 동기화 완료"
else
    log "ℹ️ 변경사항 없음"
fi

# 로그 파일 크기 관리 (100KB 초과시 truncate)
if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE") -gt 102400 ]; then
    tail -100 "$LOG_FILE" > "$LOG_FILE.tmp"
    mv "$LOG_FILE.tmp" "$LOG_FILE"
fi
