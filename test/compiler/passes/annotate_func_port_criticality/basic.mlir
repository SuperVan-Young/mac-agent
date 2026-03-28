// RUN: compiler-opt --pass lower-arith-to-logic --pass lower-logic-to-asap7 --pass annotate-func-port-criticality
// CHECK: "func.func"() ({
// CHECK: logic.region_kind = "arith.prefix_tree"
// CHECK: timing.critical_port_pairs = [
// CHECK: timing.keep_fast_instances = [
// CHECK: timing.reclaim_instances = [
// CHECK: timing.max_delay =
"builtin.module"() ({
  "arith.prefix_tree"() {implementation = "kogge_stone", lhs_row = ["b0=A[0]", "b1=A[1]", "b2=A[2]", "b3=A[3]"], rhs_row = ["b0=B[0]", "b1=B[1]", "b2=B[2]", "b3=B[3]"], output_name = "D", owner = "arith.prefix_tree"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:4", "input:B:4"], output_ports = ["output:D:4"]} : () -> ()
