#!/usr/bin/env python3
"""
Merge problem statements from logs/issue_gen/<repo>/*.json into a HF JSONL file.

Example:
  python scripts/add_issues_to_hf.py \
    --in-jsonl exports/Instagram__MonkeyType.70c3acf6.hf.jsonl \
    --issues-dir logs/issue_gen/MonkeyType \
    --out-jsonl exports/Instagram__MonkeyType.70c3acf6.hf.with_issues.jsonl \
    --prefer-model openai/gpt-4o-mini \
    --out-parquet exports/Instagram__MonkeyType.70c3acf6.hf.with_issues.parquet
"""

import argparse, json, os, glob, sys
from pathlib import Path

def choose_statement(meta: dict, prefer_model: str | None) -> str | None:
    """
    Pick the best problem statement from the issue file's `responses` dict.
    Preference: `prefer_model` if available, else first non-empty list in sorted model order.
    """
    responses = meta.get("responses", {})
    if not isinstance(responses, dict) or not responses:
        return None

    if prefer_model and prefer_model in responses and responses[prefer_model]:
        return (responses[prefer_model][0] or "").strip() or None

    # Fallback: deterministic order by model name
    for model in sorted(responses.keys()):
        lst = responses.get(model) or []
        if lst and lst[0]:
            cand = (lst[0] or "").strip()
            if cand:
                return cand
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-jsonl", required=True, help="Input HF JSONL produced by export step")
    ap.add_argument("--issues-dir", required=True, help="Directory with per-instance issue JSON files")
    ap.add_argument("--out-jsonl", required=True, help="Output JSONL with problem_statement merged in")
    ap.add_argument("--prefer-model", default=None, help="Model name to prefer when multiple responses exist")
    ap.add_argument("--out-parquet", default=None, help="Also write a Parquet copy (requires pandas/pyarrow)")
    args = ap.parse_args()

    in_path = Path(args.in_jsonl)
    issues_dir = Path(args.issues_dir)
    out_path = Path(args.out_jsonl)

    if not in_path.exists():
        print(f"[err] Input JSONL not found: {in_path}", file=sys.stderr)
        sys.exit(1)
    if not issues_dir.exists():
        print(f"[err] Issues dir not found: {issues_dir}", file=sys.stderr)
        sys.exit(1)

    # Load issues: {instance_id -> problem_statement}
    issues: dict[str, str] = {}
    issue_files = sorted(glob.glob(str(issues_dir / "*.json")))
    for p in issue_files:
        iid = Path(p).stem  # filename is <instance_id>.json
        try:
            meta = json.loads(Path(p).read_text())
        except Exception as e:
            print(f"[warn] Skipping unreadable issue file {p}: {e}", file=sys.stderr)
            continue
        stmt = choose_statement(meta, args.prefer_model)
        if stmt:
            issues[iid] = stmt

    if not issues:
        print("[warn] No problem statements found in issues directory; output will match input.", file=sys.stderr)

    # Merge into HF JSONL
    updated, total = 0, 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with in_path.open() as fin, out_path.open("w") as fout:
        for line in fin:
            total += 1
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception as e:
                print(f"[warn] Skipping bad JSONL line {total}: {e}", file=sys.stderr)
                continue
            iid = row.get("instance_id")
            if iid in issues:
                row["problem_statement"] = issues[iid]
                updated += 1
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[ok] wrote {out_path}  (updated {updated}/{total})")

    # Optional Parquet
    if args.out_parquet:
        try:
            import pandas as pd
        except Exception:
            print("[warn] pandas not installed; skipping Parquet export.", file=sys.stderr)
            return
        rows = [json.loads(l) for l in out_path.read_text().splitlines() if l.strip()]
        df = pd.DataFrame(rows)
        outpq = Path(args.out_parquet)
        outpq.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.to_parquet(outpq, index=False)
            print(f"[ok] wrote {outpq}")
        except Exception as e:
            print(f"[warn] failed writing Parquet: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
