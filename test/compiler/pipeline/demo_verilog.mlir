// RUN: compiler-opt --pass lower-arith-to-logic --pass verify-post-arith-to-logic --pass lower-logic-to-asap7 --pass verify-post-logic-to-physical --pass emit-verilog
// CHECK: module mac16x16p32(A, B, C, D);
// CHECK: HAxp5_ASAP7_75t_R ct_c0_ha
// CHECK: FAx1_ASAP7_75t_R ct_c1_fa
// CHECK: assign D = C;
"builtin.module"() ({
  "arith.compressor_tree"() {reduction_type = "dadda", columns = ["c0=A[0],B[0]", "c1=pp_0_1,pp_1_0,C[0]", "c2=pp_0_2,pp_1_1"], owner = "arith.compressor_tree"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]} : () -> ()
