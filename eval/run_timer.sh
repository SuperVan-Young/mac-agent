#!/usr/bin/env bash
set -euo pipefail

# Generic STA runner for mapped baseline netlists and candidate netlists.
# Inputs: netlist, liberty, sdc. Outputs: stable reports under --out-dir.
#
# Typical usage:
#   ./eval/run_timer.sh \
#     --netlist syn/outputs/baseline_mapped.v \
#     --sdc eval/templates/minimal.sdc
#
# Notes:
# - Tool auto-detection: OpenROAD first, then OpenTimer (ot-shell).
# - `--dry-run` validates arguments and prints the resolved command only.

usage() {
  cat <<'USAGE'
Usage:
  eval/run_timer.sh --netlist <file.v> --sdc <file.sdc> [options]

Required:
  --netlist <path>    Gate-level netlist to analyze
  --sdc <path>        SDC constraint file

Optional:
  --liberty <path>    Liberty timing library path, or a colon-separated list
                      of liberty files. Default: repo-local ASAP7 TT/RVT bundle.
  --out-dir <path>    Output report directory
  --top <name>        Top module name (default: mac16x16p32)
  --tool <name>       auto | openroad | opentimer (default: auto)
  --conda-prefix <p>  Conda prefix for OpenROAD fallback (default: /tmp/mac-agent-openroad-env)
  --timeout-sec <n>   Timeout in seconds (default: 90)
  --dry-run           Validate and print command without execution
  -h, --help          Show this help

Outputs written to out-dir:
  timing_summary.rpt
  critical_path.rpt
  sta.log
USAGE
}

die() {
  echo "ERROR: $*" >&2
  exit 1
}

NETLIST=""
LIBERTY=""
SDC=""
OUT_DIR=""
TOP_MODULE="mac16x16p32"
TOOL="auto"
CONDA_PREFIX_PATH="${OPENROAD_CONDA_PREFIX:-/tmp/mac-agent-openroad-env}"
TIMEOUT_SEC="90"
DRY_RUN=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_LIBERTIES=(
  "${REPO_ROOT}/tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib"
  "${REPO_ROOT}/tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib"
  "${REPO_ROOT}/tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib"
  "${REPO_ROOT}/tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib"
  "${REPO_ROOT}/tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"
)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --netlist) NETLIST="${2:-}"; shift 2 ;;
    --liberty) LIBERTY="${2:-}"; shift 2 ;;
    --sdc) SDC="${2:-}"; shift 2 ;;
    --out-dir) OUT_DIR="${2:-}"; shift 2 ;;
    --top) TOP_MODULE="${2:-}"; shift 2 ;;
    --tool) TOOL="${2:-}"; shift 2 ;;
    --conda-prefix) CONDA_PREFIX_PATH="${2:-}"; shift 2 ;;
    --timeout-sec) TIMEOUT_SEC="${2:-}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "Unknown argument: $1" ;;
  esac
done

[[ -n "$NETLIST" ]] || die "--netlist is required"
if [[ -z "$LIBERTY" ]]; then
  LIBERTY="$(IFS=:; echo "${DEFAULT_LIBERTIES[*]}")"
fi
[[ -n "$SDC" ]] || die "--sdc is required"
[[ -f "$NETLIST" ]] || die "Netlist not found: $NETLIST"
[[ -f "$SDC" ]] || die "SDC not found: $SDC"

IFS=':' read -r -a LIBERTY_FILES <<< "$LIBERTY"
[[ "${#LIBERTY_FILES[@]}" -gt 0 ]] || die "No liberty files resolved"
for liberty_file in "${LIBERTY_FILES[@]}"; do
  [[ -f "$liberty_file" ]] || die "Liberty not found: $liberty_file"
done

case "$TOOL" in
  auto|openroad|opentimer) ;;
  *) die "--tool must be one of: auto, openroad, opentimer" ;;
esac

if [[ ! "$TIMEOUT_SEC" =~ ^[0-9]+$ ]]; then
  die "--timeout-sec must be an integer"
fi

design_name="$(basename "$NETLIST")"
design_name="${design_name%.*}"
if [[ -z "$OUT_DIR" ]]; then
  OUT_DIR="results/${design_name}/eval_sta"
fi
mkdir -p "$OUT_DIR"

