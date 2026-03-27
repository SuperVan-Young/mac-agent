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
} {
  require_env $var
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
