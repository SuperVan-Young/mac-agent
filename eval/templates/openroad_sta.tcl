proc require_env {name} {
  if {![info exists ::env($name)] || $::env($name) eq ""} {
    puts stderr "Missing required env var: $name"
    exit 2
  }
}

foreach var {
  NETLIST_PATH
  LIBERTY_PATHS
  SDC_PATH
  TOP_MODULE
  TIMING_SUMMARY_REPORT
  CRITICAL_PATH_REPORT
} {
  require_env $var
}

foreach lib_path [split $::env(LIBERTY_PATHS) ":"] {
  read_liberty $lib_path
}
read_verilog $::env(NETLIST_PATH)
link_design $::env(TOP_MODULE)
read_sdc $::env(SDC_PATH)

report_checks -path_delay max -group_count 1 -digits 4 > $::env(CRITICAL_PATH_REPORT)

set wns "NA"
set tns "NA"
set critical_delay "NA"

catch { set wns [string trim [report_worst_slack -max -digits 4]] }
catch { set tns [string trim [report_tns -digits 4]] }

set cfp [open $::env(CRITICAL_PATH_REPORT) "r"]
set ctext [read $cfp]
close $cfp
foreach line [split $ctext "\n"] {
  if {[regexp {data arrival time} $line]} {
    if {[regexp {([-+]?[0-9]*\.?[0-9]+)} $line -> delay]} {
      set critical_delay $delay
    }
  }
}

set fp [open $::env(TIMING_SUMMARY_REPORT) "w"]
puts $fp "timing_status=complete"
puts $fp "wns=$wns"
puts $fp "tns=$tns"
puts $fp "critical_delay=$critical_delay"
close $fp

report_worst_slack -max -digits 4 >> $::env(TIMING_SUMMARY_REPORT)
catch { report_tns -digits 4 >> $::env(TIMING_SUMMARY_REPORT) }
