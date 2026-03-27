#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM_DIR="${ROOT_DIR}/sim"
OUT_DIR="${SIM_DIR}/out"
DUT_PATH="${ROOT_DIR}/rtl/baseline.v"
RANDOM_COUNT=5000
SEED=1
EXTRA_SRCS=()

usage() {
    cat <<EOF
Usage: $0 [-d <dut_path>] [-n <random_count>] [-s <seed>] [-o <out_dir>]

Options:
  -d  DUT file path (default: rtl/baseline.v)
  -n  number of random vectors (default: 5000)
  -s  RNG seed (default: 1)
  -o  output directory (default: sim/out)
  -l  extra Verilog source file, may be repeated
EOF
}

while getopts ":d:n:s:o:l:h" opt; do
    case "${opt}" in
        d) DUT_PATH="${OPTARG}" ;;
        n) RANDOM_COUNT="${OPTARG}" ;;
        s) SEED="${OPTARG}" ;;
        o) OUT_DIR="${OPTARG}" ;;
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

mkdir -p "${OUT_DIR}"
VEC_FILE="${OUT_DIR}/vectors.txt"
SIMV="${OUT_DIR}/simv.out"

if rg -q "_ASAP7_" "${DUT_PATH}"; then
    while IFS= read -r stdcell_src; do
        EXTRA_SRCS+=("${stdcell_src}")
    done < <(find "${ROOT_DIR}/tech/asap7/verilog/stdcell" -maxdepth 1 -type f -name '*.v' | sort)
fi

python3 "${SIM_DIR}/vectors.py" \
    --out "${VEC_FILE}" \
    --random-count "${RANDOM_COUNT}" \
    --seed "${SEED}"

echo "Compiling DUT: ${DUT_PATH}"
iverilog -g2012 \
    -s tb_mac \
    -o "${SIMV}" \
    "${EXTRA_SRCS[@]}" \
    "${DUT_PATH}" \
    "${SIM_DIR}/tb_mac.sv"

echo "Running simulation..."
set +e
vvp "${SIMV}" +VEC_FILE="${VEC_FILE}" +DUT_NAME="$(basename "${DUT_PATH}")"
SIM_RC=$?
set -e

if [[ ${SIM_RC} -eq 0 ]]; then
    echo "SIMULATION_STATUS=PASS"
else
    echo "SIMULATION_STATUS=FAIL"
fi

exit "${SIM_RC}"
