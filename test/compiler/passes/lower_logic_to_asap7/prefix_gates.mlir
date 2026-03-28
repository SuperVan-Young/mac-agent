// RUN: compiler-opt --pass lower-logic-to-asap7 --pass verify-post-logic-to-physical
// CHECK: "asap7.xor2"() {instance_name = "pt_b0_xor_p"
// CHECK: "asap7.and2"() {instance_name = "pt_b0_and_g"
// CHECK: "asap7.or2"() {instance_name = "pt_s0_or_g_1"
// CHECK-NOT: "logic.xor2"()
// CHECK-NOT: "logic.and2"()
// CHECK-NOT: "logic.or2"()
"builtin.module"() ({
  "logic.xor2"() {instance_name = "pt_b0_xor_p", region_kind = "prefix_tree", output = "pt_p_0", lhs = "A[0]", rhs = "B[0]"} : () -> ()
  "logic.and2"() {instance_name = "pt_b0_and_g", region_kind = "prefix_tree", output = "pt_g_0", lhs = "A[0]", rhs = "B[0]"} : () -> ()
  "logic.or2"() {instance_name = "pt_s0_or_g_1", region_kind = "prefix_tree", output = "pt_s0_g_1", lhs = "pt_g_1", rhs = "pt_s0_gand_1"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:4", "input:B:4"], output_ports = ["output:D:4"]} : () -> ()
