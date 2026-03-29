// RUN: compiler-opt --pass lower-arith-to-logic --pass verify-post-arith-to-logic
// CHECK: instance_name = "compressor_tree_0_inst"
// CHECK: callee = "mac16x16p32__compressor_tree_0"
// CHECK: "logic.input"() : () -> !rtl.wire<"pp_0_1":1>
// CHECK: "logic.half_adder"(
// CHECK: "logic.constant"() {value = "1'b0"}
// CHECK: logic.region_kind = "arith.compressor_tree"
// CHECK: sym_name = "mac16x16p32__compressor_tree_0"
// CHECK: sym_visibility = "private"
// CHECK-NOT: "arith.compressor_tree"()
"builtin.module"() ({
  %0 = "logic.input"() : () -> !rtl.wire<"pp_0_1":1>
  %1 = "logic.input"() : () -> !rtl.wire<"pp_1_0":1>
  %2 = "logic.input"() : () -> !rtl.wire<"pp_0_2":1>
  %3 = "logic.input"() : () -> !rtl.wire<"pp_1_1":1>
  %4 = "logic.input"() : () -> !rtl.wire<"C[2]":1>
  %5, %6 = "arith.compressor_tree"(%0, %1, %2, %3, %4) {implementation = "dadda", owner = "arith.compressor_tree"} : (!rtl.wire<"pp_0_1":1>, !rtl.wire<"pp_1_0":1>, !rtl.wire<"pp_0_2":1>, !rtl.wire<"pp_1_1":1>, !rtl.wire<"C[2]":1>) -> (!rtl.wire<"ct_lhs":2>, !rtl.wire<"ct_rhs":2>)
}) {func_name = "mac16x16p32", input_ports = ["input:A:4", "input:B:4"], output_ports = ["output:ct_lhs:2", "output:ct_rhs:2"]} : () -> ()
