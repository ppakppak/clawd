#!/bin/bash
# 카카오톡 파일 감시 및 자동 분석
# 사용법: ./katok-watcher.sh [start|stop|status]

WATCH_DIRS=(
    "$HOME/.wine/drive_c/users/ppak/Documents"
    "$HOME/Documents/katok_talk"
)
LOG_FILE="$HOME/clawd/logs/katok-watcher.log"
PID_FILE="$HOME/clawd/logs/katok-watcher.pid"
PROCESSED_FILE="$HOME/clawd/logs/katok-processed.txt"
OUTPUT_DIR="$HOME/clawd/katok-analysis"

mkdir -p "$HOME/clawd/logs" "$OUTPUT_DIR"
touch "$PROCESSED_FILE"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

extract_text() {
    local file="$1"
    local ext="${file##*.}"
    local output=""
    
    case "${ext,,}" in
        hwp)
            output=$(hwp5txt "$file" 2>/dev/null)
            ;;
        pdf)
            output=$(pdftotext "$file" - 2>/dev/null)
            ;;
        txt)
            output=$(cat "$file" 2>/dev/null)
            ;;
        docx)
            # unzip + xml 파싱 (간단 버전)
            output=$(unzip -p "$file" word/document.xml 2>/dev/null | sed 's/<[^>]*>//g')
            ;;
        *)
            output=""
            ;;
    esac
    
    echo "$output"
}

is_kakaotalk_chat() {
    local file="$1"
    head -5 "$file" 2>/dev/null | grep -q "카카오톡 대화"
}

process_file() {
    local file="$1"
    local filename=$(basename "$file")
    local ext="${file##*.}"
    
    # 이미 처리된 파일 스킵
    if grep -Fxq "$file" "$PROCESSED_FILE" 2>/dev/null; then
        return
    fi
    
    log "새 파일 감지: $filename"
    
    # 텍스트 추출
    local text=$(extract_text "$file")
    
    if [ -z "$text" ]; then
        log "텍스트 추출 실패: $filename"
        return
    fi
    
    # 분석 결과 저장
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local analysis_file="$OUTPUT_DIR/${timestamp}_${filename%.*}.md"
    
    # 카톡 대화인지 확인
    if [[ "${ext,,}" == "txt" ]] && is_kakaotalk_chat "$file"; then
        cat > "$analysis_file" << EOF
# 카카오톡 대화 분석

- **원본 파일:** $filename
- **분석 시간:** $(date '+%Y-%m-%d %H:%M:%S')
- **파일 크기:** $(wc -c < "$file") bytes
- **메시지 수:** $(grep -c '^\[' "$file") 개

## 원본 내용 (처음 100줄)

\`\`\`
$(head -100 "$file")
\`\`\`

---
*전체 내용은 원본 파일 참조*
EOF
    else
        # 일반 문서
        local preview=$(echo "$text" | head -c 3000)
        cat > "$analysis_file" << EOF
# 문서 분석

- **파일:** $filename
- **분석 시간:** $(date '+%Y-%m-%d %H:%M:%S')
- **파일 타입:** $ext

## 내용 미리보기

$preview

---
*전체 내용은 원본 파일 참조*
EOF
    fi
    
    log "분석 완료: $analysis_file"
    
    # 처리 완료 기록
    echo "$file" >> "$PROCESSED_FILE"
    
    # 텔레그램 알림 (openclaw cron wake 활용)
    echo "📁 새 카톡 파일: $filename" > /tmp/katok-notify.txt
}

watch_directories() {
    log "카톡 파일 감시 시작"
    log "감시 대상: ${WATCH_DIRS[*]}"
    
    inotifywait -m -r -e create -e moved_to --format '%w%f' "${WATCH_DIRS[@]}" 2>/dev/null | while read file; do
        # 임시 파일 무시
        [[ "$file" == *.tmp ]] && continue
        [[ "$file" == *.part ]] && continue
        [[ "$file" == .* ]] && continue
        
        # 잠시 대기 (파일 쓰기 완료 대기)
        sleep 2
        
        # 파일이 존재하면 처리
        if [ -f "$file" ]; then
            process_file "$file"
        fi
    done
}

case "${1:-start}" in
    start)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "이미 실행 중 (PID: $(cat $PID_FILE))"
            exit 1
        fi
        
        echo "카톡 감시 시작..."
        watch_directories &
        echo $! > "$PID_FILE"
        echo "PID: $(cat $PID_FILE)"
        ;;
    stop)
        if [ -f "$PID_FILE" ]; then
            kill $(cat "$PID_FILE") 2>/dev/null
            rm -f "$PID_FILE"
            echo "중지됨"
        else
            echo "실행 중이 아님"
        fi
        ;;
    status)
        if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "실행 중 (PID: $(cat $PID_FILE))"
        else
            echo "중지됨"
        fi
        ;;
    test)
        # 기존 파일 처리 테스트
        for dir in "${WATCH_DIRS[@]}"; do
            find "$dir" -maxdepth 1 -type f \( -name "*.txt" -o -name "*.hwp" -o -name "*.pdf" \) -mtime -7 2>/dev/null | while read file; do
                process_file "$file"
            done
        done
        ;;
    *)
        echo "사용법: $0 [start|stop|status|test]"
        ;;
esac
