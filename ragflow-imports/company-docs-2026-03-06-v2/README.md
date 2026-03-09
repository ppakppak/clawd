# RAGFlow Import Summary

- Date: 2026-03-06
- Source root: `/home/ppak/Dropbox/Company`
- Target dataset: `company-docs-2026-03-06-v2`
- Dataset ID: `41327c2418e011f1b02bdb21e1fca700`

## Scope
- Included: `*.pdf`, `*.hwp` (recursive)
- HWP handling: converted to text via `hwp5txt` before upload

## Result
- Files discovered: 442 (PDF 353 + HWP 89)
- Uploaded: 435
- Convert failed (HWP): 3
- Upload failed (PDF parse/open error): 4

## Artifacts
- `map.tsv`: `document_id <tab> original_relative_path <tab> uploaded_name`
- `failures.tsv`: failed files and reasons
- `doc_ids.txt`: uploaded document IDs
- `ingest.log`: full run log

## Note
One parsing failure was observed due embedding API quota (`429`), and many docs may remain in RUNNING until quota recovers.
