#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  env/setup_conda.sh [options]

Options:
  --prefix <path>          Conda prefix path (default: /tmp/mac-agent-openroad-env)
  --requirements <path>    Python requirements file (default: <repo>/requirements.txt)
  --skip-install           Skip OpenROAD installation step
  --skip-python            Skip pip install -r <requirements>
  -h, --help               Show this help
USAGE
}

CONDA_PREFIX_PATH="/tmp/mac-agent-openroad-env"
SKIP_INSTALL=0
SKIP_PYTHON=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REQUIREMENTS_PATH="${REPO_ROOT}/requirements.txt"
DEFAULT_ASAP7_LIB_DIR="${REPO_ROOT}/tech/asap7/lib/NLDM"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      [[ $# -ge 2 ]] || { echo "ERROR: --prefix expects a value" >&2; exit 1; }
      CONDA_PREFIX_PATH="$2"
      shift 2
      ;;
    --requirements)
      [[ $# -ge 2 ]] || { echo "ERROR: --requirements expects a value" >&2; exit 1; }
      REQUIREMENTS_PATH="$2"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --skip-python)
      SKIP_PYTHON=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: conda not found in PATH" >&2
  exit 1
fi

if [[ -d "${CONDA_PREFIX_PATH}" ]]; then
  echo "Conda environment already exists at: ${CONDA_PREFIX_PATH}"
else
  echo "Creating conda environment at: ${CONDA_PREFIX_PATH}"
  conda create -p "${CONDA_PREFIX_PATH}" python=3.10 -y
fi

echo "Installing base conda dependencies (python, pip, iverilog)"
conda install -p "${CONDA_PREFIX_PATH}" -c conda-forge python=3.10 pip iverilog -y

if [[ "${SKIP_INSTALL}" -eq 0 ]]; then
  echo "Installing OpenROAD from litex-hub"
  conda install -p "${CONDA_PREFIX_PATH}" -c litex-hub -c conda-forge openroad -y
else
  echo "Skipping OpenROAD install (--skip-install)"
fi

if [[ "${SKIP_PYTHON}" -eq 0 ]]; then
  if [[ ! -f "${REQUIREMENTS_PATH}" ]]; then
    echo "ERROR: requirements file not found: ${REQUIREMENTS_PATH}" >&2
    exit 1
  fi
  echo "Installing Python packages from: ${REQUIREMENTS_PATH}"
  conda run -p "${CONDA_PREFIX_PATH}" python -m pip install --upgrade pip
  conda run -p "${CONDA_PREFIX_PATH}" python -m pip install -r "${REQUIREMENTS_PATH}"
else
  echo "Skipping Python package install (--skip-python)"
fi

echo "Tool versions in ${CONDA_PREFIX_PATH}:"
conda run -p "${CONDA_PREFIX_PATH}" python --version
conda run -p "${CONDA_PREFIX_PATH}" iverilog -V
conda run -p "${CONDA_PREFIX_PATH}" vvp -V

if conda list -p "${CONDA_PREFIX_PATH}" | grep -E '^openroad[[:space:]]' >/dev/null 2>&1; then
  conda run -p "${CONDA_PREFIX_PATH}" openroad -version
else
  echo "OpenROAD is not installed in ${CONDA_PREFIX_PATH}"
fi

if [[ -d "${DEFAULT_ASAP7_LIB_DIR}" ]]; then
  echo "Default repo-local ASAP7 liberty bundle:"
  find "${DEFAULT_ASAP7_LIB_DIR}" -maxdepth 1 -type f | sort
else
  echo "WARN: repo-local ASAP7 liberty bundle not found at ${DEFAULT_ASAP7_LIB_DIR}"
fi
