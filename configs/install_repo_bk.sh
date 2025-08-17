#!/usr/bin/env bash
set -euo pipefail

# --- Portable Conda/Mamba loader ---
load_conda() {
  # If conda is already on PATH, try to source its conda.sh via conda info
  if command -v conda >/dev/null 2>&1; then
    if CONDA_BASE="$(conda info --base 2>/dev/null)"; then
      if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
        # shellcheck disable=SC1090
        . "$CONDA_BASE/etc/profile.d/conda.sh"
        return 0
      fi
    fi
  fi

  # Try common install prefixes
  for ROOT in \
    "$HOME/miniforge" "$HOME/mambaforge" "$HOME/miniconda3" \
    "/opt/miniforge" "/opt/mambaforge" "/opt/miniconda3" \
    "/usr/local/miniconda3" "/root/miniconda3"
  do
    if [ -f "$ROOT/etc/profile.d/conda.sh" ]; then
      # shellcheck disable=SC1090
      . "$ROOT/etc/profile.d/conda.sh"
      export PATH="$ROOT/bin:$PATH"
      return 0
    fi
  done

  echo "Error: Could not find a Conda installation (looked for conda.sh in common locations)." >&2
  exit 1
}
load_conda
# --- End portable loader ---

# Prefer mamba if present (faster solves), else conda
if command -v mamba >/dev/null 2>&1; then
  CREATE="mamba create -y -q"
else
  CREATE="conda create -y -q"
fi

ENV_NAME="testbed"

# Create env if it doesn't exist yet
if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  $CREATE -n "$ENV_NAME" python=3.10
fi

# Activate (requires conda.sh sourced above)
conda activate "$ENV_NAME"

# --- Your repo install steps go here ---
# (Keep these as-is if they were already working for your flow.)
pip install -e .
pip install -U pytest
