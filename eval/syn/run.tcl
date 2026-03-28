# Minimal Cadence Genus flow for baseline MAC only.
#
# Optional env vars:
#   GENUS_TOP             (default: mac16x16p32)
#   GENUS_RTL             (default: <repo>/rtl/baseline.v)
#   GENUS_LIB             (default: repo-local ASAP7 TT/RVT liberty bundle, colon-separated)
#   GENUS_CLK_PERIOD      (default: 1.0, ns)
#   GENUS_A_WIDTH         (default: 16)
#   GENUS_B_WIDTH         (default: 16)
#   GENUS_ACC_WIDTH       (default: 32)
#   GENUS_PIPELINE_CYCLES (default: 1)
#   GENUS_OUT_DIR         (default: eval/syn/outputs)
#   GENUS_RPT_DIR         (default: eval/syn/reports)
#   GENUS_DRY_RUN         (default: 0; if 1, parse-only sanity mode)

proc env_or_default {name default_value} {
    if {[info exists ::env($name)] && $::env($name) ne ""} {
        return $::env($name)
    }
    return $default_value
}

set script_dir [file dirname [file normalize [info script]]]
set repo_root [file normalize [file join $script_dir .. ..]]
set DEFAULT_LIB_FILES [join [list \
    [file join $repo_root tech asap7 lib NLDM asap7sc7p5t_AO_RVT_TT_nldm_211120.lib] \
    [file join $repo_root tech asap7 lib NLDM asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib] \
    [file join $repo_root tech asap7 lib NLDM asap7sc7p5t_OA_RVT_TT_nldm_211120.lib] \
    [file join $repo_root tech asap7 lib NLDM asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib] \
    [file join $repo_root tech asap7 lib NLDM asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib] \
] ":"]

set TOP_NAME      [env_or_default GENUS_TOP mac16x16p32]
set RTL_FILE      [env_or_default GENUS_RTL [file join $repo_root rtl baseline.v]]
set LIB_FILES_RAW [env_or_default GENUS_LIB $DEFAULT_LIB_FILES]
set LIB_FILES     [split $LIB_FILES_RAW ":"]
set CLK_PERIOD_NS [env_or_default GENUS_CLK_PERIOD 1.0]
set A_WIDTH       [env_or_default GENUS_A_WIDTH 16]
set B_WIDTH       [env_or_default GENUS_B_WIDTH 16]
set ACC_WIDTH     [env_or_default GENUS_ACC_WIDTH 32]
set PIPELINE_CYCLES [env_or_default GENUS_PIPELINE_CYCLES 1]
set OUT_DIR       [env_or_default GENUS_OUT_DIR [file join $script_dir outputs]]
set RPT_DIR       [env_or_default GENUS_RPT_DIR [file join $script_dir reports]]
set DRY_RUN_FLAG  [env_or_default GENUS_DRY_RUN 0]
set DRY_RUN       [expr {$DRY_RUN_FLAG in {1 true TRUE yes YES}}]

foreach lib_file $LIB_FILES {
    if {![file exists $lib_file]} {
        puts "WARN: Genus liberty not found at $lib_file"
    }
}

file mkdir $OUT_DIR
file mkdir $RPT_DIR

if {$DRY_RUN} {
    puts "GENUS_DRY_RUN=1: parsed Genus baseline script without executing tool commands."
    puts "Resolved TOP: $TOP_NAME"
    puts "Resolved RTL: $RTL_FILE"
    puts "Resolved LIBS: $LIB_FILES_RAW"
    puts "Resolved A_WIDTH: $A_WIDTH"
    puts "Resolved B_WIDTH: $B_WIDTH"
    puts "Resolved ACC_WIDTH: $ACC_WIDTH"
    puts "Resolved PIPELINE_CYCLES: $PIPELINE_CYCLES"
    puts "Resolved OUT_DIR: $OUT_DIR"
    puts "Resolved RPT_DIR: $RPT_DIR"
    exit 0
}

set_db library $LIB_FILES

set HDL_DEFINES [list \
    "MAC_A_WIDTH=$A_WIDTH" \
    "MAC_B_WIDTH=$B_WIDTH" \
    "MAC_ACC_WIDTH=$ACC_WIDTH" \
    "MAC_PIPELINE_CYCLES=$PIPELINE_CYCLES" \
]
if {$PIPELINE_CYCLES > 1} {
    lappend HDL_DEFINES "MAC_USE_CLK=1"
}

read_hdl -define $HDL_DEFINES $RTL_FILE
elaborate $TOP_NAME
current_design $TOP_NAME

if {$PIPELINE_CYCLES > 1} {
    create_clock -name VCLK -period $CLK_PERIOD_NS [get_ports clk]
    set_input_delay [expr {$CLK_PERIOD_NS * 0.1}] -clock VCLK [remove_from_collection [all_inputs] [get_ports clk]]
    set_output_delay [expr {$CLK_PERIOD_NS * 0.1}] -clock VCLK [all_outputs]
} else {
    # Combinational baseline: constrain input->output max delay as a simple target.
    set_max_delay $CLK_PERIOD_NS -from [all_inputs] -to [all_outputs]
}

syn_generic
syn_map
syn_opt

write_hdl -mapped > [file join $OUT_DIR baseline_mapped.v]
report_timing -max_paths 10 > [file join $RPT_DIR baseline_timing.rpt]
report_area > [file join $RPT_DIR baseline_area.rpt]

puts "Baseline Genus flow complete."
