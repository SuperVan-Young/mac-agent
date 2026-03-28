#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  eval/area/run_area.sh

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
  AREA_DETAIL_ENABLE
  AREA_INSTANCE_CSV
  AREA_CELL_DETAIL_REPORT
  AREA_MODULE_DETAIL_REPORT
  AREA_GROUP_DETAIL_REPORT
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

[[ $# -eq 0 ]] || { usage >&2; exit 2; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENROAD_CONDA_PREFIX="${OPENROAD_CONDA_PREFIX:-/tmp/mac-agent-openroad-env}"
AREA_DETAIL_ENABLE="${AREA_DETAIL_ENABLE:-0}"

for var in NETLIST_PATH LEF_PATHS LIBERTY_PATHS TOP_MODULE AREA_LOG AREA_TOTAL_REPORT AREA_BREAKDOWN_REPORT AREA_JSON; do
  require_env "$var"
done

if [[ "${AREA_DETAIL_ENABLE}" == "1" ]]; then
  for var in AREA_INSTANCE_CSV AREA_CELL_DETAIL_REPORT AREA_MODULE_DETAIL_REPORT AREA_GROUP_DETAIL_REPORT; do
    require_env "$var"
  done
fi

command -v conda >/dev/null 2>&1 || die "conda not found in PATH"
[[ -x "${OPENROAD_CONDA_PREFIX}/bin/openroad" ]] || die "Missing ${OPENROAD_CONDA_PREFIX}/bin/openroad"
conda run -p "${OPENROAD_CONDA_PREFIX}" openroad \
  -no_init \
  -exit \
  -log "${AREA_LOG}" \
  "${SCRIPT_DIR}/templates/openroad_area.tcl" >/dev/null 2>&1

if [[ "${AREA_DETAIL_ENABLE}" == "1" ]]; then
  python3 "${SCRIPT_DIR}/openroad_area_report.py" \
    --detail \
    --openroad-log "${AREA_LOG}" \
    --netlist "${NETLIST_PATH}" \
    --liberty-paths "${LIBERTY_PATHS}" \
    --top-module "${TOP_MODULE}" \
    --design-area-rpt "${AREA_TOTAL_REPORT}" \
    --cell-usage-rpt "${AREA_BREAKDOWN_REPORT}" \
    --instance-area-csv "${AREA_INSTANCE_CSV}" \
    --cell-area-rpt "${AREA_CELL_DETAIL_REPORT}" \
    --module-area-rpt "${AREA_MODULE_DETAIL_REPORT}" \
    --group-area-rpt "${AREA_GROUP_DETAIL_REPORT}" \
    --out "${AREA_JSON}"
else
  python3 "${SCRIPT_DIR}/openroad_area_report.py" \
    --openroad-log "${AREA_LOG}" \
    --design-area-rpt "${AREA_TOTAL_REPORT}" \
    --cell-usage-rpt "${AREA_BREAKDOWN_REPORT}" \
    --out "${AREA_JSON}"
fi
