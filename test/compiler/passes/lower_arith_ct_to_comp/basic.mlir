// RUN: compiler-opt --pass lower-arith-ct-to-comp
// CHECK: "comp.ha"() {instance_name = "ct_c0_ha"
// CHECK: "comp.fa"() {instance_name = "ct_c1_fa"
// CHECK: "comp.ha"() {instance_name = "ct_c2_ha"
// CHECK-NOT: "arith.compressor_tree"()
"builtin.module"() ({
  "arith.compressor_tree"() {reduction_type = "dadda", columns = ["c0=A[0],B[0]", "c1=pp_0_1,pp_1_0,C[0]", "c2=pp_0_2,pp_1_1"], owner = "arith.compressor_tree"} : () -> ()
}) : () -> ()
