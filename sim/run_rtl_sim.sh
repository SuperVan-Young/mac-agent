#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM_DIR="${ROOT_DIR}/sim"
OUT_DIR="${SIM_DIR}/out"
DUT_PATH="${ROOT_DIR}/rtl/baseline.v"
RANDOM_COUNT=5000
SEED=1
A_WIDTH=16
B_WIDTH=16
ACC_WIDTH=32
PIPELINE_CYCLES=1
EXTRA_SRCS=()

usage() {
    cat <<EOF
Usage: $0 [-d <dut_path>] [-n <random_count>] [-s <seed>] [-o <out_dir>] [-a <a_width>] [-b <b_width>] [-w <acc_width>] [-p <pipeline_cycles>]

Options:
  -d  DUT file path (default: rtl/baseline.v)
  -n  number of random vectors (default: 5000)
  -s  RNG seed (default: 1)
  -o  output directory (default: sim/out)
  -a  A input width (default: 16)
  -b  B input width (default: 16)
  -w  C/D accumulator width (default: 32)
  -p  pipeline cycles (default: 1; >1 enables latency check)
  -l  extra Verilog source file, may be repeated
EOF
}

while getopts ":d:n:s:o:a:b:w:p:l:h" opt; do
    case "${opt}" in
        d) DUT_PATH="${OPTARG}" ;;
        n) RANDOM_COUNT="${OPTARG}" ;;
        s) SEED="${OPTARG}" ;;
        o) OUT_DIR="${OPTARG}" ;;
        a) A_WIDTH="${OPTARG}" ;;
        b) B_WIDTH="${OPTARG}" ;;
        w) ACC_WIDTH="${OPTARG}" ;;
        p) PIPELINE_CYCLES="${OPTARG}" ;;
        l) EXTRA_SRCS+=("${OPTARG}") ;;
        h)
            usage
            exit 0
            ;;
        \?)
            echo "ERROR: invalid option -${OPTARG}" >&2
            usage
            exit 2
            ;;
        :)
            echo "ERROR: option -${OPTARG} requires an argument" >&2
            usage
            exit 2
            ;;
    esac
done

if ! command -v iverilog >/dev/null 2>&1; then
    echo "ERROR: iverilog not found in PATH" >&2
    exit 127
fi

if ! command -v vvp >/dev/null 2>&1; then
    echo "ERROR: vvp not found in PATH" >&2
    exit 127
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found in PATH" >&2
    exit 127
fi

if [[ ! -f "${DUT_PATH}" ]]; then
    echo "ERROR: DUT file not found: ${DUT_PATH}" >&2
    exit 2
fi

for int_arg in RANDOM_COUNT SEED A_WIDTH B_WIDTH ACC_WIDTH PIPELINE_CYCLES; do
    if ! [[ "${!int_arg}" =~ ^[0-9]+$ ]]; then
        echo "ERROR: ${int_arg} must be a non-negative integer, got '${!int_arg}'" >&2
        exit 2
    fi
done
if [[ "${A_WIDTH}" -eq 0 || "${B_WIDTH}" -eq 0 || "${ACC_WIDTH}" -eq 0 ]]; then
    echo "ERROR: A/B/ACC widths must be greater than zero" >&2
    exit 2
fi
if [[ "${PIPELINE_CYCLES}" -lt 1 ]]; then
    echo "ERROR: PIPELINE_CYCLES must be >= 1" >&2
    exit 2
fi

mkdir -p "${OUT_DIR}"
VEC_FILE="${OUT_DIR}/vectors.txt"
SIMV="${OUT_DIR}/simv.out"

if rg -q "_ASAP7_" "${DUT_PATH}"; then
    while IFS= read -r stdcell_src; do
        EXTRA_SRCS+=("${stdcell_src}")
    done < <(find "${ROOT_DIR}/tech/asap7/verilog/stdcell" -maxdepth 1 -type f -name '*.v' | sort)
fi

IVERILOG_DEFINES=(
    "-DMAC_A_WIDTH=${A_WIDTH}"
    "-DMAC_B_WIDTH=${B_WIDTH}"
    "-DMAC_ACC_WIDTH=${ACC_WIDTH}"
    "-DMAC_PIPELINE_CYCLES=${PIPELINE_CYCLES}"
)
if [[ "${PIPELINE_CYCLES}" -gt 1 && "$(basename "${DUT_PATH}")" == "baseline.v" ]]; then
    IVERILOG_DEFINES+=("-DMAC_USE_CLK=1")
fi

echo "Compiling DUT: ${DUT_PATH}"
iverilog -g2012 \
    "${IVERILOG_DEFINES[@]}" \
    -s tb_mac \
    -o "${SIMV}" \
    "${EXTRA_SRCS[@]}" \
    "${DUT_PATH}" \
    "${SIM_DIR}/tb_mac.sv"

python3 "${SIM_DIR}/vectors.py" \
    --out "${VEC_FILE}" \
    --random-count "${RANDOM_COUNT}" \
    --seed "${SEED}" \
    --a-width "${A_WIDTH}" \
    --b-width "${B_WIDTH}" \
    --acc-width "${ACC_WIDTH}"

echo "Running simulation..."
set +e
vvp "${SIMV}" \
    +VEC_FILE="${VEC_FILE}" \
    +DUT_NAME="$(basename "${DUT_PATH}")" \
    +PIPELINE_LATENCY="$((PIPELINE_CYCLES - 1))"
SIM_RC=$?
set -e

if [[ ${SIM_RC} -eq 0 ]]; then
    echo "SIMULATION_STATUS=PASS"
else
    echo "SIMULATION_STATUS=FAIL"
fi

exit "${SIM_RC}"
