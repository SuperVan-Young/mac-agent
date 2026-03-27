REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
CONFIG ?=

include $(REPO_ROOT)/env/config.mk
ifneq ($(strip $(CONFIG)),)
include $(CONFIG)
endif

SYN_LOG ?= $(LOG_DIR)/synth.log

ifeq ($(DESIGN_TYPE),baseline)
EVAL_NETLIST ?= $(SYN_OUT_DIR)/baseline_mapped.v
else
EVAL_NETLIST ?= $(DUT)
endif

.PHONY: help print-config dirs check sim synth generate-sdc timing area summary all clean

help:
	@printf '%s\n' \
	  'Usage: make [target] [CONFIG=/path/to/config.mk]' \
	  '' \
	  'Core targets:' \
	  '  make all            # baseline: synth/check/sim/timing/area/summary; candidate: check/sim/timing/area/summary' \
	  '  make check          # candidate legality check' \
	  '  make sim            # RTL/gate simulation' \
	  '  make synth          # baseline synthesis (Genus)' \
	  '  make timing         # timing analysis via OpenROAD(OpenSTA)' \
	  '  make area           # OpenROAD area analysis with LEF + liberty' \
	  '  make summary        # aggregate reports into summary.json/csv' \
	  '' \
	  'Useful variables (override in CONFIG or on CLI):' \
	  '  DESIGN_NAME, DESIGN_TYPE, DUT, FLOW_RESULTS_ROOT, RESULTS_DIR' \
	  '  MAC_A_WIDTH, MAC_B_WIDTH, MAC_ACC_WIDTH, MAC_PIPELINE_CYCLES' \
	  '  OPENROAD_CONDA_PREFIX, LIBERTY_PATHS, LEF_PATHS' \
	  '  STA_PERIOD_NS, STA_INPUT_DELAY_NS, STA_OUTPUT_DELAY_NS' \
	  '  SIM_RANDOM_COUNT, SIM_SEED, SIM_SEED_LIST, SIM_PARALLEL_JOBS, CHECK_ENABLE' \
	  '' \
	  'Scheduler-inspectable outputs live under:' \
	  '  $(FLOW_RESULTS_ROOT)'

print-config:
	@printf '%s\n' \
	  "CONFIG=$(CONFIG)" \
	  "DESIGN_NAME=$(DESIGN_NAME)" \
	  "DESIGN_TYPE=$(DESIGN_TYPE)" \
	  "DUT=$(DUT)" \
	  "FLOW_RESULTS_ROOT=$(FLOW_RESULTS_ROOT)" \
	  "SCHEDULER_INSPECT_PATH=$(FLOW_RESULTS_ROOT)" \
	  "EVAL_NETLIST=$(EVAL_NETLIST)" \
	  "RESULTS_DIR=$(RESULTS_DIR)" \
	  "LOG_DIR=$(LOG_DIR)" \
	  "SYN_OUT_DIR=$(SYN_OUT_DIR)" \
	  "SYN_RPT_DIR=$(SYN_RPT_DIR)" \
	  "MAC_A_WIDTH=$(MAC_A_WIDTH)" \
	  "MAC_B_WIDTH=$(MAC_B_WIDTH)" \
	  "MAC_ACC_WIDTH=$(MAC_ACC_WIDTH)" \
	  "MAC_PIPELINE_CYCLES=$(MAC_PIPELINE_CYCLES)" \
	  "OPENROAD_CONDA_PREFIX=$(OPENROAD_CONDA_PREFIX)" \
	  "LEF_PATHS=$(LEF_PATHS)" \
	  "SIM_SEED_LIST=$(SIM_SEED_LIST)" \
	  "SIM_PARALLEL_JOBS=$(SIM_PARALLEL_JOBS)" \
	  "STA_PERIOD_NS=$(STA_PERIOD_NS)" \
	  "STA_INPUT_DELAY_NS=$(STA_INPUT_DELAY_NS)" \
	  "STA_OUTPUT_DELAY_NS=$(STA_OUTPUT_DELAY_NS)"

dirs:
	@mkdir -p "$(RESULTS_DIR)" "$(LOG_DIR)" "$(SIM_OUT_DIR)" "$(EVAL_OUT_DIR)" "$(SYN_OUT_DIR)" "$(SYN_RPT_DIR)"

check: dirs
	@mkdir -p "$(dir $(CHECK_LOG))"
ifeq ($(CHECK_ENABLE),1)
ifeq ($(DESIGN_TYPE),candidate)
	@python3 "$(REPO_ROOT)/check/check_candidate_netlist.py" "$(DUT)" --liberty "$(LIBERTY_PATHS)" | tee "$(CHECK_LOG)"
else
	@printf '%s\n' 'SKIP: baseline design does not run candidate legality check' | tee "$(CHECK_LOG)"
endif
else
	@printf '%s\n' 'SKIP: candidate legality check disabled' | tee "$(CHECK_LOG)"
endif

sim: check
	@mkdir -p "$(SIM_OUT_DIR)" "$(dir $(SIM_LOG))"
	@bash "$(REPO_ROOT)/sim/run_rtl_sim.sh" \
	  -d "$(DUT)" \
	  -n "$(SIM_RANDOM_COUNT)" \
	  -s "$(SIM_SEED)" \
	  -S "$(SIM_SEED_LIST)" \
	  -j "$(SIM_PARALLEL_JOBS)" \
	  -a "$(MAC_A_WIDTH)" \
	  -b "$(MAC_B_WIDTH)" \
	  -w "$(MAC_ACC_WIDTH)" \
	  -p "$(MAC_PIPELINE_CYCLES)" \
	  -o "$(SIM_OUT_DIR)" > "$(SIM_LOG)" 2>&1

