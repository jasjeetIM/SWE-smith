#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./triage_patches.sh /path/to/patches.json [pytest-args...]
#
# cd ~/swe-smith/MonkeyType-test
# JSON="../logs/bug_gen/${REPO_KEY}_all_patches_n10.json"
# ../scripts/triage_patches.sh "$JSON" -q
#
# Requires: jq, git, pytest

PATCHES_JSON="${1:-}"
shift || true
PYTEST_ARGS=("$@")

if [[ -z "${PATCHES_JSON}" ]]; then
  echo "ERROR: provide path to patches JSON as first arg." >&2
  exit 1
fi
if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq not found. Install: conda install -c conda-forge jq" >&2
  exit 1
fi

# Must be inside a git repo
git rev-parse --is-inside-work-tree >/dev/null

# Confirm we’re clean to start
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: repo has uncommitted changes. Commit/stash them first." >&2
  exit 1
fi

N=$(jq 'length' "$PATCHES_JSON")
echo "Found $N patches in $PATCHES_JSON"

fail_list=()
pass_list=()
skip_list=()

for ((i=0; i<N; i++)); do
  echo "== Patch #$i =="
  git reset --hard >/dev/null
  git clean -fd >/dev/null

  jq -r ".[$i].patch" "$PATCHES_JSON" > /tmp/bug.diff

  if git apply --check /tmp/bug.diff 2>/dev/null; then
    git apply /tmp/bug.diff

    if pytest "${PYTEST_ARGS[@]}"; then
      echo "PATCH $i: tests PASS"
      pass_list+=("$i")
    else
      echo "PATCH $i: tests FAIL"
      fail_list+=("$i")
    fi
  else
    echo "PATCH $i: does not apply (skipping)"
    skip_list+=("$i")
  fi
  echo
done

# Restore repo to clean state
git reset --hard >/dev/null
git clean -fd >/dev/null

echo "===== SUMMARY ====="
echo "Failing patches: ${fail_list[*]:-none}"
echo "Passing patches: ${pass_list[*]:-none}"
echo "Non-applicable : ${skip_list[*]:-none}"

# Optional: write failing indices to a file
printf "%s\n" "${fail_list[@]:-}" > failing_patches.txt
echo "Wrote failing indices to ./failing_patches.txt"
