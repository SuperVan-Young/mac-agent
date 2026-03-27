#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM_DIR="${ROOT_DIR}/sim"
OUT_DIR="${SIM_DIR}/out"
DUT_PATH="${ROOT_DIR}/rtl/baseline.v"
RANDOM_COUNT=5000
SEED=1
SEED_LIST=""
PARALLEL_JOBS=0
A_WIDTH=16
B_WIDTH=16
ACC_WIDTH=32
PIPELINE_CYCLES=1
EXTRA_SRCS=()

usage() {
    cat <<EOF
Usage: $0 [-d <dut_path>] [-n <random_count>] [-s <seed>] [-S <seed_list>] [-j <parallel_jobs>] [-o <out_dir>] [-a <a_width>] [-b <b_width>] [-w <acc_width>] [-p <pipeline_cycles>]

Options:
  -d  DUT file path (default: rtl/baseline.v)
  -n  number of random vectors (default: 5000)
  -s  RNG seed (default: 1)
  -S  comma-separated RNG seed list; each seed launches one simulation
  -j  max parallel simulation jobs (default: number of seeds; 0 means auto)
  -o  output directory (default: sim/out)
  -a  A input width (default: 16)
  -b  B input width (default: 16)
  -w  C/D accumulator width (default: 32)
  -p  pipeline cycles (default: 1; >1 enables latency check)
  -l  extra Verilog source file, may be repeated
EOF
}

while getopts ":d:n:s:S:j:o:a:b:w:p:l:h" opt; do
    case "${opt}" in
        d) DUT_PATH="${OPTARG}" ;;
        n) RANDOM_COUNT="${OPTARG}" ;;
        s) SEED="${OPTARG}" ;;
        S) SEED_LIST="${OPTARG}" ;;
        j) PARALLEL_JOBS="${OPTARG}" ;;
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

for int_arg in RANDOM_COUNT SEED PARALLEL_JOBS A_WIDTH B_WIDTH ACC_WIDTH PIPELINE_CYCLES; do
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

if [[ -z "${SEED_LIST}" ]]; then
    SEED_LIST="${SEED}"
fi

IFS=',' read -r -a SEEDS <<< "${SEED_LIST}"
if [[ "${#SEEDS[@]}" -eq 0 ]]; then
    echo "ERROR: no seeds resolved" >&2
    exit 2
fi
for seed_item in "${SEEDS[@]}"; do
    if ! [[ "${seed_item}" =~ ^[0-9]+$ ]]; then
        echo "ERROR: invalid seed in list: '${seed_item}'" >&2
        exit 2
    fi
done
if [[ "${PARALLEL_JOBS}" -eq 0 ]]; then
    PARALLEL_JOBS="${#SEEDS[@]}"
fi
if [[ "${PARALLEL_JOBS}" -lt 1 ]]; then
    echo "ERROR: PARALLEL_JOBS must be >= 1" >&2
    exit 2
fi

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

run_one_seed() {
    local seed_value="$1"
    local seed_dir="${OUT_DIR}/seed_${seed_value}"
    local seed_vec="${seed_dir}/vectors.txt"
    local seed_log="${seed_dir}/sim.log"
    mkdir -p "${seed_dir}"

    python3 "${SIM_DIR}/vectors.py" \
        --out "${seed_vec}" \
        --random-count "${RANDOM_COUNT}" \
        --seed "${seed_value}" \
        --a-width "${A_WIDTH}" \
        --b-width "${B_WIDTH}" \
        --acc-width "${ACC_WIDTH}" > "${seed_dir}/vectors_gen.log"

    set +e
    vvp "${SIMV}" \
        +VEC_FILE="${seed_vec}" \
        +DUT_NAME="$(basename "${DUT_PATH}")" \
        +PIPELINE_LATENCY="$((PIPELINE_CYCLES - 1))" > "${seed_log}" 2>&1
    local rc=$?
    set -e

    if [[ "${rc}" -eq 0 ]]; then
        echo "SEED=${seed_value} STATUS=PASS"
    else
        echo "SEED=${seed_value} STATUS=FAIL LOG=${seed_log}" >&2
    fi
    return "${rc}"
}

echo "Running simulation for ${#SEEDS[@]} seed(s) with max ${PARALLEL_JOBS} parallel job(s)..."
running_jobs=0
pids=()
for seed_item in "${SEEDS[@]}"; do
    run_one_seed "${seed_item}" &
    pids+=("$!")
    running_jobs=$((running_jobs + 1))
    if [[ "${running_jobs}" -ge "${PARALLEL_JOBS}" ]]; then
        for pid in "${pids[@]}"; do
            wait "${pid}" || true
        done
        pids=()
        running_jobs=0
    fi
done

SIM_RC=0
for pid in "${pids[@]}"; do
    if ! wait "${pid}"; then
        SIM_RC=1
    fi
done

for seed_item in "${SEEDS[@]}"; do
    if [[ ! -f "${OUT_DIR}/seed_${seed_item}/sim.log" ]]; then
        SIM_RC=1
    elif ! rg -q 'SIMULATION_STATUS=PASS|RESULT: PASS' "${OUT_DIR}/seed_${seed_item}/sim.log"; then
        SIM_RC=1
    fi
done

if [[ ${SIM_RC} -eq 0 ]]; then
    echo "SIMULATION_STATUS=PASS"
else
    echo "SIMULATION_STATUS=FAIL"
fi

exit "${SIM_RC}"
