#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  eval/run_area.sh openroad

Low-level area wrapper intended to be called by Makefile.
Required environment variables:
  NETLIST_PATH
  LEF_PATHS
  LIBERTY_PATHS
  TOP_MODULE
  AREA_LOG
  AREA_TOTAL_REPORT
  AREA_BREAKDOWN_REPORT
  AREA_JSON

Optional environment variables:
  OPENROAD_CONDA_PREFIX
USAGE
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

require_env() {
  local name="$1"
  [[ -n "${!name:-}" ]] || die "Missing environment variable: ${name}"
}

[[ $# -eq 1 ]] || { usage >&2; exit 2; }
TOOL="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENROAD_CONDA_PREFIX="${OPENROAD_CONDA_PREFIX:-/tmp/mac-agent-openroad-env}"

for var in NETLIST_PATH LEF_PATHS LIBERTY_PATHS TOP_MODULE AREA_LOG AREA_TOTAL_REPORT AREA_BREAKDOWN_REPORT AREA_JSON; do
  require_env "$var"
done

case "${TOOL}" in
  openroad)
    command -v conda >/dev/null 2>&1 || die "conda not found in PATH"
    [[ -x "${OPENROAD_CONDA_PREFIX}/bin/openroad" ]] || die "Missing ${OPENROAD_CONDA_PREFIX}/bin/openroad"
    conda run -p "${OPENROAD_CONDA_PREFIX}" openroad \
      -no_init \
      -exit \
      -log "${AREA_LOG}" \
      "${SCRIPT_DIR}/templates/openroad_area.tcl" >/dev/null 2>&1
    ;;
  *)
    die "Unsupported area tool: ${TOOL} (expected: openroad)"
    ;;
esac

python3 "${SCRIPT_DIR}/openroad_area_report.py" \
  --openroad-log "${AREA_LOG}" \
  --design-area-rpt "${AREA_TOTAL_REPORT}" \
  --cell-usage-rpt "${AREA_BREAKDOWN_REPORT}" \
  --out "${AREA_JSON}"
