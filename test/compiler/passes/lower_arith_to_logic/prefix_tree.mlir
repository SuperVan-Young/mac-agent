// RUN: compiler-opt --pass lower-arith-to-logic --pass verify-post-arith-to-logic
// CHECK: instance_name = "prefix_tree_0_inst"
// CHECK: callee = "mac16x16p32__prefix_tree_0"
// CHECK: ^bb0(
// CHECK: !rtl.wire<"ct_lhs[0]":1>
// CHECK: instance_name = "pt_b0_xor_p"
// CHECK: instance_name = "pt_b0_and_g"
// CHECK: instance_name = "pt_s0_ao21_g_1"
// CHECK: "logic.constant"() {value = "1'b0"}
// CHECK: instance_name = "pt_b3_xor_sum"
// CHECK: "func.return"(
// CHECK: logic.region_kind = "arith.prefix_tree"
// CHECK: sym_name = "mac16x16p32__prefix_tree_0"
// CHECK: sym_visibility = "private"
// CHECK-NOT: "logic.full_adder"()
// CHECK-NOT: "arith.prefix_tree"()
"builtin.module"() ({
  %0 = "logic.input"() : () -> !rtl.wire<"ct_lhs":4>
  %1 = "logic.input"() : () -> !rtl.wire<"ct_rhs":4>
  %2 = "arith.prefix_tree"(%0, %1) {implementation = #arith.prefix_impl<kogge_stone>, owner = "arith.prefix_tree"} : (!rtl.wire<"ct_lhs":4>, !rtl.wire<"ct_rhs":4>) -> !rtl.wire<"D":4>
}) {func_name = "mac16x16p32", input_ports = ["input:ct_lhs:4", "input:ct_rhs:4"], output_ports = ["output:D:4"]} : () -> ()
