#!/bin/bash
# RAGFlow 자동 동기화 스크립트
# 사용법: ./ragflow-sync.sh [--force]

set -e

# 설정
CONFIG_FILE="$HOME/clawd/.credentials/ragflow.env"
STATE_FILE="$HOME/clawd/memory/ragflow-sync-state.json"
RAGFLOW_URL="http://localhost:9385"  # API port
DATASET_ID="eca02df2075811f1b4260b2d9b7e8ea5"

# 동기화할 디렉토리들
SYNC_DIRS=(
    "$HOME/clawd/memory"
    "$HOME/clawd/clawd-logs/daily"
)

# 설정 파일 확인
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "❌ 설정 파일이 없습니다: $CONFIG_FILE"
    echo "다음 명령으로 생성하세요:"
    echo "  mkdir -p ~/.credentials"
    echo "  echo 'RAGFLOW_API_KEY=your-api-key-here' > $CONFIG_FILE"
    exit 1
fi

source "$CONFIG_FILE"

if [[ -z "$RAGFLOW_API_KEY" ]]; then
    echo "❌ RAGFLOW_API_KEY가 설정되지 않았습니다."
    exit 1
fi

# 상태 파일 초기화
if [[ ! -f "$STATE_FILE" ]]; then
    echo '{"lastSync": 0, "syncedFiles": {}}' > "$STATE_FILE"
fi

FORCE_SYNC=false
if [[ "$1" == "--force" ]]; then
    FORCE_SYNC=true
    echo "🔄 강제 동기화 모드"
fi

echo "📂 RAGFlow 동기화 시작..."
echo "   Dataset: $DATASET_ID"

uploaded=0
skipped=0

for dir in "${SYNC_DIRS[@]}"; do
    if [[ ! -d "$dir" ]]; then
        continue
    fi
    
    # .md 파일만 찾기
    find "$dir" -name "*.md" -type f | while read -r file; do
        filename=$(basename "$file")
        file_mtime=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file")
        
        # 이미 동기화된 파일인지 확인
        if [[ "$FORCE_SYNC" == "false" ]]; then
            synced_time=$(jq -r ".syncedFiles[\"$file\"] // 0" "$STATE_FILE")
            if [[ "$file_mtime" -le "$synced_time" ]]; then
                ((skipped++)) || true
                continue
            fi
        fi
        
        echo "📤 업로드: $filename"
        
        # 파일 업로드
        response=$(curl -s -X POST \
            "${RAGFLOW_URL}/api/v1/datasets/${DATASET_ID}/documents" \
            -H "Authorization: Bearer ${RAGFLOW_API_KEY}" \
            -H "Content-Type: multipart/form-data" \
            -F "file=@${file}")
        
        code=$(echo "$response" | jq -r '.code // 999')
        
        if [[ "$code" == "0" ]]; then
            # 문서 ID 추출
            doc_id=$(echo "$response" | jq -r '.data[0].id // empty')
            if [[ -n "$doc_id" ]]; then
                echo "   ✅ 업로드 성공 (ID: $doc_id)"
                echo "$doc_id" >> /tmp/ragflow_uploaded_ids.txt
            else
                echo "   ✅ 성공"
            fi
            # 상태 업데이트
            jq ".syncedFiles[\"$file\"] = $file_mtime" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
            ((uploaded++)) || true
        else
            echo "   ❌ 실패: $(echo "$response" | jq -r '.message // "Unknown error"')"
        fi
    done
done

# 업로드된 문서들 파싱
if [[ -f /tmp/ragflow_uploaded_ids.txt ]]; then
    doc_ids=$(cat /tmp/ragflow_uploaded_ids.txt | jq -R . | jq -s .)
    doc_count=$(echo "$doc_ids" | jq 'length')
    
    if [[ "$doc_count" -gt 0 ]]; then
        echo ""
        echo "🔄 파싱 시작 ($doc_count 문서)..."
        
        parse_response=$(curl -s -X POST \
            "${RAGFLOW_URL}/api/v1/datasets/${DATASET_ID}/chunks" \
            -H "Authorization: Bearer ${RAGFLOW_API_KEY}" \
            -H "Content-Type: application/json" \
            -d "{\"document_ids\": $doc_ids}")
        
        parse_code=$(echo "$parse_response" | jq -r '.code // 999')
        if [[ "$parse_code" == "0" ]]; then
            echo "   ✅ 파싱 요청 완료"
        else
            echo "   ❌ 파싱 실패: $(echo "$parse_response" | jq -r '.message // "Unknown error"')"
        fi
    fi
    
    rm -f /tmp/ragflow_uploaded_ids.txt
fi

# 마지막 동기화 시간 업데이트
jq ".lastSync = $(date +%s)" "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

echo ""
echo "✨ 동기화 완료!"
echo "   업로드: $uploaded 파일"
echo "   스킵: $skipped 파일"