resolve_tool() {
  local req="$1"
  local have_openroad=1
  if command -v openroad >/dev/null 2>&1; then
    have_openroad=0
  elif command -v conda >/dev/null 2>&1 && [[ -x "${CONDA_PREFIX_PATH}/bin/openroad" ]]; then
    have_openroad=0
  fi

  if [[ "$req" == "openroad" ]]; then
    [[ "$have_openroad" -eq 0 ]] || die "Requested openroad, but command not found in PATH or ${CONDA_PREFIX_PATH}/bin/openroad"
    echo "openroad"
    return
  fi
  if [[ "$req" == "opentimer" ]]; then
    command -v ot-shell >/dev/null 2>&1 || die "Requested opentimer, but command not found"
    echo "opentimer"
    return
  fi
  if [[ "$have_openroad" -eq 0 ]]; then
    echo "openroad"
    return
  fi
  if command -v ot-shell >/dev/null 2>&1; then
    echo "opentimer"
    return
  fi
  die "No STA tool found (expected 'openroad' or 'ot-shell' in PATH)"
}

TOOL_RESOLVED=""

if [[ "$DRY_RUN" -eq 1 && "$TOOL" == "auto" ]]; then
  if command -v openroad >/dev/null 2>&1; then
    TOOL_RESOLVED="openroad"
  elif command -v conda >/dev/null 2>&1 && [[ -x "${CONDA_PREFIX_PATH}/bin/openroad" ]]; then
    TOOL_RESOLVED="openroad"
  elif command -v ot-shell >/dev/null 2>&1; then
    TOOL_RESOLVED="opentimer"
  else
    TOOL_RESOLVED="none"
  fi
else
  TOOL_RESOLVED="$(resolve_tool "$TOOL")"
fi

export NETLIST_PATH="$(realpath "$NETLIST")"
export LIBERTY_PATHS="$(printf '%s:' "${LIBERTY_FILES[@]}")"
export LIBERTY_PATHS="${LIBERTY_PATHS%:}"
export SDC_PATH="$(realpath "$SDC")"
export OUT_DIR_PATH="$(realpath "$OUT_DIR")"
export TOP_MODULE
export TIMING_SUMMARY_REPORT="${OUT_DIR_PATH}/timing_summary.rpt"
export CRITICAL_PATH_REPORT="${OUT_DIR_PATH}/critical_path.rpt"
STA_LOG="${OUT_DIR_PATH}/sta.log"

if [[ "$TOOL_RESOLVED" == "openroad" ]]; then
  if command -v openroad >/dev/null 2>&1; then
    STA_CMD=(openroad -no_init -exit "${SCRIPT_DIR}/templates/openroad_sta.tcl")
  else
    command -v conda >/dev/null 2>&1 || die "conda is required for --conda-prefix fallback"
    [[ -x "${CONDA_PREFIX_PATH}/bin/openroad" ]] || die "OpenROAD not found at ${CONDA_PREFIX_PATH}/bin/openroad"
    STA_CMD=(conda run -p "${CONDA_PREFIX_PATH}" openroad -no_init -exit "${SCRIPT_DIR}/templates/openroad_sta.tcl")
  fi
elif [[ "$TOOL_RESOLVED" == "opentimer" ]]; then
  STA_CMD=(ot-shell "${SCRIPT_DIR}/templates/opentimer_sta.tcl")
else
  STA_CMD=(echo "No STA tool found in PATH")
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  {
    echo "Dry run passed"
    echo "Resolved tool: ${TOOL_RESOLVED}"
    echo "Output dir: ${OUT_DIR_PATH}"
    echo "Conda prefix: ${CONDA_PREFIX_PATH}"
    printf 'Command:'
    printf ' %q' "${STA_CMD[@]}"
    printf '\n'
  } | tee "$STA_LOG"
  exit 0
fi

run_with_timeout() {
  if command -v timeout >/dev/null 2>&1; then
    timeout "${TIMEOUT_SEC}s" "${STA_CMD[@]}"
    return
  fi
  if command -v gtimeout >/dev/null 2>&1; then
    gtimeout "${TIMEOUT_SEC}s" "${STA_CMD[@]}"
    return
  fi
  echo "WARN: timeout command not found; running without timeout cap" >&2
  "${STA_CMD[@]}"
}

{
  echo "Running STA"
  echo "Tool: ${TOOL_RESOLVED}"
  echo "Top: ${TOP_MODULE}"
  echo "Netlist: ${NETLIST_PATH}"
  echo "Liberties: ${LIBERTY_PATHS}"
  echo "SDC: ${SDC_PATH}"
  echo "Out: ${OUT_DIR_PATH}"
  run_with_timeout
} |& tee "$STA_LOG"

[[ -f "$TIMING_SUMMARY_REPORT" ]] || die "Missing output: $TIMING_SUMMARY_REPORT"
[[ -f "$CRITICAL_PATH_REPORT" ]] || die "Missing output: $CRITICAL_PATH_REPORT"

echo "STA completed. Reports:"
echo "  $TIMING_SUMMARY_REPORT"
echo "  $CRITICAL_PATH_REPORT"
