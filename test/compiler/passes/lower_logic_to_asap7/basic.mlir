// RUN: compiler-opt --pass lower-logic-to-asap7 --pass verify-post-logic-to-physical
// CHECK: instance_name = "ppg_and2_0"
// CHECK: instance_name = "ct_demo_ha_xor"
// CHECK: instance_name = "ct_demo_ha_and"
// CHECK: instance_name = "ct_demo_fa_xor_ab"
// CHECK: instance_name = "ct_demo_fa_ao21_carry"
// CHECK-NOT: "logic.full_adder"()
// CHECK-NOT: "logic.half_adder"()
"builtin.module"() ({
  "func.func"() ({
  ^bb0(%0: !rtl.wire<"A[0]":1>, %1: !rtl.wire<"B[0]":1>):
    %2 = "logic.and2"(%0, %1) {instance_name = "ppg_and2_0"} : (!rtl.wire<"A[0]":1>, !rtl.wire<"B[0]":1>) -> !rtl.wire<"pp_0_0":1>
    "func.return"(%2) : (!rtl.wire<"pp_0_0":1>) -> ()
  }) {logic.region_kind = "arith.partial_product_generator", sym_name = "ppg", function_type = (!rtl.wire<"A[0]":1>, !rtl.wire<"B[0]":1>) -> !rtl.wire<"pp_0_0":1>, sym_visibility = "private"} : () -> ()
  "func.func"() ({
  ^bb0(%3: !rtl.wire<"pp_0_1":1>, %4: !rtl.wire<"pp_1_0":1>, %5: !rtl.wire<"pp_0_2":1>, %6: !rtl.wire<"pp_1_1":1>, %7: !rtl.wire<"C[2]":1>):
    %8, %9 = "logic.half_adder"(%3, %4) {instance_name = "ct_demo_ha"} : (!rtl.wire<"pp_0_1":1>, !rtl.wire<"pp_1_0":1>) -> (!rtl.wire<"ct_c1_sum":1>, !rtl.wire<"ct_c2_carry":1>)
    %10, %11 = "logic.full_adder"(%5, %6, %7) {instance_name = "ct_demo_fa"} : (!rtl.wire<"pp_0_2":1>, !rtl.wire<"pp_1_1":1>, !rtl.wire<"C[2]":1>) -> (!rtl.wire<"ct_c2_sum":1>, !rtl.wire<"ct_c3_carry":1>)
    "func.return"(%8, %9, %10, %11) : (!rtl.wire<"ct_c1_sum":1>, !rtl.wire<"ct_c2_carry":1>, !rtl.wire<"ct_c2_sum":1>, !rtl.wire<"ct_c3_carry":1>) -> ()
  }) {logic.region_kind = "arith.compressor_tree", sym_name = "ct", function_type = (!rtl.wire<"pp_0_1":1>, !rtl.wire<"pp_1_0":1>, !rtl.wire<"pp_0_2":1>, !rtl.wire<"pp_1_1":1>, !rtl.wire<"C[2]":1>) -> (!rtl.wire<"ct_c1_sum":1>, !rtl.wire<"ct_c2_carry":1>, !rtl.wire<"ct_c2_sum":1>, !rtl.wire<"ct_c3_carry":1>), sym_visibility = "private"} : () -> ()
}) : () -> ()
