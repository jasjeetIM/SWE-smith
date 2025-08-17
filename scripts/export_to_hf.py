#!/usr/bin/env python3
"""
Convert SWE-smith patch JSON -> Hugging Face SWE-smith JSONL (optionally Parquet).

Example:

# Requires: pip install pandas pyarrow

#SET THESE VARIABLES:
PATCH_JSON="logs/bug_gen/Instagram__MonkeyType.70c3acf6_all_patches_n10.json"
OUT_JSONL="exports/Instagram__MonkeyType.70c3acf6.hf.jsonl"
OUT_PARQUET="exports/Instagram__MonkeyType.70c3acf6.hf.parquet"
REPO_KEY="Instagram__MonkeyType.70c3acf6"
COMMIT="70c3acf62950be5dfb28743c7a719bfdecebcd84"  # full hash preferred

python scripts/export_to_hf.py \
  --patch-json "$PATCH_JSON" \
  --out-jsonl "$OUT_JSONL" \
  --out-parquet "$OUT_PARQUET" \
  --repo-key "$REPO_KEY" \
  --base-commit "$COMMIT" \
  --image-name "$REPO_KEY"
 

 Verify: head -n 1 exports/Instagram__MonkeyType.70c3acf6.hf.jsonl | jq .
"""

from __future__ import annotations
import argparse, json, datetime, pathlib, sys

def key_to_repo(repo_key: str) -> str:
    # "Instagram__MonkeyType.70c3acf6" -> "Instagram/MonkeyType"
    left = repo_key.split(".", 1)[0]
    parts = left.split("__", 1)
    return f"{parts[0]}/{parts[1]}" if len(parts) == 2 else repo_key

def utc_now_iso() -> str:
    # "2025-08-17T12:34:56Z"
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"

def load_patches(path: pathlib.Path) -> list[dict]:
    with path.open() as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Input patch file must be a JSON array.")
    return data

def to_hf_rows(
    patches: list[dict],
    repo_key: str,
    base_commit: str | None,
    image_name: str | None,
    created_at: str | None,
) -> list[dict]:
    repo = key_to_repo(repo_key)
    commit_from_key = repo_key.rsplit(".", 1)[-1] if "." in repo_key else ""
    created = created_at or utc_now_iso()
    img = image_name or repo_key
    base = base_commit or commit_from_key

    rows: list[dict] = []
    for p in patches:
        patch_text = p.get("patch") or p.get("diff") or ""
        if not patch_text:
            # skip entries with no patch text
            continue
        problem_statement = (
            p.get("explanation")
            or p.get("strategy")
            or "A bug has been introduced; write a patch to make the tests pass."
        )
        row = {
            "instance_id": p.get("instance_id"),
            "repo": repo,
            "patch": patch_text,
            "FAIL_TO_PASS": [],      # you can fill with failing test names later if you collect them
            "PASS_TO_PASS": [],      # likewise for passing tests
            "created_at": created,
            "image_name": img,       # ties back to the environment/docker image name you built
            "base_commit": base,     # prefer full hash if you have it
            "problem_statement": problem_statement,
            # Optional: keep some provenance for inspection/debugging
            "metadata": {
                "strategy": p.get("strategy"),
                "cost": p.get("cost"),
                "repo_key": repo_key,
            },
        }
        rows.append(row)
    return rows

def write_jsonl(rows: list[dict], out_path: pathlib.Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as out:
        for r in rows:
            out.write(json.dumps(r) + "\n")

def write_parquet_if_requested(rows: list[dict], out_parquet: pathlib.Path | None) -> None:
    if not out_parquet:
        return
    try:
        import pandas as pd  # type: ignore
    except Exception as e:
        print(f"[warn] Skipping Parquet export (pandas missing): {e}", file=sys.stderr)
        return
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out_parquet, index=False)

def main():
    ap = argparse.ArgumentParser(description="Export SWE-smith patches to HF JSONL/Parquet.")
    ap.add_argument("--patch-json", "-i", required=True, help="Input patches JSON (from collect_patches).")
    ap.add_argument("--out-jsonl", "-o", required=True, help="Output HF JSONL path.")
    ap.add_argument("--repo-key", "-k", required=True, help="e.g. Instagram__MonkeyType.70c3acf6")
    ap.add_argument("--base-commit", "-c", default=None, help="Full base commit (preferred). Defaults to short from repo-key.")
    ap.add_argument("--image-name", default=None, help="Image/env name; defaults to repo-key.")
    ap.add_argument("--created-at", default=None, help="ISO timestamp (UTC) for created_at; defaults to now.")
    ap.add_argument("--out-parquet", default=None, help="Optional Parquet output path.")
    args = ap.parse_args()

    patch_path = pathlib.Path(args.patch_json)
    out_jsonl = pathlib.Path(args.out_jsonl)
    out_parquet = pathlib.Path(args.out_parquet) if args.out_parquet else None

    patches = load_patches(patch_path)
    rows = to_hf_rows(
        patches=patches,
        repo_key=args.repo_key,
        base_commit=args.base_commit,
        image_name=args.image_name,
        created_at=args.created_at,
    )
    write_jsonl(rows, out_jsonl)
    write_parquet_if_requested(rows, out_parquet)

    print(f"[ok] Wrote JSONL:   {out_jsonl}")
    if out_parquet:
        print(f"[ok] Wrote Parquet: {out_parquet}")

if __name__ == "__main__":
    main()
