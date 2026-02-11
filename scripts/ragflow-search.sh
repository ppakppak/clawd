#!/bin/bash
# RAGFlow 검색 스크립트
# 사용법: ./ragflow-search.sh "검색 쿼리"

set -e

CONFIG_FILE="$HOME/clawd/.credentials/ragflow.env"
RAGFLOW_URL="http://localhost:9385"
DATASET_ID="eca02df2075811f1b4260b2d9b7e8ea5"

if [[ -z "$1" ]]; then
    echo "사용법: $0 \"검색 쿼리\""
    exit 1
fi

QUERY="$1"
TOP_K="${2:-5}"  # 기본 5개 결과

source "$CONFIG_FILE"

if [[ -z "$RAGFLOW_API_KEY" ]]; then
    echo "❌ RAGFLOW_API_KEY가 설정되지 않았습니다."
    exit 1
fi

# 검색 실행
response=$(curl -s -X POST \
    "${RAGFLOW_URL}/api/v1/retrieval" \
    -H "Authorization: Bearer ${RAGFLOW_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"question\": \"$QUERY\",
        \"dataset_ids\": [\"$DATASET_ID\"],
        \"top_k\": $TOP_K
    }")

code=$(echo "$response" | jq -r '.code // 999')

if [[ "$code" == "0" ]]; then
    # 결과 파싱 및 출력
    echo "$response" | jq -r '
        .data.chunks[]? | 
        "---\n📄 \(.document_name // "Unknown")\n📊 유사도: \(.similarity // "N/A")\n\n\(.content)\n"
    '
else
    echo "❌ 검색 실패: $(echo "$response" | jq -r '.message // "Unknown error"')"
    exit 1
fi
