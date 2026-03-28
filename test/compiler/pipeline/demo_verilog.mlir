// RUN: compiler-opt --pass lower-multiplier-to-arith-parts --pass lower-arith-to-logic --pass verify-post-arith-to-logic --pass lower-logic-to-asap7 --pass region-scoped-cell-sizing --pass verify-post-logic-to-physical --pass emit-verilog
// CHECK: module mac16x16p32(A, B, C, D);
// CHECK: mac16x16p32__partial_product_generator_0 partial_product_generator_0_inst(.A(A), .B(B)
// CHECK: mac16x16p32__compressor_tree_0 compressor_tree_0_inst(
// CHECK: mac16x16p32__prefix_tree_0 prefix_tree_0_inst(
// CHECK: module mac16x16p32__partial_product_generator_0(A, B
// CHECK: AND2x2_ASAP7_75t_R ppg_and2_0
// CHECK: module mac16x16p32__prefix_tree_0(
// CHECK: AO21x1_ASAP7_75t_R pt_s0_ao21_g_1
// CHECK: XOR2xp5_ASAP7_75t_R pt_b31_xor_sum
// CHECK-NOT: assign D =
"builtin.module"() ({
  "arith.multiplier"() {implementation = "array"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]} : () -> ()
