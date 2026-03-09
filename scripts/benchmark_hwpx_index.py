#!/usr/bin/env python3
"""
Benchmark: python-hwpx vs hwpx-cli (batch index)

- Select up to N .hwpx files from input directory
- Run python-hwpx paragraph chunk indexing (JSONL output)
- Run hwpx-cli batch index on same file set
- Print JSON summary
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import tempfile
import time
from pathlib import Path


def _select_files(input_dir: Path, max_files: int) -> list[Path]:
    files = sorted(input_dir.rglob("*.hwpx"))
    return files[:max_files]


def _python_hwpx_index(files: list[Path], out_jsonl: Path, max_chars: int) -> dict:
    from hwpx import HwpxDocument

    started = time.perf_counter()
    per_file_sec = []
    failures = []
    chunk_count = 0
    total_chars = 0

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with out_jsonl.open("w", encoding="utf-8") as f:
        for fp in files:
            t0 = time.perf_counter()
            try:
                doc = HwpxDocument.open(str(fp))
                paragraphs = getattr(doc, "paragraphs", [])
                for p_idx, p in enumerate(paragraphs):
                    text = (getattr(p, "text", "") or "").strip()
                    if not text:
                        continue
                    # paragraph 기준 + max_chars 제한
                    for i in range(0, len(text), max_chars):
                        chunk = text[i : i + max_chars]
                        chunk_count += 1
                        total_chars += len(chunk)
                        rec = {
                            "sourcePath": str(fp),
                            "chunkBy": "paragraph",
                            "paragraphIndex": p_idx,
                            "chunkIndexInParagraph": i // max_chars,
                            "text": chunk,
                        }
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception as e:  # noqa: BLE001
                failures.append({"file": str(fp), "error": f"{type(e).__name__}: {e}"})
            per_file_sec.append(time.perf_counter() - t0)

    elapsed = time.perf_counter() - started
    success = len(files) - len(failures)
    return {
        "tool": "python-hwpx",
        "elapsedSec": round(elapsed, 4),
        "scannedFiles": len(files),
        "indexedFiles": success,
        "failedFiles": len(failures),
        "chunkCount": chunk_count,
        "totalChars": total_chars,
        "filesPerSec": round(success / elapsed, 4) if elapsed > 0 else None,
        "medianFileSec": round(statistics.median(per_file_sec), 4) if per_file_sec else None,
        "p95FileSec": round(sorted(per_file_sec)[int(len(per_file_sec) * 0.95) - 1], 4)
        if per_file_sec
        else None,
        "output": str(out_jsonl),
        "failures": failures,
    }


def _prepare_input_dir(files: list[Path], dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for i, src in enumerate(files, start=1):
        dst = dest_dir / f"{i:03d}_{src.name}"
        if dst.exists() or dst.is_symlink():
            dst.unlink()
        # symlink를 따라가지 않는 구현체 대응을 위해 실제 파일 복사
        shutil.copy2(src, dst)


def _hwpx_cli_index(
    files: list[Path],
    cli_js: Path,
    node_bin: str,
    out_jsonl: Path,
    max_chars: int,
) -> dict:
    with tempfile.TemporaryDirectory(prefix="hwpx-bench-links-") as td:
        link_dir = Path(td)
        _prepare_input_dir(files, link_dir)

        cmd = [
            node_bin,
            str(cli_js),
            "batch",
            "index",
            str(link_dir),
            "--output",
            str(out_jsonl),
            "--chunk-by",
            "paragraph",
            "--max-chars",
            str(max_chars),
            "--json",
        ]

        t0 = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.perf_counter() - t0

        if proc.returncode != 0:
            return {
                "tool": "hwpx-cli",
                "elapsedSec": round(elapsed, 4),
                "error": proc.stderr.strip() or proc.stdout.strip() or f"exit {proc.returncode}",
            }

        raw = proc.stdout.strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}

        parsed["tool"] = "hwpx-cli"
        parsed["elapsedSec_wall"] = round(elapsed, 4)
        parsed["output"] = str(out_jsonl)
        return parsed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", type=Path, default=Path("/home/ppak/clawd/hwpx-analysis"))
    ap.add_argument("--max-files", type=int, default=100)
    ap.add_argument(
        "--cli-js",
        type=Path,
        default=Path("/tmp/hwpx-cli-eval/packages/hwpx-cli/dist/cli.js"),
    )
    ap.add_argument("--node-bin", default="node")
    ap.add_argument("--max-chars", type=int, default=1200)
    ap.add_argument("--out-dir", type=Path, default=Path("/tmp/hwpx-bench"))
    args = ap.parse_args()

    files = _select_files(args.input_dir, args.max_files)
    if not files:
        print(json.dumps({"error": f"No .hwpx files under {args.input_dir}"}, ensure_ascii=False))
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    py_out = args.out_dir / "python_hwpx_index.jsonl"
    cli_out = args.out_dir / "hwpx_cli_index.jsonl"

    py_result = _python_hwpx_index(files, py_out, args.max_chars)
    cli_result = _hwpx_cli_index(files, args.cli_js, args.node_bin, cli_out, args.max_chars)

    summary = {
        "inputDir": str(args.input_dir),
        "selectedFiles": len(files),
        "maxFiles": args.max_files,
        "python-hwpx": py_result,
        "hwpx-cli": cli_result,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
