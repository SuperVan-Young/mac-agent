// RUN: compiler-opt --pass lower-arith-to-logic
// CHECK: "logic.half_adder"() {instance_name = "ct_c0_ha"
// CHECK: region_kind = "compressor_tree"
// CHECK: "logic.full_adder"() {instance_name = "ct_c1_fa"
// CHECK: "logic.half_adder"() {instance_name = "ct_c2_ha"
// CHECK-NOT: "arith.compressor_tree"()
"builtin.module"() ({
  "arith.compressor_tree"() {reduction_type = "dadda", columns = ["c0=A[0],B[0]", "c1=pp_0_1,pp_1_0,C[0]", "c2=pp_0_2,pp_1_1"], owner = "arith.compressor_tree"} : () -> ()
}) : () -> ()
