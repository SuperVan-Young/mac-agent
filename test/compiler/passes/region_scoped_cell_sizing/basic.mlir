// RUN: compiler-opt --pass lower-arith-to-logic --pass lower-logic-to-asap7 --pass annotate-func-port-criticality --pass region-scoped-cell-sizing
// CHECK: "func.func"() ({
// CHECK: instance_name = "pt_b0_xor_p", cell = "XOR2xp5_ASAP7_75t_R"
// CHECK: instance_name = "pt_b3_xor_sum", cell = "XOR2x2_ASAP7_75t_R"
// CHECK: logic.region_kind = "arith.prefix_tree"
// CHECK: timing.keep_fast_instances =
// CHECK: timing.reclaim_instances =
"builtin.module"() ({
  %0 = "logic.input"() : () -> !rtl.wire<"ct_lhs":4>
  %1 = "logic.input"() : () -> !rtl.wire<"ct_rhs":4>
  %2 = "arith.prefix_tree"(%0, %1) {implementation = "kogge_stone", owner = "arith.prefix_tree"} : (!rtl.wire<"ct_lhs":4>, !rtl.wire<"ct_rhs":4>) -> !rtl.wire<"D":4>
}) {func_name = "mac16x16p32", input_ports = ["input:ct_lhs:4", "input:ct_rhs:4"], output_ports = ["output:D:4"]} : () -> ()
