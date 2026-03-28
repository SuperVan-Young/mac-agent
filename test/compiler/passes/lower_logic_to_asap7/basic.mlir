// RUN: compiler-opt --pass lower-logic-to-asap7 --pass verify-post-logic-to-physical
// CHECK: "asap7.half_adder"() {instance_name = "ct_c0_ha"
// CHECK: impl_type = "xor_and"
// CHECK: "asap7.full_adder"() {instance_name = "ct_c1_fa"
// CHECK: impl_type = "xor3_and2"
// CHECK: "asap7.half_adder"() {instance_name = "ct_c2_ha"
// CHECK-NOT: "logic.full_adder"()
// CHECK-NOT: "logic.half_adder"()
"builtin.module"() ({
  "logic.half_adder"() {instance_name = "ct_c0_ha", region_kind = "compressor_tree", sum_out = "ct_c0_sum", carry_out = "ct_c1_carry", lhs = "A[0]", rhs = "B[0]"} : () -> ()
  "logic.full_adder"() {instance_name = "ct_c1_fa", region_kind = "compressor_tree", sum_out = "ct_c1_sum", carry_out = "ct_c2_carry", lhs = "pp_0_1", rhs = "pp_1_0", cin = "C[0]"} : () -> ()
  "logic.half_adder"() {instance_name = "ct_c2_ha", region_kind = "compressor_tree", sum_out = "ct_c2_sum", carry_out = "ct_c3_carry", lhs = "pp_0_2", rhs = "pp_1_1"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]} : () -> ()
