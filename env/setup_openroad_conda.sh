#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  env/setup_openroad_conda.sh [options]

Options:
  --prefix <path>   Conda prefix path (default: /tmp/mac-agent-openroad-env)
  --skip-install    Skip OpenROAD installation step
  -h, --help        Show this help
USAGE
}

CONDA_PREFIX_PATH="/tmp/mac-agent-openroad-env"
SKIP_INSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      [[ $# -ge 2 ]] || { echo "ERROR: --prefix expects a value" >&2; exit 1; }
      CONDA_PREFIX_PATH="$2"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
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

if [[ "$SKIP_INSTALL" -eq 0 ]]; then
  echo "Installing OpenROAD from litex-hub"
  conda install -p "${CONDA_PREFIX_PATH}" -c litex-hub openroad -y
else
  echo "Skipping OpenROAD install (--skip-install)"
fi

if conda list -p "${CONDA_PREFIX_PATH}" | rg '^openroad\s' >/dev/null 2>&1; then
  echo "OpenROAD version:"
  conda run -p "${CONDA_PREFIX_PATH}" openroad -version
else
  echo "OpenROAD is not installed in ${CONDA_PREFIX_PATH}"
fi
