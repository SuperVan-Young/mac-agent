# OpenROAD/OpenSTA minimal STA driver.
# Required env vars:
#   NETLIST_PATH LIBERTY_PATHS SDC_PATH OUT_DIR_PATH
#   TIMING_SUMMARY_REPORT CRITICAL_PATH_REPORT TOP_MODULE

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
  OUT_DIR_PATH
  TIMING_SUMMARY_REPORT
  CRITICAL_PATH_REPORT
  TOP_MODULE
} {
  require_env $var
}

foreach lib_path [split $::env(LIBERTY_PATHS) ":"] {
  read_liberty $lib_path
}
read_verilog $::env(NETLIST_PATH)
link_design $::env(TOP_MODULE)
read_sdc $::env(SDC_PATH)

if {[llength [all_clocks]] > 0} {
  catch { set_propagated_clock [all_clocks] }
}

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
puts $fp ""
puts $fp "# OpenROAD summary"
puts $fp "report_worst_slack_max=$wns"
puts $fp "report_tns=$tns"
close $fp

report_worst_slack -max -digits 4 >> $::env(TIMING_SUMMARY_REPORT)
catch { report_tns -digits 4 >> $::env(TIMING_SUMMARY_REPORT) }
catch { report_worst_slack -min -digits 4 >> $::env(TIMING_SUMMARY_REPORT) }
catch { report_clock_skew -digits 4 >> $::env(TIMING_SUMMARY_REPORT) }
