// RUN: compiler-opt --pass lower-multiplier-to-arith-parts --pass lower-arith-to-logic --pass verify-post-arith-to-logic --pass lower-logic-to-asap7 --pass verify-post-logic-to-physical --pass emit-verilog
// CHECK: module mac16x16p32(A, B, C, D);
// CHECK: AND2x2_ASAP7_75t_R ppg_and2_0
// CHECK: XOR2x2_ASAP7_75t_R pt_b0_fa_xor_ab
// CHECK: OR2x2_ASAP7_75t_R pt_b0_fa_or_carry
// CHECK: XOR2x2_ASAP7_75t_R pt_b31_fa_xor_sum
// CHECK-NOT: assign D =
"builtin.module"() ({
  "arith.multiplier"() {implementation = "array"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]} : () -> ()
