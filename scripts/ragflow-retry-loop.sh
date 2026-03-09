#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="${HOME}/clawd/.credentials/ragflow.env"
RAGFLOW_URL="${RAGFLOW_URL:-http://localhost:9385}"
DATASET_ID="${1:-41327c2418e011f1b02bdb21e1fca700}"
SLEEP_SEC="${SLEEP_SEC:-90}"
RETRY_BATCH="${RETRY_BATCH:-20}"
MAX_LOOPS="${MAX_LOOPS:-480}"   # 480 * 90s ~= 12h
OUT_DIR="${HOME}/clawd/ragflow-imports/company-docs-2026-03-06-v2"
LOG_FILE="${OUT_DIR}/auto-retry.log"

mkdir -p "$OUT_DIR"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "[$(date '+%F %T')] missing config: $CONFIG_FILE" | tee -a "$LOG_FILE"
  exit 1
fi

# shellcheck disable=SC1090
source "$CONFIG_FILE"
if [[ -z "${RAGFLOW_API_KEY:-}" ]]; then
  echo "[$(date '+%F %T')] missing RAGFLOW_API_KEY" | tee -a "$LOG_FILE"
  exit 1
fi

fetch_docs_jsonl() {
  local out_file="$1"
  : > "$out_file"
  local page=1

  while true; do
    local resp count
    resp=$(curl -s -H "Authorization: Bearer ${RAGFLOW_API_KEY}" \
      "${RAGFLOW_URL}/api/v1/datasets/${DATASET_ID}/documents?page=${page}&page_size=100")

    count=$(echo "$resp" | jq -r '.data.docs | length // 0')
    if [[ "$count" -eq 0 ]]; then
      break
    fi

    echo "$resp" | jq -c '.data.docs[]' >> "$out_file"
    page=$((page + 1))
  done
}

retry_fail_batch() {
  local docs_jsonl="$1"
  local ids_file
  ids_file=$(mktemp)

  jq -r 'select(.run=="FAIL") | .id' "$docs_jsonl" | head -n "$RETRY_BATCH" > "$ids_file"
  local fail_batch_count
  fail_batch_count=$(wc -l < "$ids_file" | tr -d ' ')

  if [[ "$fail_batch_count" -eq 0 ]]; then
    rm -f "$ids_file"
    return 0
  fi

  local ids_json resp code msg
  ids_json=$(jq -R . < "$ids_file" | jq -s .)

  resp=$(curl -s -X POST "${RAGFLOW_URL}/api/v1/datasets/${DATASET_ID}/chunks" \
    -H "Authorization: Bearer ${RAGFLOW_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"document_ids\": ${ids_json}}")

  code=$(echo "$resp" | jq -r '.code // 999')
  msg=$(echo "$resp" | jq -r '.message // ""')

  if [[ "$code" == "0" ]]; then
    echo "retry_submitted=${fail_batch_count}" | tee -a "$LOG_FILE"
  else
    echo "retry_submit_failed count=${fail_batch_count} msg=${msg}" | tee -a "$LOG_FILE"
  fi

  rm -f "$ids_file"
}

for ((loop=1; loop<=MAX_LOOPS; loop++)); do
  docs_jsonl=$(mktemp)
  fetch_docs_jsonl "$docs_jsonl"

  total=$(wc -l < "$docs_jsonl" | tr -d ' ')
  done_cnt=$(jq -s '[.[] | select(.run=="DONE")] | length' "$docs_jsonl")
  running_cnt=$(jq -s '[.[] | select(.run=="RUNNING")] | length' "$docs_jsonl")
  fail_cnt=$(jq -s '[.[] | select(.run=="FAIL")] | length' "$docs_jsonl")
  unstart_cnt=$(jq -s '[.[] | select(.run=="UNSTART")] | length' "$docs_jsonl")

  echo "[$(date '+%F %T')] loop=${loop} total=${total} done=${done_cnt} running=${running_cnt} fail=${fail_cnt} unstart=${unstart_cnt}" | tee -a "$LOG_FILE"

  if [[ "$fail_cnt" -gt 0 ]]; then
    retry_fail_batch "$docs_jsonl"
  fi

  rm -f "$docs_jsonl"

  if [[ "$running_cnt" -eq 0 && "$fail_cnt" -eq 0 && "$unstart_cnt" -eq 0 ]]; then
    echo "[$(date '+%F %T')] completed: no RUNNING/FAIL/UNSTART docs left" | tee -a "$LOG_FILE"
    exit 0
  fi

  sleep "$SLEEP_SEC"
done

echo "[$(date '+%F %T')] max loops reached. exiting." | tee -a "$LOG_FILE"
exit 0
