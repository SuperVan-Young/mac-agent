#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  eval/timing/run_timer.sh openroad [--max-paths N] [--endpoint-count N] [--from PINS] [--to PINS] [--output-report PATH]

This is a low-level timing wrapper intended to be called by Makefile.
Required environment variables:
  NETLIST_PATH
  LIBERTY_PATHS
  SDC_PATH
  TOP_MODULE
  TIMING_SUMMARY_REPORT
  CRITICAL_PATH_REPORT

Optional environment variables:
  OPENROAD_CONDA_PREFIX
  TIMING_QUERY_MAX_PATHS
  TIMING_QUERY_ENDPOINT_COUNT
  TIMING_QUERY_FROM
  TIMING_QUERY_TO
  TIMING_QUERY_OUTPUT_REPORT

Query option notes:
  --from/--to accept comma-separated pin/port names or OpenSTA patterns.
  Literal bus bits such as A[15] are supported.
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

require_int() {
  local name="$1"
  local value="$2"
  [[ "${value}" =~ ^[1-9][0-9]*$ ]] || die "${name} must be a positive integer: ${value}"
}

[[ $# -ge 1 ]] || { usage >&2; exit 2; }
TOOL="$1"
shift
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPENROAD_CONDA_PREFIX="${OPENROAD_CONDA_PREFIX:-/tmp/mac-agent-openroad-env}"
TIMING_QUERY_MAX_PATHS="${TIMING_QUERY_MAX_PATHS:-1}"
TIMING_QUERY_ENDPOINT_COUNT="${TIMING_QUERY_ENDPOINT_COUNT:-}"
TIMING_QUERY_FROM="${TIMING_QUERY_FROM:-}"
TIMING_QUERY_TO="${TIMING_QUERY_TO:-}"
TIMING_QUERY_OUTPUT_REPORT="${TIMING_QUERY_OUTPUT_REPORT:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-paths)
      [[ $# -ge 2 ]] || die "Missing value for $1"
      TIMING_QUERY_MAX_PATHS="$2"
      shift 2
      ;;
    --endpoint-count)
      [[ $# -ge 2 ]] || die "Missing value for $1"
      TIMING_QUERY_ENDPOINT_COUNT="$2"
      shift 2
      ;;
    --from)
      [[ $# -ge 2 ]] || die "Missing value for $1"
      TIMING_QUERY_FROM="$2"
      shift 2
      ;;
    --to)
      [[ $# -ge 2 ]] || die "Missing value for $1"
      TIMING_QUERY_TO="$2"
      shift 2
      ;;
    --output-report)
      [[ $# -ge 2 ]] || die "Missing value for $1"
      TIMING_QUERY_OUTPUT_REPORT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
done

for var in NETLIST_PATH LIBERTY_PATHS SDC_PATH TOP_MODULE TIMING_SUMMARY_REPORT CRITICAL_PATH_REPORT; do
  require_env "$var"
done

require_int "TIMING_QUERY_MAX_PATHS" "${TIMING_QUERY_MAX_PATHS}"
if [[ -n "${TIMING_QUERY_ENDPOINT_COUNT}" ]]; then
  require_int "TIMING_QUERY_ENDPOINT_COUNT" "${TIMING_QUERY_ENDPOINT_COUNT}"
fi

export TIMING_QUERY_MAX_PATHS
export TIMING_QUERY_ENDPOINT_COUNT
export TIMING_QUERY_FROM
export TIMING_QUERY_TO
export TIMING_QUERY_OUTPUT_REPORT

case "${TOOL}" in
  openroad)
    command -v conda >/dev/null 2>&1 || die "conda not found in PATH"
    [[ -x "${OPENROAD_CONDA_PREFIX}/bin/sta" ]] || die "Missing ${OPENROAD_CONDA_PREFIX}/bin/sta"
    conda run -p "${OPENROAD_CONDA_PREFIX}" sta "${SCRIPT_DIR}/templates/openroad_sta.tcl"
    ;;
  *)
    die "Unsupported timing tool: ${TOOL} (expected: openroad)"
    ;;
esac

if [[ -f "${TIMING_SUMMARY_REPORT}" ]]; then
  WNS_VALUE="$(awk '/worst slack/{print $NF; exit}' "${TIMING_SUMMARY_REPORT}" || true)"
  TNS_VALUE="$(awk '/^tns /{print $2; exit}' "${TIMING_SUMMARY_REPORT}" || true)"
  if [[ -n "${WNS_VALUE}" || -n "${TNS_VALUE}" ]]; then
    python3 - "${TIMING_SUMMARY_REPORT}" "${WNS_VALUE:-}" "${TNS_VALUE:-}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
wns = sys.argv[2]
tns = sys.argv[3]
lines = path.read_text(encoding="utf-8").splitlines()
updated = []
for line in lines:
    if line.startswith("wns=") and wns:
        updated.append(f"wns={wns}")
    elif line.startswith("tns=") and tns:
        updated.append(f"tns={tns}")
    else:
        updated.append(line)
path.write_text("\n".join(updated) + "\n", encoding="utf-8")
PY
  fi
fi
