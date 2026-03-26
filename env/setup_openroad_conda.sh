#!/usr/bin/env bash
set -euo pipefail

CONDA_PREFIX_PATH="${1:-/tmp/mac-agent-openroad-env}"

if ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: conda not found in PATH" >&2
  exit 1
fi

echo "Creating conda environment at: ${CONDA_PREFIX_PATH}"
conda create -p "${CONDA_PREFIX_PATH}" python=3.10 -y

echo "Installing OpenROAD from litex-hub"
conda install -p "${CONDA_PREFIX_PATH}" -c litex-hub openroad -y

echo "OpenROAD version:"
conda run -p "${CONDA_PREFIX_PATH}" openroad -version
