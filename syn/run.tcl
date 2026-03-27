# Minimal Cadence Genus flow for baseline MAC only.
#
# Optional env vars:
#   GENUS_TOP             (default: mac16x16p32)
#   GENUS_RTL             (default: <repo>/rtl/baseline.v)
#   GENUS_LIB             (required in real Genus runs; .lib path)
#   GENUS_CLK_PERIOD      (default: 1.0, ns)
#   GENUS_OUT_DIR         (default: syn/outputs)
#   GENUS_RPT_DIR         (default: syn/reports)
#   GENUS_DRY_RUN         (default: 0; if 1, parse-only sanity mode)

proc env_or_default {name default_value} {
    if {[info exists ::env($name)] && $::env($name) ne ""} {
        return $::env($name)
    }
    return $default_value
}

set script_dir [file dirname [file normalize [info script]]]
set repo_root [file normalize [file join $script_dir ..]]

set TOP_NAME      [env_or_default GENUS_TOP mac16x16p32]
set RTL_FILE      [env_or_default GENUS_RTL [file join $repo_root rtl baseline.v]]
set LIB_FILE      [env_or_default GENUS_LIB ""]
set CLK_PERIOD_NS [env_or_default GENUS_CLK_PERIOD 1.0]
set OUT_DIR       [env_or_default GENUS_OUT_DIR [file join $script_dir outputs]]
set RPT_DIR       [env_or_default GENUS_RPT_DIR [file join $script_dir reports]]
set DRY_RUN_FLAG  [env_or_default GENUS_DRY_RUN 0]
set DRY_RUN       [expr {$DRY_RUN_FLAG in {1 true TRUE yes YES}}]

if {$LIB_FILE eq ""} {
    puts "WARN: GENUS_LIB is not set; set it before real Genus synthesis."
}

file mkdir $OUT_DIR
file mkdir $RPT_DIR

if {$DRY_RUN} {
    puts "GENUS_DRY_RUN=1: parsed Genus baseline script without executing tool commands."
    puts "Resolved TOP: $TOP_NAME"
    puts "Resolved RTL: $RTL_FILE"
    puts "Resolved LIB: $LIB_FILE"
    puts "Resolved OUT_DIR: $OUT_DIR"
    puts "Resolved RPT_DIR: $RPT_DIR"
    exit 0
}

set_db library [list $LIB_FILE]

read_hdl $RTL_FILE
elaborate $TOP_NAME
current_design $TOP_NAME

# Combinational baseline: constrain input->output max delay as a simple target.
set_max_delay $CLK_PERIOD_NS -from [all_inputs] -to [all_outputs]

syn_generic
syn_map
syn_opt

write_hdl -mapped > [file join $OUT_DIR baseline_mapped.v]
report_timing -max_paths 10 > [file join $RPT_DIR baseline_timing.rpt]
report_area > [file join $RPT_DIR baseline_area.rpt]

puts "Baseline Genus flow complete."
