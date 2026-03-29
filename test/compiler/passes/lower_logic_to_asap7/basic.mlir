// RUN: compiler-opt --pass lower-logic-to-asap7 --pass verify-post-logic-to-physical
// CHECK: instance_name = "ppg_and2_0"
// CHECK: instance_name = "ct_demo_ha_xor"
// CHECK: instance_name = "ct_demo_ha_and"
// CHECK: instance_name = "ct_demo_fa_xor_ab"
// CHECK: instance_name = "ct_demo_fa_ao21_carry"
// CHECK-NOT: "logic.full_adder"()
// CHECK-NOT: "logic.half_adder"()
"builtin.module"() ({
  %0 = "logic.input"() : () -> !rtl.wire<"A[0]":1>
  %1 = "logic.input"() : () -> !rtl.wire<"B[0]":1>
  %2 = "logic.input"() : () -> !rtl.wire<"pp_0_1":1>
  %3 = "logic.input"() : () -> !rtl.wire<"pp_1_0":1>
  %4 = "logic.input"() : () -> !rtl.wire<"pp_0_2":1>
  %5 = "logic.input"() : () -> !rtl.wire<"pp_1_1":1>
  %6 = "logic.input"() : () -> !rtl.wire<"C[2]":1>
  %7 = "logic.and2"(%0, %1) {instance_name = "ppg_and2_0", region_kind = "partial_product_generator"} : (!rtl.wire<"A[0]":1>, !rtl.wire<"B[0]":1>) -> !rtl.wire<"pp_0_0":1>
  %8, %9 = "logic.half_adder"(%2, %3) {instance_name = "ct_demo_ha", region_kind = "compressor_tree"} : (!rtl.wire<"pp_0_1":1>, !rtl.wire<"pp_1_0":1>) -> (!rtl.wire<"ct_c1_sum":1>, !rtl.wire<"ct_c2_carry":1>)
  %10, %11 = "logic.full_adder"(%4, %5, %6) {instance_name = "ct_demo_fa", region_kind = "compressor_tree"} : (!rtl.wire<"pp_0_2":1>, !rtl.wire<"pp_1_1":1>, !rtl.wire<"C[2]":1>) -> (!rtl.wire<"ct_c2_sum":1>, !rtl.wire<"ct_c3_carry":1>)
}) {func_name = "mac16x16p32", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]} : () -> ()
