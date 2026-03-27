REPO_ROOT ?= $(CURDIR)

DESIGN_NAME ?= candidate_mac16x16p32
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
LEF_PATHS ?= $(REPO_ROOT)/tech/asap7/lef/asap7_tech_1x_201209.lef:$(REPO_ROOT)/tech/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef:$(REPO_ROOT)/tech/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef:$(REPO_ROOT)/tech/asap7/lef/asap7sc7p5t_28_SL_1x_220121a.lef:$(REPO_ROOT)/tech/asap7/lef/asap7sc7p5t_DFFHQNH2V2X.lef:$(REPO_ROOT)/tech/asap7/lef/asap7sc7p5t_DFFHQNV2X.lef:$(REPO_ROOT)/tech/asap7/lef/asap7sc7p5t_DFFHQNV4X.lef

STA_PERIOD_NS ?= 1.000
STA_INPUT_DELAY_NS ?= 0.100
STA_OUTPUT_DELAY_NS ?= 0.100

SIM_RANDOM_COUNT ?= 5000
SIM_SEED ?= 1
SIM_SEED_LIST ?= $(SIM_SEED)
SIM_PARALLEL_JOBS ?= 0
CHECK_ENABLE ?= 1

# Canonical scheduler-inspectable output root.
FLOW_RESULTS_ROOT ?= $(REPO_ROOT)/results/fixed
RESULTS_DIR ?= $(FLOW_RESULTS_ROOT)
LOG_DIR ?= $(RESULTS_DIR)/logs
CHECK_LOG ?= $(LOG_DIR)/check.log
SIM_OUT_DIR ?= $(RESULTS_DIR)/sim
SIM_LOG ?= $(LOG_DIR)/sim.log
EVAL_OUT_DIR ?= $(RESULTS_DIR)/eval_sta
SYN_OUT_DIR ?= $(RESULTS_DIR)/syn/outputs
SYN_RPT_DIR ?= $(RESULTS_DIR)/syn/reports
GENERATED_SDC ?= $(EVAL_OUT_DIR)/constraints.sdc
TIMING_SUMMARY ?= $(EVAL_OUT_DIR)/timing_summary.rpt
CRITICAL_PATH ?= $(EVAL_OUT_DIR)/critical_path.rpt
TIMING_LOG ?= $(LOG_DIR)/sta.log
AREA_JSON ?= $(RESULTS_DIR)/area.json
AREA_LOG ?= $(LOG_DIR)/area.log
AREA_TOTAL_REPORT ?= $(EVAL_OUT_DIR)/design_area.rpt
AREA_BREAKDOWN_REPORT ?= $(EVAL_OUT_DIR)/cell_usage.rpt
