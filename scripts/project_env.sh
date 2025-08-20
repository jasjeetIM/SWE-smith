# --- conda helper (safe if sourced multiple times) ---
[ -f "$HOME/miniforge/etc/profile.d/conda.sh" ] && . "$HOME/miniforge/etc/profile.d/conda.sh"
export PATH="$HOME/miniforge/bin:$PATH"

# --- repo/commit you want as defaults ---
export REPO="Instagram/MonkeyType"
export COMMIT="70c3acf62950be5dfb28743c7a719bfdecebcd84"

# --- derived vars (computed every source) ---
export SHORT="${COMMIT:0:8}"
export REPO_KEY="${REPO//\//__}.${SHORT}"

# handy paths you keep using
export ENVYML="logs/build_images/env/${REPO_KEY}/sweenv_${REPO_KEY}.yml"
export CONFIG="configs/bug_gen/class_basic.yml"
export MODEL="openai/gpt-4o-mini"
export PATCH_JSON="logs/bug_gen/${REPO_KEY}_all_patches_n10.json"
export HF_JSONL="exports/${REPO_KEY}.hf.jsonl"
export HF_PARQ="exports/${REPO_KEY}.hf.parquet"
export HF_PTF="exports/${REPO_KEY}.hf.ptf.jsonl"
export HF_PTF_PS="exports/${REPO_KEY}.hf.final.jsonl"
export HF_PTF_PS_PQ="exports/${REPO_KEY}.hf.final.parquet"
export DATASET_JSON="logs/experiments/${REPO_KEY}.gather.json"
export ISSUE_DIR="logs/issue_gen/MonkeyType"
# optional helper to switch quickly
set_repo() {
  export REPO="$1"
  export COMMIT="$2"
  export SHORT="${COMMIT:0:8}"
  export REPO_KEY="${REPO//\//__}.${SHORT}"
}

# Steps 
# git config --global --unset-all url."https://github.com/".insteadof || true
# git config --global --add url."https://github.com/".insteadof git@github.com:
# git config --global --add url."https://github.com/".insteadof ssh://git@github.com/
# git config --global --add url."https://github.com/".insteadof git://github.com/

