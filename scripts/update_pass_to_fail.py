#!/usr/bin/env python3
import argparse, json, os, re, shlex, subprocess, sys, tempfile
from pathlib import Path

def run(cmd: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    print(f"[run] {cmd}  (cwd={cwd})")
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, shell=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env
    )

def assert_ok(cp: subprocess.CompletedProcess, ctx: str):
    if cp.returncode != 0:
        print(cp.stdout)
        raise SystemExit(f"[err] {ctx} (exit {cp.returncode})")

def clone_repo(owner_repo: str, commit: str, dest: Path):
    url = f"https://github.com/{owner_repo}.git"
    cp = run(f"git clone --depth 1 --filter=blob:none {shlex.quote(url)} {shlex.quote(str(dest))}")
    assert_ok(cp, f"git clone failed for {owner_repo}")
    cp = run(f"git checkout {shlex.quote(commit)}", cwd=dest)
    assert_ok(cp, f"git checkout {commit} failed")

def collect_nodeids(env_name: str, repo_dir: Path) -> list[str]:
    cp = run(f'conda run -n {shlex.quote(env_name)} pytest --collect-only -q', cwd=repo_dir)
    assert_ok(cp, "pytest --collect-only failed")
    nodeids = []
    for line in cp.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith(("<", "warning", "ERROR", "collected ")):
            continue
        # Looks like: tests/test_x.py::TestFoo::test_bar
        nodeids.append(line)
    return nodeids

STATUS_RE = re.compile(r"^(.+?::.+?)\s+(PASSED|FAILED|SKIPPED|XFAILED|XPASS|ERROR)\b")

def run_pytest_status(env_name: str, repo_dir: Path, extra: str = "") -> dict[str, str]:
    """
    Return {nodeid: STATUS}, using verbose output so we can parse per-test results.
    """
    cmd = f'conda run -n {shlex.quote(env_name)} pytest -vv -rA {extra}'
    cp = run(cmd, cwd=repo_dir)
    # Don't assert here; we want to parse even if failures occur
    results: dict[str, str] = {}
    for line in cp.stdout.splitlines():
        m = STATUS_RE.match(line.strip())
        if m:
            nodeid, status = m.group(1), m.group(2)
            results[nodeid] = status
    return results

def compute_pass_set(all_nodes: list[str], statuses: dict[str, str]) -> set[str]:
    """
    Consider PASSED as pass set. Exclude FAILED, ERROR, SKIPPED, XPASS/XFAILED from pass set.
    """
    passed = {n for n, s in statuses.items() if s == "PASSED"}
    # Any nodes not seen in statuses (rare) treat as not-passed
    return passed & set(all_nodes)

def apply_patch(repo_dir: Path, patch_text: str):
    patch_file = repo_dir / ".tmp.patch"
    patch_file.write_text(patch_text)
    cp = run(f"git apply -p1 --reject --whitespace=nowarn {patch_file.name}", cwd=repo_dir)
    assert_ok(cp, "git apply failed")

def reset_repo(repo_dir: Path, commit: str):
    run("git reset --hard", cwd=repo_dir)
    run("git clean -fd", cwd=repo_dir)
    run(f"git checkout {shlex.quote(commit)}", cwd=repo_dir)

def main():
    ap = argparse.ArgumentParser(description="Fill PASS_TO_FAIL for each instance in an HF JSONL.")
    ap.add_argument("--hf-in", required=True, help="Input HF JSONL (with patches)")
    ap.add_argument("--hf-out", required=True, help="Output HF JSONL with PASS_TO_FAIL filled")
    ap.add_argument("--repo", required=True, help="owner/repo (e.g., Instagram/MonkeyType)")
    ap.add_argument("--base-commit", required=True, help="Commit hash to use as clean baseline")
    ap.add_argument("--env", required=True, help="Conda env name to run tests in (e.g., testbed-run)")
    ap.add_argument("--pytest-extra", default="", help="Extra pytest args if needed")
    args = ap.parse_args()

    in_path = Path(args.hf_in)
    out_path = Path(args.hf_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(l) for l in in_path.read_text().splitlines() if l.strip()]
    if not rows:
        raise SystemExit("[err] No rows in input JSONL")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        repo_dir = td / "repo"
        clone_repo(args.repo, args.base_commit, repo_dir)

        # Baseline: collect all nodeids & pass set on clean repo
        all_nodes = collect_nodeids(args.env, repo_dir)
        if not all_nodes:
            raise SystemExit("[err] No tests collected; check your env and repo")
        baseline_status = run_pytest_status(args.env, repo_dir, args.pytest_extra)
        baseline_pass = compute_pass_set(all_nodes, baseline_status)
        print(f"[info] baseline: collected={len(all_nodes)} passed={len(baseline_pass)}")

        updated = 0
        for row in rows:
            patch = row.get("patch")
            iid = row.get("instance_id")
            if not patch:
                print(f"[warn] {iid}: missing patch; skipping")
                continue

            # Reset to clean baseline each time
            reset_repo(repo_dir, args.base_commit)
            try:
                apply_patch(repo_dir, patch)
            except SystemExit as e:
                print(f"[warn] {iid}: patch failed ({e}); skipping")
                continue

            after_status = run_pytest_status(args.env, repo_dir, args.pytest_extra)
            after_fail = {n for n, s in after_status.items() if s in {"FAILED", "ERROR"}}
            pass_to_fail = sorted(baseline_pass & after_fail)

            row["PASS_TO_FAIL"] = pass_to_fail
            updated += 1
            print(f"[ok] {iid}: PASS_TO_FAIL={len(pass_to_fail)}")

        out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        print(f"[ok] wrote {out_path}  (updated {updated}/{len(rows)})")

if __name__ == "__main__":
    main()
