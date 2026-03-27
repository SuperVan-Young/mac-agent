REPO_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
CONFIG ?=

include $(REPO_ROOT)/env/config.mk
ifneq ($(strip $(CONFIG)),)
include $(CONFIG)
endif

.PHONY: help print-config dirs check sim generate-sdc timing area summary all clean

help:
	@printf '%s\n' \
	  'Usage: make [target] [CONFIG=/path/to/config.mk]' \
	  '' \
	  'Core targets:' \
	  '  make all            # check -> sim -> timing/area -> summary' \
	  '  make check          # candidate legality check' \
	  '  make sim            # RTL/gate simulation' \
	  '  make timing         # timing analysis via $(TIMING_TOOL)' \
	  '  make area           # liberty-based area analysis' \
	  '  make summary        # aggregate reports into summary.json/csv' \
	  '' \
	  'Useful variables (override in CONFIG or on CLI):' \
	  '  DESIGN_NAME, DESIGN_TYPE, DUT, RESULTS_DIR' \
	  '  OPENROAD_CONDA_PREFIX, LIBERTY_PATHS' \
	  '  STA_PERIOD_NS, STA_INPUT_DELAY_NS, STA_OUTPUT_DELAY_NS' \
	  '  SIM_RANDOM_COUNT, SIM_SEED, CHECK_ENABLE'

print-config:
	@printf '%s\n' \
	  "CONFIG=$(CONFIG)" \
	  "DESIGN_NAME=$(DESIGN_NAME)" \
	  "DESIGN_TYPE=$(DESIGN_TYPE)" \
	  "DUT=$(DUT)" \
	  "RESULTS_DIR=$(RESULTS_DIR)" \
	  "OPENROAD_CONDA_PREFIX=$(OPENROAD_CONDA_PREFIX)" \
	  "STA_PERIOD_NS=$(STA_PERIOD_NS)" \
	  "STA_INPUT_DELAY_NS=$(STA_INPUT_DELAY_NS)" \
	  "STA_OUTPUT_DELAY_NS=$(STA_OUTPUT_DELAY_NS)"

dirs:
	@mkdir -p "$(RESULTS_DIR)" "$(SIM_OUT_DIR)" "$(EVAL_OUT_DIR)"

check: dirs
ifeq ($(CHECK_ENABLE),1)
	@python3 "$(REPO_ROOT)/tools/check_candidate_netlist.py" "$(DUT)" --liberty "$(LIBERTY_PATHS)" | tee "$(CHECK_LOG)"
else
	@printf '%s\n' 'SKIP: candidate legality check disabled' | tee "$(CHECK_LOG)"
endif

sim: check
	@bash "$(REPO_ROOT)/sim/run_rtl_sim.sh" \
	  -d "$(DUT)" \
	  -n "$(SIM_RANDOM_COUNT)" \
	  -s "$(SIM_SEED)" \
	  -o "$(SIM_OUT_DIR)" > "$(SIM_LOG)" 2>&1

generate-sdc: dirs
	@printf '%s\n' \
	  'create_clock -name VCLK -period $(STA_PERIOD_NS)' \
	  'set_input_delay $(STA_INPUT_DELAY_NS) -clock VCLK [get_ports {A[*] B[*] C[*]}]' \
	  'set_output_delay $(STA_OUTPUT_DELAY_NS) -clock VCLK [get_ports {D[*]}]' > "$(GENERATED_SDC)"

timing: sim generate-sdc
	@NETLIST_PATH="$(DUT)" \
	  LIBERTY_PATHS="$(LIBERTY_PATHS)" \
	  SDC_PATH="$(GENERATED_SDC)" \
	  TOP_MODULE="$(TOP_MODULE)" \
	  TIMING_SUMMARY_REPORT="$(TIMING_SUMMARY)" \
	  CRITICAL_PATH_REPORT="$(CRITICAL_PATH)" \
	  OPENROAD_CONDA_PREFIX="$(OPENROAD_CONDA_PREFIX)" \
	  bash "$(REPO_ROOT)/eval/run_timer.sh" openroad > "$(TIMING_LOG)" 2>&1

area: sim
	@python3 "$(REPO_ROOT)/eval/area_report.py" \
	  --netlist "$(DUT)" \
	  --liberty "$(LIBERTY_PATHS)" \
	  --top "$(TOP_MODULE)" \
	  --out "$(AREA_JSON)"

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
