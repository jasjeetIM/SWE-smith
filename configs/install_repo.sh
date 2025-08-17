#!/bin/bash

# Try to find conda installation

# Ensure conda/mamba are available in non-interactive shells
if ! command -v conda >/dev/null 2>&1 && ! command -v mamba >/dev/null 2>&1; then
  # source conda if available
  if [ -f "$HOME/miniforge/etc/profile.d/conda.sh" ]; then
    . "$HOME/miniforge/etc/profile.d/conda.sh"
  elif [ -f "/opt/miniforge/etc/profile.d/conda.sh" ]; then
    . "/opt/miniforge/etc/profile.d/conda.sh"
  fi
  # hard add to PATH as a fallback
  export PATH="$HOME/miniforge/bin:$PATH"
  export CONDA_EXE="${CONDA_EXE:-$HOME/miniforge/bin/conda}"
  export MAMBA_EXE="${MAMBA_EXE:-$HOME/miniforge/bin/mamba}"
fi

if [ -f "/root/miniconda3/bin/activate" ]; then
    . /root/miniconda3/bin/activate
elif [ -f "/opt/miniconda3/bin/activate" ]; then
    . /opt/miniconda3/bin/activate
elif [ -f "$HOME/miniconda3/bin/activate" ]; then
    . $HOME/miniconda3/bin/activate
else
    echo "Error: Could not find conda installation"
    exit 1
fi
conda create -n testbed python=3.10 -yq
conda activate testbed
pip install -e .
pip install pytest
