#!/bin/bash
# 카카오톡 대화 내보내기 자동화
# 사용법: ./katok-export.sh "채팅방이름"

CHATROOM="${1:-AI바우처}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="${CHATROOM}_${TIMESTAMP}.txt"

# 경로 설정
WIN_PATH="C:\\users\\ppak\\Documents\\${FILENAME}"
LINUX_PATH="/home/ppak/.wine/drive_c/users/ppak/Documents/${FILENAME}"
OUTPUT_DIR="/home/ppak/clawd/katok-analysis"

log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

log "=== 카카오톡 대화 내보내기 ==="
log "채팅방: $CHATROOM"

# 창 활성화 함수 (최소화된 창도 복원)
activate_window() {
    local win_id=$1
    # wmctrl로 최소화 해제 + 활성화
    wmctrl -i -a "$win_id" 2>/dev/null || {
        # wmctrl 실패시 xdotool fallback
        xdotool windowmap "$win_id" 2>/dev/null
        xdotool windowraise "$win_id" 2>/dev/null
        xdotool windowactivate --sync "$win_id" 2>/dev/null
    }
}

# 1. 카카오톡 메인창 찾기
MAIN_WIN=$(xdotool search --name "^카카오톡$" 2>/dev/null | head -1)
if [ -z "$MAIN_WIN" ]; then
    log "❌ 카카오톡 메인창 없음"
    exit 1
fi

# 2. 채팅방 열기
log "채팅방 검색..."
activate_window $MAIN_WIN
sleep 0.8
xdotool key ctrl+f
sleep 0.5
xdotool type --delay 50 "$CHATROOM"
sleep 0.8
xdotool key Return
sleep 1.5

# 3. 채팅방 창 찾기
CHAT_WIN=$(xdotool search --name "$CHATROOM" 2>/dev/null | head -1)
if [ -z "$CHAT_WIN" ]; then
    log "❌ 채팅방 없음: $CHATROOM"
    exit 1
fi

# 4. 대화 내보내기 (Ctrl+S)
log "대화 내보내기..."
activate_window $CHAT_WIN
sleep 0.8
xdotool key ctrl+s
sleep 1.5

# 5. 저장 대화상자 처리
SAVE_WIN=$(xdotool search --name "다른 이름으로 저장" 2>/dev/null | head -1)
if [ -z "$SAVE_WIN" ]; then
    log "❌ 저장 대화상자 없음"
    exit 1
fi

log "파일명 입력: $WIN_PATH"
activate_window $SAVE_WIN
sleep 0.5

# 파일명 필드 선택 및 입력
xdotool key alt+n
sleep 0.3
xdotool key ctrl+a
sleep 0.2
xdotool type --delay 15 "$WIN_PATH"
sleep 0.5

# 저장
xdotool key Return
sleep 2

# 6. 결과 확인
if [ -f "$LINUX_PATH" ]; then
    log "✅ 저장 성공!"
    mkdir -p "$OUTPUT_DIR"
    mv "$LINUX_PATH" "$OUTPUT_DIR/"
    FINAL="$OUTPUT_DIR/$FILENAME"
    
    LINES=$(wc -l < "$FINAL")
    log "📄 $LINES 줄 저장됨"
    echo "$FINAL"
    exit 0
else
    # 저장 실패 시 ESC로 대화상자 닫기
    xdotool key Escape
    log "❌ 저장 실패"
    exit 1
fi
