REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := all
CONFIG ?=

# Overrides must be loaded before defaults so derived paths follow CONFIG.
ifneq ($(strip $(CONFIG)),)
include $(CONFIG)
endif
include $(REPO_ROOT)/eval/config.mk
SYN_LOG ?= $(LOG_DIR)/synth.log

.PHONY: help print-config dirs check sim syn synth generate-sdc timing area area-debug summary all clean

help:
	@printf '%s\n' \
	  'make all        # evaluate DUT: check, sim, timing, area, summary (no synthesis)' \
	  'make syn        # synthesize SYN_RTL with Genus; output: $(SYN_OUT_DIR)/baseline_mapped.v' \
	  'make check sim timing area area-debug summary # individual stages' \
	  'make print-config # inspect resolved configuration' \
	  'Override DUT, DESIGN_NAME, RESULTS_DIR, or CONFIG=/path/to/config.mk.'

print-config:
	@$(foreach key,CONFIG DESIGN_NAME DESIGN_TYPE DUT SYN_RTL RESULTS_DIR LOG_DIR SYN_OUT_DIR SYN_RPT_DIR MAC_A_WIDTH MAC_B_WIDTH MAC_ACC_WIDTH MAC_PIPELINE_CYCLES OPENROAD_CONDA_PREFIX LIBERTY_PATHS LEF_PATHS SIM_SEED_LIST SIM_PARALLEL_JOBS CHECK_ENABLE STA_PERIOD_NS STA_INPUT_DELAY_NS STA_OUTPUT_DELAY_NS,printf '%s\n' "$(key)=$($(key))";)

dirs:
	@mkdir -p "$(RESULTS_DIR)" "$(LOG_DIR)" "$(SIM_OUT_DIR)" "$(EVAL_OUT_DIR)" "$(SYN_OUT_DIR)" "$(SYN_RPT_DIR)"

check: dirs
ifeq ($(CHECK_ENABLE),1)
	@python3 "$(REPO_ROOT)/eval/check/check_candidate_netlist.py" "$(DUT)" --liberty "$(LIBERTY_PATHS)" | tee "$(CHECK_LOG)"
else
	@printf '%s\n' 'SKIP: candidate legality check disabled' | tee "$(CHECK_LOG)"
endif

synth: syn

sim: check
	@mkdir -p "$(SIM_OUT_DIR)" "$(dir $(SIM_LOG))"
	@bash "$(REPO_ROOT)/eval/sim/run_rtl_sim.sh" \
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

syn: dirs
	@mkdir -p "$(dir $(SYN_LOG))" "$(SYN_OUT_DIR)" "$(SYN_RPT_DIR)"
	@command -v genus >/dev/null 2>&1 || { echo "ERROR: genus not found in PATH"; exit 127; }
	@cd "$(SYN_OUT_DIR)" && GENUS_TOP="$(TOP_MODULE)" \
	  GENUS_RTL="$(abspath $(SYN_RTL))" \
	  GENUS_LIB="$(LIBERTY_PATHS)" \
	  GENUS_CLK_PERIOD="$(STA_PERIOD_NS)" \
	  GENUS_A_WIDTH="$(MAC_A_WIDTH)" \
	  GENUS_B_WIDTH="$(MAC_B_WIDTH)" \
	  GENUS_ACC_WIDTH="$(MAC_ACC_WIDTH)" \
	  GENUS_PIPELINE_CYCLES="$(MAC_PIPELINE_CYCLES)" \
	  GENUS_OUT_DIR="$(abspath $(SYN_OUT_DIR))" \
	  GENUS_RPT_DIR="$(abspath $(SYN_RPT_DIR))" \
	  genus -no_gui -batch -files "$(REPO_ROOT)/eval/syn/run.tcl" > "$(abspath $(SYN_LOG))" 2>&1

generate-sdc: dirs
	@if [ "$(MAC_PIPELINE_CYCLES)" -gt 1 ]; then \
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

timing: sim generate-sdc
	@mkdir -p "$(EVAL_OUT_DIR)" "$(dir $(TIMING_LOG))"
	@NETLIST_PATH="$(DUT)" \
	  LIBERTY_PATHS="$(LIBERTY_PATHS)" \
	  SDC_PATH="$(GENERATED_SDC)" \
	  TOP_MODULE="$(TOP_MODULE)" \
	  TIMING_SUMMARY_REPORT="$(TIMING_SUMMARY)" \
	  CRITICAL_PATH_REPORT="$(CRITICAL_PATH)" \
	  OPENROAD_CONDA_PREFIX="$(OPENROAD_CONDA_PREFIX)" \
	  bash "$(REPO_ROOT)/eval/timing/run_timer.sh" openroad > "$(TIMING_LOG)" 2>&1

area: sim
	@mkdir -p "$(EVAL_OUT_DIR)" "$(dir $(AREA_LOG))" "$(dir $(AREA_JSON))"
	@NETLIST_PATH="$(DUT)" \
	  LEF_PATHS="$(LEF_PATHS)" \
	  LIBERTY_PATHS="$(LIBERTY_PATHS)" \
	  TOP_MODULE="$(TOP_MODULE)" \
	  AREA_LOG="$(AREA_LOG)" \
	  AREA_TOTAL_REPORT="$(AREA_TOTAL_REPORT)" \
	  AREA_BREAKDOWN_REPORT="$(AREA_BREAKDOWN_REPORT)" \
	  AREA_DETAIL_ENABLE=0 \
	  AREA_JSON="$(AREA_JSON)" \
	  OPENROAD_CONDA_PREFIX="$(OPENROAD_CONDA_PREFIX)" \
	  bash "$(REPO_ROOT)/eval/area/run_area.sh"

area-debug: sim
	@mkdir -p "$(EVAL_OUT_DIR)" "$(dir $(AREA_LOG))" "$(dir $(AREA_JSON))"
	@NETLIST_PATH="$(DUT)" \
	  LEF_PATHS="$(LEF_PATHS)" \
	  LIBERTY_PATHS="$(LIBERTY_PATHS)" \
	  TOP_MODULE="$(TOP_MODULE)" \
	  AREA_LOG="$(AREA_LOG)" \
	  AREA_TOTAL_REPORT="$(AREA_TOTAL_REPORT)" \
	  AREA_BREAKDOWN_REPORT="$(AREA_BREAKDOWN_REPORT)" \
	  AREA_DETAIL_ENABLE=1 \
	  AREA_INSTANCE_CSV="$(AREA_INSTANCE_CSV)" \
	  AREA_CELL_DETAIL_REPORT="$(AREA_CELL_DETAIL_REPORT)" \
	  AREA_MODULE_DETAIL_REPORT="$(AREA_MODULE_DETAIL_REPORT)" \
	  AREA_GROUP_DETAIL_REPORT="$(AREA_GROUP_DETAIL_REPORT)" \
	  AREA_JSON="$(AREA_JSON)" \
	  OPENROAD_CONDA_PREFIX="$(OPENROAD_CONDA_PREFIX)" \
	  bash "$(REPO_ROOT)/eval/area/run_area.sh"

summary: timing area
	@python3 "$(REPO_ROOT)/eval/summary/parse_reports.py" \
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
