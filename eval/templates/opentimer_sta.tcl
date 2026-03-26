# OpenTimer minimal STA driver.
# Required env vars:
#   NETLIST_PATH LIBERTY_PATH SDC_PATH
#   TIMING_SUMMARY_REPORT CRITICAL_PATH_REPORT

proc require_env {name} {
  if {![info exists ::env($name)] || $::env($name) eq ""} {
    puts stderr "Missing required env var: $name"
    exit 2
  }
}

foreach var {
  NETLIST_PATH
  LIBERTY_PATH
  SDC_PATH
  TIMING_SUMMARY_REPORT
  CRITICAL_PATH_REPORT
} {
  require_env $var
}

# Command names can differ by OpenTimer version. Keep this script minimal
# and aligned with common ot-shell commands.
read_celllib $::env(LIBERTY_PATH)
read_verilog $::env(NETLIST_PATH)
read_sdc $::env(SDC_PATH)
update_timing

report_timing -num_paths 1 > $::env(CRITICAL_PATH_REPORT)

set fp [open $::env(TIMING_SUMMARY_REPORT) "w"]
puts $fp "timing_status=not_run"
puts $fp "wns=NA"
puts $fp "tns=NA"
puts $fp "critical_delay=NA"
close $fp

report_wns >> $::env(TIMING_SUMMARY_REPORT)
catch { report_tns >> $::env(TIMING_SUMMARY_REPORT) }
