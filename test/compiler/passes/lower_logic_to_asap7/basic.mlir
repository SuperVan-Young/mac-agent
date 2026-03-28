// RUN: compiler-opt --pass lower-logic-to-asap7 --pass verify-post-logic-to-physical
// CHECK: "asap7.and2"() {instance_name = "ppg_and2_0"
// CHECK: "asap7.xor2"() {instance_name = "ct_demo_ha_xor"
// CHECK: "asap7.and2"() {instance_name = "ct_demo_ha_and"
// CHECK: "asap7.xor2"() {instance_name = "ct_demo_fa_xor_ab"
// CHECK: "asap7.ao21"() {instance_name = "ct_demo_fa_ao21_carry"
// CHECK-NOT: "logic.full_adder"()
// CHECK-NOT: "logic.half_adder"()
"builtin.module"() ({
  "logic.and2"() {instance_name = "ppg_and2_0", region_kind = "partial_product_generator", output = "pp_0_0", lhs = "A[0]", rhs = "B[0]"} : () -> ()
  "logic.half_adder"() {instance_name = "ct_demo_ha", region_kind = "compressor_tree", sum_out = "ct_c1_sum", carry_out = "ct_c2_carry", lhs = "pp_0_1", rhs = "pp_1_0"} : () -> ()
  "logic.full_adder"() {instance_name = "ct_demo_fa", region_kind = "compressor_tree", sum_out = "ct_c2_sum", carry_out = "ct_c3_carry", lhs = "pp_0_2", rhs = "pp_1_1", cin = "C[2]"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]} : () -> ()
