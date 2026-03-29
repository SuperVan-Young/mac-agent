// RUN: compiler-opt --pass lower-multiplier-to-arith-parts --pass lower-arith-to-logic --pass verify-post-arith-to-logic --pass lower-logic-to-asap7 --pass annotate-func-port-criticality --pass region-scoped-cell-sizing --pass verify-post-logic-to-physical --pass emit-verilog
// CHECK: module mac16x16p32(A, B, C, D);
// CHECK: AND2x2_ASAP7_75t_R ppg_and2_0
// CHECK: AO21x1_ASAP7_75t_R pt_s0_ao21_g_31
// CHECK: XOR2xp5_ASAP7_75t_R pt_b0_xor_sum
// CHECK: XOR2x2_ASAP7_75t_R pt_b31_xor_sum
// CHECK-NOT: assign D =
"builtin.module"() ({
  "func.func"() ({
  ^bb0(%0: !rtl.wire<"A":16>, %1: !rtl.wire<"B":16>, %2: !rtl.wire<"C":32>):
    %3 = "arith.multiplier"(%0, %1, %2) {implementation = #arith.multiplier_impl<array>} : (!rtl.wire<"A":16>, !rtl.wire<"B":16>, !rtl.wire<"C":32>) -> !rtl.wire<"D":32>
    "func.return"(%3) : (!rtl.wire<"D":32>) -> ()
  }) {sym_name = "mac16x16p32", function_type = (!rtl.wire<"A":16>, !rtl.wire<"B":16>, !rtl.wire<"C":32>) -> !rtl.wire<"D":32>} : () -> ()
}) : () -> ()
