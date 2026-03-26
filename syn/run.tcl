# Minimal DC flow for baseline MAC only.
#
# Optional env vars:
#   DC_TOP             (default: mac16x16p32)
#   DC_RTL             (default: <repo>/rtl/baseline.v)
#   DC_TARGET_LIB      (required in real DC runs)
#   DC_LINK_LIB        (default: "* $DC_TARGET_LIB")
#   DC_SYNTHETIC_LIB   (default: dw_foundation.sldb)
#   DC_CLK_PERIOD      (default: 1.0, ns)
#   DC_OUT_DIR         (default: syn/outputs)
#   DC_RPT_DIR         (default: syn/reports)

proc env_or_default {name default_value} {
    if {[info exists ::env($name)] && $::env($name) ne ""} {
        return $::env($name)
    }
    return $default_value
}

set script_dir [file dirname [file normalize [info script]]]
set repo_root [file normalize [file join $script_dir ..]]

set TOP_NAME      [env_or_default DC_TOP mac16x16p32]
set RTL_FILE      [env_or_default DC_RTL [file join $repo_root rtl baseline.v]]
set TARGET_LIB    [env_or_default DC_TARGET_LIB ""]
set SYNTH_LIB     [env_or_default DC_SYNTHETIC_LIB dw_foundation.sldb]
set CLK_PERIOD_NS [env_or_default DC_CLK_PERIOD 1.0]
set OUT_DIR       [env_or_default DC_OUT_DIR [file join $script_dir outputs]]
set RPT_DIR       [env_or_default DC_RPT_DIR [file join $script_dir reports]]

if {$TARGET_LIB eq ""} {
    puts "WARN: DC_TARGET_LIB is not set; set it before real DC synthesis."
}

set LINK_LIB [env_or_default DC_LINK_LIB "* $TARGET_LIB"]

file mkdir $OUT_DIR
file mkdir $RPT_DIR

set_app_var target_library    [list $TARGET_LIB]
set_app_var link_library      $LINK_LIB
set_app_var synthetic_library [list $SYNTH_LIB]

analyze -format verilog $RTL_FILE
elaborate $TOP_NAME
current_design $TOP_NAME
link

# Combinational baseline: constrain input->output max delay as a simple target.
set_max_delay $CLK_PERIOD_NS -from [all_inputs] -to [all_outputs]

compile_ultra

write -format verilog -hierarchy -output [file join $OUT_DIR baseline_mapped.v]
report_timing -max_paths 10 > [file join $RPT_DIR baseline_timing.rpt]
report_area > [file join $RPT_DIR baseline_area.rpt]

puts "Baseline DC flow complete."
