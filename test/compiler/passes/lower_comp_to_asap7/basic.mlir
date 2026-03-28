// RUN: compiler-opt --pass lower-comp-to-asap7
// CHECK: "asap7.xor2"() {instance_name = "ct_c0_ha_sum"
// CHECK: "asap7.and2"() {instance_name = "ct_c0_ha_carry"
// CHECK: "asap7.xor2"() {instance_name = "ct_c1_fa_xor0"
// CHECK: "asap7.xor2"() {instance_name = "ct_c1_fa_xor1"
// CHECK: "asap7.and2"() {instance_name = "ct_c1_fa_carry"
// CHECK-NOT: "comp.fa"()
// CHECK-NOT: "comp.ha"()
"builtin.module"() ({
  "comp.ha"() {instance_name = "ct_c0_ha", sum_out = "ct_c0_sum", carry_out = "ct_c1_carry", lhs = "A[0]", rhs = "B[0]", owner = "arith.compressor_tree"} : () -> ()
  "comp.fa"() {instance_name = "ct_c1_fa", sum_out = "ct_c1_sum", carry_out = "ct_c2_carry", lhs = "pp_0_1", rhs = "pp_1_0", cin = "C[0]", owner = "arith.compressor_tree"} : () -> ()
  "comp.ha"() {instance_name = "ct_c2_ha", sum_out = "ct_c2_sum", carry_out = "ct_c3_carry", lhs = "pp_0_2", rhs = "pp_1_1", owner = "arith.compressor_tree"} : () -> ()
}) : () -> ()