synth: dirs
	@mkdir -p "$(dir $(SYN_LOG))" "$(SYN_OUT_DIR)" "$(SYN_RPT_DIR)"
ifeq ($(DESIGN_TYPE),baseline)
	@command -v genus >/dev/null 2>&1 || { echo "ERROR: genus not found in PATH"; exit 127; }
	@GENUS_TOP="$(TOP_MODULE)" \
	  GENUS_RTL="$(DUT)" \
	  GENUS_LIB="$(LIBERTY_PATHS)" \
	  GENUS_CLK_PERIOD="$(STA_PERIOD_NS)" \
	  GENUS_A_WIDTH="$(MAC_A_WIDTH)" \
	  GENUS_B_WIDTH="$(MAC_B_WIDTH)" \
	  GENUS_ACC_WIDTH="$(MAC_ACC_WIDTH)" \
	  GENUS_PIPELINE_CYCLES="$(MAC_PIPELINE_CYCLES)" \
	  GENUS_OUT_DIR="$(SYN_OUT_DIR)" \
	  GENUS_RPT_DIR="$(SYN_RPT_DIR)" \
	  genus -no_gui -files "$(REPO_ROOT)/syn/run.tcl" > "$(SYN_LOG)" 2>&1
else
	@printf '%s\n' 'SKIP: synthesis target only applies to baseline design type' > "$(SYN_LOG)"
endif

generate-sdc: dirs
	@if [ "$(DESIGN_TYPE)" = "baseline" ] && [ "$(MAC_PIPELINE_CYCLES)" -gt 1 ]; then \
	  printf '%s\n' \
	    'create_clock -name VCLK -period $(STA_PERIOD_NS) [get_ports clk]' \
	    'set_input_delay $(STA_INPUT_DELAY_NS) -clock VCLK [get_ports {A[*] B[*] C[*]}]' \
	    'set_output_delay $(STA_OUTPUT_DELAY_NS) -clock VCLK [get_ports {D[*]}]' > "$(GENERATED_SDC)"; \
	else \
	  printf '%s\n' \
	    'create_clock -name VCLK -period $(STA_PERIOD_NS)' \
	    'set_input_delay $(STA_INPUT_DELAY_NS) -clock VCLK [get_ports {A[*] B[*] C[*]}]' \
	    'set_output_delay $(STA_OUTPUT_DELAY_NS) -clock VCLK [get_ports {D[*]}]' > "$(GENERATED_SDC)"; \
	fi

ifeq ($(DESIGN_TYPE),baseline)
timing: synth
area: synth
endif

timing: sim generate-sdc
	@mkdir -p "$(EVAL_OUT_DIR)" "$(dir $(TIMING_LOG))"
	@NETLIST_PATH="$(EVAL_NETLIST)" \
	  LIBERTY_PATHS="$(LIBERTY_PATHS)" \
	  SDC_PATH="$(GENERATED_SDC)" \
	  TOP_MODULE="$(TOP_MODULE)" \
	  TIMING_SUMMARY_REPORT="$(TIMING_SUMMARY)" \
	  CRITICAL_PATH_REPORT="$(CRITICAL_PATH)" \
	  OPENROAD_CONDA_PREFIX="$(OPENROAD_CONDA_PREFIX)" \
	  bash "$(REPO_ROOT)/eval/run_timer.sh" openroad > "$(TIMING_LOG)" 2>&1

area: sim
	@mkdir -p "$(EVAL_OUT_DIR)" "$(dir $(AREA_LOG))" "$(dir $(AREA_JSON))"
	@NETLIST_PATH="$(EVAL_NETLIST)" \
	  LEF_PATHS="$(LEF_PATHS)" \
	  LIBERTY_PATHS="$(LIBERTY_PATHS)" \
	  TOP_MODULE="$(TOP_MODULE)" \
	  AREA_LOG="$(AREA_LOG)" \
	  AREA_TOTAL_REPORT="$(AREA_TOTAL_REPORT)" \
	  AREA_BREAKDOWN_REPORT="$(AREA_BREAKDOWN_REPORT)" \
	  AREA_INSTANCE_CSV="$(AREA_INSTANCE_CSV)" \
	  AREA_CELL_DETAIL_REPORT="$(AREA_CELL_DETAIL_REPORT)" \
	  AREA_MODULE_DETAIL_REPORT="$(AREA_MODULE_DETAIL_REPORT)" \
	  AREA_GROUP_DETAIL_REPORT="$(AREA_GROUP_DETAIL_REPORT)" \
	  AREA_JSON="$(AREA_JSON)" \
	  OPENROAD_CONDA_PREFIX="$(OPENROAD_CONDA_PREFIX)" \
	  bash "$(REPO_ROOT)/eval/run_area.sh"

summary: timing area
	@python3 "$(REPO_ROOT)/eval/parse_reports.py" \
	  --design-name "$(DESIGN_NAME)" \
	  --design-type "$(DESIGN_TYPE)" \
	  --top "$(TOP_MODULE)" \
	  --sim-log "$(SIM_LOG)" \
	  --timing-summary "$(TIMING_SUMMARY)" \
	  --critical-path "$(CRITICAL_PATH)" \
	  --area-json "$(AREA_JSON)" \
	  --results-dir "$(RESULTS_DIR)" \
	  --write-csv

all: summary

clean:
	@rm -rf "$(RESULTS_DIR)"
