# scripts/export_to_swebench.py
import json, argparse, datetime
from pathlib import Path
from unidiff import PatchSet
import re

_HUNK_RE = re.compile(r'^@@\s+-([0-9]+)(?:,([0-9]+))?\s+\+([0-9]+)(?:,([0-9]+))?\s+@@')

def _swap_hunk_header(line: str) -> str:
    m = _HUNK_RE.match(line)
    if not m:
        return line
    a_start, a_len, b_start, b_len = m.groups()
    a_len = a_len or '1'
    b_len = b_len or '1'
    # swap A/B
    return f"@@ -{b_start},{b_len} +{a_start},{a_len} @@{line[m.end():]}"

def invert_unified_diff(patch_text: str) -> str:
    """
    Invert a unified diff: swap old/new file headers, swap hunk ranges, and flip
    +/- line prefixes. Safe for typical 'git diff' output (text files).
    """
    out = []
    for raw in patch_text.splitlines(keepends=False):
        line = raw

        # swap file headers
        if line.startswith('--- '):
            out.append('+++' + line[3:])
            continue
        if line.startswith('+++ '):
            out.append('---' + line[3:])
            continue

        # swap hunk header ranges
        if line.startswith('@@ '):
            out.append(_swap_hunk_header(line))
            continue

        # flip added/removed lines inside hunks
        if line.startswith('+') and not line.startswith('+++ '):
            out.append('-' + line[1:])
            continue
        if line.startswith('-') and not line.startswith('--- '):
            out.append('+' + line[1:])
            continue

        # leave everything else as-is (context, diff --git, index, etc.)
        out.append(line)

    return '\n'.join(out) + ('\n' if patch_text.endswith('\n') else '')

def row_to_swebench(hf_row):
    return {
        "instance_id": hf_row["instance_id"],              # keep yours
        "repo": hf_row["repo"],
        "issue_id": None,                                  # synthetic; leave None or generate
        "base_commit": hf_row["base_commit"],
        "problem_statement": hf_row.get("problem_statement"),
        "version": None,                                   # optional unless you have it
        "issue_url": None, "pr_url": None,                 # synthetic
        "patch": invert_unified_diff(hf_row["patch"]),     # GOLD fix
        "test_patch": "",                                # usually None for synthetic
        "created_at": hf_row.get("created_at") or datetime.datetime.utcnow().isoformat()+'Z',
        "FAIL_TO_PASS": hf_row.get("PASS_TO_FAIL", []),    # rename semantics
        "PASS_TO_PASS": hf_row.get("PASS_TO_PASS", []),    # already empty in your samples
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hf-jsonl", required=True)
    ap.add_argument("--out-jsonl", required=True)
    args = ap.parse_args()

    out = Path(args.out_jsonl)
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(args.hf_jsonl, "r", encoding="utf-8") as f_in, \
         open(out, "w", encoding="utf-8") as f_out:
        for line in f_in:
            if not line.strip(): continue
            row = json.loads(line)
            sb = row_to_swebench(row)
            f_out.write(json.dumps(sb, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    main()
