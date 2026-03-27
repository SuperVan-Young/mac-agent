proc require_env {name} {
  if {![info exists ::env($name)] || $::env($name) eq ""} {
    puts stderr "Missing required env var: $name"
    exit 2
  }
}

foreach var {
  NETLIST_PATH
  LEF_PATHS
  LIBERTY_PATHS
  TOP_MODULE
  AREA_INSTANCE_CSV
} {
  require_env $var
}

proc csv_escape {value} {
  set escaped [string map {\" \"\"} $value]
  return "\"$escaped\""
}

foreach lef_path [split $::env(LEF_PATHS) ":"] {
  read_lef $lef_path
}

foreach lib_path [split $::env(LIBERTY_PATHS) ":"] {
  read_liberty $lib_path
}

read_verilog $::env(NETLIST_PATH)
link_design $::env(TOP_MODULE)

report_design_area
report_cell_usage

set block [ord::get_db_block]
set out_dir [file dirname $::env(AREA_INSTANCE_CSV)]
file mkdir $out_dir
set fp [open $::env(AREA_INSTANCE_CSV) "w"]
puts $fp "inst_name,master_name"
if {$block ne "NULL"} {
  foreach inst [$block getInsts] {
    set master [$inst getMaster]
    puts $fp "[csv_escape [$inst getName]],[csv_escape [$master getName]]"
  }
}
close $fp
