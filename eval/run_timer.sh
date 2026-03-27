#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  eval/run_timer.sh openroad

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

for var in NETLIST_PATH LIBERTY_PATHS SDC_PATH TOP_MODULE TIMING_SUMMARY_REPORT CRITICAL_PATH_REPORT; do
  require_env "$var"
done

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
