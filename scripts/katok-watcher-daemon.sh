#!/bin/bash
# 카카오톡 파일 감시 데몬

WATCH_DIRS=(
    "/home/ppak/.wine/drive_c/users/ppak/Documents"
    "/home/ppak/Documents/katok_talk"
)
LOG_FILE="/home/ppak/clawd/logs/katok-watcher.log"
PROCESSED_FILE="/home/ppak/clawd/logs/katok-processed.txt"
OUTPUT_DIR="/home/ppak/clawd/katok-analysis"

mkdir -p "/home/ppak/clawd/logs" "$OUTPUT_DIR"
touch "$PROCESSED_FILE"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

extract_text() {
    local file="$1"
    local ext="${file##*.}"
    
    case "${ext,,}" in
        hwp) hwp5txt "$file" 2>/dev/null ;;
        pdf) pdftotext "$file" - 2>/dev/null ;;
        txt) cat "$file" 2>/dev/null ;;
        docx) unzip -p "$file" word/document.xml 2>/dev/null | sed 's/<[^>]*>//g' ;;
    esac
}

process_file() {
    local file="$1"
    local filename=$(basename "$file")
    local ext="${file##*.}"
    
    grep -Fxq "$file" "$PROCESSED_FILE" 2>/dev/null && return
    
    log "새 파일: $filename"
    
    local text=$(extract_text "$file")
    [ -z "$text" ] && return
    
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local analysis_file="$OUTPUT_DIR/${timestamp}_${filename%.*}.md"
    
    if [[ "${ext,,}" == "txt" ]] && head -5 "$file" 2>/dev/null | grep -q "카카오톡 대화"; then
        cat > "$analysis_file" << EOF
# 카카오톡 대화 분석

- **원본:** $filename
- **시간:** $(date '+%Y-%m-%d %H:%M:%S')
- **메시지:** $(grep -c '^\[' "$file") 개

## 미리보기

\`\`\`
$(head -100 "$file")
\`\`\`
EOF
    else
        cat > "$analysis_file" << EOF
# 문서: $filename

- **시간:** $(date '+%Y-%m-%d %H:%M:%S')
- **타입:** $ext

## 내용

$(echo "$text" | head -c 3000)
EOF
    fi
    
    log "분석 완료: $analysis_file"
    echo "$file" >> "$PROCESSED_FILE"
}

log "카톡 감시 시작: ${WATCH_DIRS[*]}"

inotifywait -m -r -e create -e moved_to --format '%w%f' "${WATCH_DIRS[@]}" 2>/dev/null | while read file; do
    [[ "$file" == *.tmp ]] && continue
    [[ "$file" == *.part ]] && continue
    [[ "$file" == .* ]] && continue
    
    sleep 2
    [ -f "$file" ] && process_file "$file"
done
