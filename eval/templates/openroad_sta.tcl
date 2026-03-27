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

proc regex_escape {text} {
  set escaped $text
  regsub -all {[][(){}.^$*+?|\\]} $escaped {\\&} escaped
  return $escaped
}

proc resolve_sta_objects {spec} {
  set resolved {}
  foreach raw_token [split $spec ","] {
    set token [string trim $raw_token]
    if {$token eq ""} {
      continue
    }

    set exact_re "^([regex_escape $token])$"
    set objs [get_pins -quiet -regexp $exact_re]
    if {[llength $objs] == 0} {
      set objs [get_ports -quiet -regexp $exact_re]
    }
    if {[llength $objs] == 0} {
      set objs [get_pins -quiet $token]
    }
    if {[llength $objs] == 0} {
      set objs [get_ports -quiet $token]
    }
    if {[llength $objs] == 0} {
      puts stderr "Unable to resolve timing object: $token"
      exit 3
    }
    foreach obj $objs {
      lappend resolved $obj
    }
  }
  return $resolved
}

foreach lib_path [split $::env(LIBERTY_PATHS) ":"] {
  read_liberty $lib_path
}
read_verilog $::env(NETLIST_PATH)
link_design $::env(TOP_MODULE)
read_sdc $::env(SDC_PATH)

set report_path $::env(CRITICAL_PATH_REPORT)
if {[info exists ::env(TIMING_QUERY_OUTPUT_REPORT)] && $::env(TIMING_QUERY_OUTPUT_REPORT) ne ""} {
  set report_path $::env(TIMING_QUERY_OUTPUT_REPORT)
}

set group_count 1
if {[info exists ::env(TIMING_QUERY_MAX_PATHS)] && $::env(TIMING_QUERY_MAX_PATHS) ne ""} {
  set group_count $::env(TIMING_QUERY_MAX_PATHS)
}

set report_cmd [list report_checks -path_delay max -digits 4 -group_count $group_count]

if {[info exists ::env(TIMING_QUERY_ENDPOINT_COUNT)] && $::env(TIMING_QUERY_ENDPOINT_COUNT) ne ""} {
  lappend report_cmd -endpoint_count $::env(TIMING_QUERY_ENDPOINT_COUNT)
}
if {[info exists ::env(TIMING_QUERY_FROM)] && $::env(TIMING_QUERY_FROM) ne ""} {
  lappend report_cmd -from [resolve_sta_objects $::env(TIMING_QUERY_FROM)]
}
if {[info exists ::env(TIMING_QUERY_TO)] && $::env(TIMING_QUERY_TO) ne ""} {
  lappend report_cmd -to [resolve_sta_objects $::env(TIMING_QUERY_TO)]
}

eval [concat $report_cmd [list > $report_path]]

set wns "NA"
set tns "NA"
set critical_delay "NA"

catch { set wns [string trim [report_worst_slack -max -digits 4]] }
catch { set tns [string trim [report_tns -digits 4]] }

set cfp [open $report_path "r"]
set ctext [read $cfp]
close $cfp
foreach line [split $ctext "\n"] {
  if {[regexp {data arrival time} $line]} {
    if {[regexp {([-+]?[0-9]*\.?[0-9]+)} $line -> delay]} {
      set critical_delay $delay
      break
    }
  }
}

set fp [open $::env(TIMING_SUMMARY_REPORT) "w"]
puts $fp "timing_status=complete"
puts $fp "wns=$wns"
puts $fp "tns=$tns"
puts $fp "critical_delay=$critical_delay"
puts $fp "query_group_count=$group_count"
puts $fp "query_report=$report_path"
if {[info exists ::env(TIMING_QUERY_ENDPOINT_COUNT)] && $::env(TIMING_QUERY_ENDPOINT_COUNT) ne ""} {
  puts $fp "query_endpoint_count=$::env(TIMING_QUERY_ENDPOINT_COUNT)"
}
if {[info exists ::env(TIMING_QUERY_FROM)] && $::env(TIMING_QUERY_FROM) ne ""} {
  puts $fp "query_from=$::env(TIMING_QUERY_FROM)"
}
if {[info exists ::env(TIMING_QUERY_TO)] && $::env(TIMING_QUERY_TO) ne ""} {
  puts $fp "query_to=$::env(TIMING_QUERY_TO)"
}
close $fp

report_worst_slack -max -digits 4 >> $::env(TIMING_SUMMARY_REPORT)
catch { report_tns -digits 4 >> $::env(TIMING_SUMMARY_REPORT) }
