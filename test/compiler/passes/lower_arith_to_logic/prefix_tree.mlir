// RUN: compiler-opt --pass lower-arith-to-logic --pass verify-post-arith-to-logic
// CHECK: "logic.instance"() {instance_name = "prefix_tree_0_inst"
// CHECK: callee = "mac16x16p32__prefix_tree_0"
// CHECK: "func.func"() ({
// CHECK: "logic.input"() {port_name = "A[0]"}
// CHECK: instance_name = "pt_b0_xor_p", region_kind = "prefix_tree", output_name = "pt_p_0"
// CHECK: instance_name = "pt_b0_and_g", region_kind = "prefix_tree", output_name = "pt_g_0"
// CHECK: instance_name = "pt_s0_and_p_1", region_kind = "prefix_tree", output_name = "pt_s0_p_1"
// CHECK: instance_name = "pt_s0_ao21_g_1", region_kind = "prefix_tree", output_name = "pt_s0_g_1"
// CHECK: "logic.constant"() {value = "1'b0"}
// CHECK: instance_name = "pt_b3_xor_sum", region_kind = "prefix_tree", output_name = "D[3]"
// CHECK: logic.region_kind = "arith.prefix_tree"
// CHECK: sym_name = "mac16x16p32__prefix_tree_0"
// CHECK: sym_visibility = "private"
// CHECK-NOT: "logic.full_adder"() {instance_name = "pt_b
// CHECK-NOT: "arith.prefix_tree"()
"builtin.module"() ({
  "arith.prefix_tree"() {implementation = "kogge_stone", lhs_row = ["b0=A[0]", "b1=A[1]", "b2=A[2]", "b3=A[3]"], rhs_row = ["b0=B[0]", "b1=B[1]", "b2=B[2]", "b3=B[3]"], output_name = "D", owner = "arith.prefix_tree"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:4", "input:B:4"], output_ports = ["output:D:4"]} : () -> ()
