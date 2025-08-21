#!/usr/bin/env python3
import argparse, os, re, subprocess, sys, json
from pathlib import Path

def sh(cmd, env=None, cwd=None):
    print(f"\n$ {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, cwd=cwd, env=env)
    if res.returncode != 0:
        raise SystemExit(res.returncode)

def parse_repo(s: str) -> str:
    m = re.search(r"github\.com[:/]+([^/]+/[^/]+?)(?:\.git|/)?$", s)
    return m.group(1) if m else s

def short_sha(sha: str) -> str:
    return sha.strip()[:8]

def repo_key(owner_repo: str, commit: str) -> str:
    return f"{owner_repo.replace('/', '__')}.{short_sha(commit)}"

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="URL or owner/repo")
    ap.add_argument("--commit", required=True, help="40-char SHA (or short SHA)")
    ap.add_argument("--model", default=os.environ.get("MODEL", "openai/gpt-4o-mini"))
    ap.add_argument("--bug_config", default="configs/bug_gen/class_basic.yml")
    ap.add_argument("--issue_config", default="configs/issue_gen/ig_openai.yaml")
    ap.add_argument("--env_name", default=os.environ.get("TEST_ENV", "testbed"))
    ap.add_argument("--exports", default=os.environ.get("EXPORT_DIR", "exports"))
    ap.add_argument("--num_patches", "-n", type=int, default=10)
    ap.add_argument("--workers", "-w", type=int, default=2)
    ap.add_argument("--verify", type=int, default=0, help="Verify N instances via SWE-bench harness (Docker)")
    args = ap.parse_args()

    owner_repo = parse_repo(args.repo)
    commit = args.commit.strip()
    rkey = repo_key(owner_repo, commit)

    EXPORT_DIR = Path(args.exports); ensure_dir(EXPORT_DIR)
    PATCH_JSON   = Path(f"logs/bug_gen/{rkey}_all_patches_n{args.num_patches}.json")
    HF_JSONL     = EXPORT_DIR / f"{rkey}.hf.jsonl"
    HF_PQ        = EXPORT_DIR / f"{rkey}.hf.parquet"
    HF_PTF       = EXPORT_DIR / f"{rkey}.hf.ptf.jsonl"
    HF_PTF_PQ    = EXPORT_DIR / f"{rkey}.hf.ptf.parquet"
    HF_FINAL     = EXPORT_DIR / f"{rkey}.hf.final.jsonl"
    HF_FINAL_PQ  = EXPORT_DIR / f"{rkey}_final.parquet"
    SB_JSONL     = EXPORT_DIR / f"{rkey}.swebench.jsonl"
    ISSUE_DIR    = Path(f"logs/issue_gen/{owner_repo.split('/')[-1]}")

    print(f"Repo:        {owner_repo}")
    print(f"Commit:      {commit}")
    print(f"Repo Key:    {rkey}")
    print(f"Exports dir: {EXPORT_DIR}")
    if "OPENAI_API_KEY" not in os.environ:
        print("WARNING: OPENAI_API_KEY not set. Steps 4 and 7 may fail.", file=sys.stderr)

    # 3) Build repo env spec (try_install_py removes env after exporting)
    sh(f'python -m swesmith.build_repo.try_install_py "{owner_repo}" configs/install_repo.sh --commit "{commit}"')

    # 4) Bug generation
    sh(
        ' '.join([
            "python -m swesmith.bug_gen.llm.modify",
            f'"{rkey}"',
            f'-c "{args.bug_config}"',
            f'--model "{args.model}"',
            f"-n {args.num_patches}",
            f"-m 1",
            f"-w {args.workers}",
        ])
    )

    # 5) Export to HF (initial)
    sh(
        ' '.join([
            "python scripts/export_to_hf.py",
            f'--patch-json "{PATCH_JSON}"',
            f'--out-jsonl "{HF_JSONL}"',
            f'--out-parquet "{HF_PQ}"',
            f'--repo-key "{rkey}"',
            f'--base-commit "{commit}"',
            f'--image-name "{rkey}"',
        ])
    )

    # Recreate the conda env that try_install_py removed
    ENV_DIR = Path(f"logs/build_images/env/{rkey}")
    ENV_YML = ENV_DIR / f"sweenv_{rkey}.yml"
    if not ENV_YML.exists():
        raise SystemExit(f"Missing env spec: {ENV_YML}")
    sh(f"conda env remove -n {args.env_name} -y || true")
    sh(f'conda env create -n {args.env_name} -f "{ENV_YML}"')
    sh(f'conda run -n {args.env_name} python -c "import pytest; print(pytest.__version__)"')

    # 6) Compute PASS_TO_FAIL
    sh(
        ' '.join([
            "python scripts/update_pass_to_fail.py",
            f'--hf-in "{HF_JSONL}"',
            f'--hf-out "{HF_PTF}"',
            f'--repo "{owner_repo}"',
            f'--base-commit "{commit}"',
            f'--env "{args.env_name}"',
        ])
    )

    # 7) Problem statements
    sh(
        ' '.join([
            "python -m swesmith.issue_gen.generate",
            f'-d "{HF_PTF}"',
            f'-c "{args.issue_config}"',
            f"-w {args.workers}",
            "-r",
        ])
    )

    # 8) Merge problem statements
    sh(
        ' '.join([
            "python scripts/add_issues_to_hf.py",
            f'--in-jsonl "{HF_PTF}"',
            f'--issues-dir "{ISSUE_DIR}"',
            f'--out-jsonl "{HF_FINAL}"',
            '--prefer-model "openai/gpt-4o-mini"',
            f'--out-parquet "{HF_FINAL_PQ}"',
            "--verbose",
        ])
    )

    # 9) Export to SWE-bench format
    sh(
        ' '.join([
            "python scripts/export_to_swebench.py",
            f'--hf-jsonl "{HF_FINAL}"',
            f'--out-jsonl "{SB_JSONL}"',
        ])
    )

    # 10) Optional verify with SWE-bench harness (Docker)
    if args.verify > 0:
        ids = []
        with open(HF_FINAL, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                row = json.loads(line)
                ids.append(row["instance_id"])
                if len(ids) >= args.verify:
                    break
        if ids:
            inst = ",".join(ids)
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{Path.cwd()}:{env.get('PYTHONPATH','')}"
            env["SWE_SSL_INSECURE"] = "1"
        sh(
            ' '.join([
                "python -m swebench.harness.run_evaluation",
                f'--dataset_name "{SB_JSONL}"',
                "--predictions_path gold",
                f"--instance_ids {inst}",
                "--max_workers 1",
                "--cache_level env",
                "--force_rebuild 1",      
                f"--run_id verify-{rkey}",
            ]),
            env=env,
        )

    print("\n=== DONE ===")
    print(f"HF JSONL:        {HF_FINAL}")
    print(f"SWE-bench JSONL: {SB_JSONL}")

if __name__ == "__main__":
    main()
