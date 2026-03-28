// RUN: compiler-opt --pass lower-arith-to-logic --pass lower-logic-to-asap7 --pass emit-verilog
// CHECK: module mac16x16p32(A, B, C, D);
// CHECK: HAxp5_ASAP7_75t_R ct_c0_ha
// CHECK: FAx1_ASAP7_75t_R ct_c1_fa
// CHECK: assign D = C;
"builtin.module"() ({
  "arith.compressor_tree"() {reduction_type = "dadda", columns = ["c0=A[0],B[0]", "c1=pp_0_1,pp_1_0,C[0]", "c2=pp_0_2,pp_1_1"], owner = "arith.compressor_tree"} : () -> ()
}) : () -> ()
