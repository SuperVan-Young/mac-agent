REPO_ROOT ?= $(CURDIR)

DESIGN_NAME ?= candidate_seed
DESIGN_TYPE ?= candidate
DUT ?= $(REPO_ROOT)/rtl/$(DESIGN_NAME).v

TOP_MODULE ?= mac16x16p32

# Baseline configurable MAC shape.
# Candidate flows remain on the canonical 16x16->32 interface by default.
MAC_A_WIDTH ?= 16
MAC_B_WIDTH ?= 16
MAC_ACC_WIDTH ?= 32
MAC_PIPELINE_CYCLES ?= 1

OPENROAD_CONDA_PREFIX ?= /tmp/mac-agent-openroad-env
LIBERTY_PATHS ?= $(REPO_ROOT)/tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib:$(REPO_ROOT)/tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib:$(REPO_ROOT)/tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib:$(REPO_ROOT)/tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib:$(REPO_ROOT)/tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib

STA_PERIOD_NS ?= 1.000
STA_INPUT_DELAY_NS ?= 0.100
STA_OUTPUT_DELAY_NS ?= 0.100

SIM_RANDOM_COUNT ?= 5000
SIM_SEED ?= 1
CHECK_ENABLE ?= 1

RESULTS_DIR ?= $(REPO_ROOT)/results/$(DESIGN_NAME)
CHECK_LOG ?= $(RESULTS_DIR)/check.log
SIM_OUT_DIR ?= $(RESULTS_DIR)/sim
SIM_LOG ?= $(RESULTS_DIR)/sim.log
EVAL_OUT_DIR ?= $(RESULTS_DIR)/eval_sta
GENERATED_SDC ?= $(EVAL_OUT_DIR)/constraints.sdc
TIMING_SUMMARY ?= $(EVAL_OUT_DIR)/timing_summary.rpt
CRITICAL_PATH ?= $(EVAL_OUT_DIR)/critical_path.rpt
TIMING_LOG ?= $(EVAL_OUT_DIR)/sta.log
AREA_JSON ?= $(RESULTS_DIR)/area.json
