// RUN: compiler-opt --pass lower-logic-to-asap7 --pass verify-post-logic-to-physical
// CHECK: instance_name = "pt_b0_xor_p"
// CHECK: instance_name = "pt_b0_and_g"
// CHECK: instance_name = "pt_s0_ao21_g_1"
// CHECK-NOT: "logic.xor2"()
// CHECK-NOT: "logic.and2"()
// CHECK-NOT: "logic.ao21"()
"builtin.module"() ({
  "func.func"() ({
  ^bb0(%0: !rtl.wire<"A[0]":1>, %1: !rtl.wire<"B[0]":1>, %2: !rtl.wire<"pt_p_1":1>, %3: !rtl.wire<"pt_g_0":1>, %4: !rtl.wire<"pt_g_1":1>):
    %5 = "logic.xor2"(%0, %1) {instance_name = "pt_b0_xor_p"} : (!rtl.wire<"A[0]":1>, !rtl.wire<"B[0]":1>) -> !rtl.wire<"pt_p_0":1>
    %6 = "logic.and2"(%0, %1) {instance_name = "pt_b0_and_g"} : (!rtl.wire<"A[0]":1>, !rtl.wire<"B[0]":1>) -> !rtl.wire<"pt_g_0":1>
    %7 = "logic.ao21"(%2, %3, %4) {instance_name = "pt_s0_ao21_g_1"} : (!rtl.wire<"pt_p_1":1>, !rtl.wire<"pt_g_0":1>, !rtl.wire<"pt_g_1":1>) -> !rtl.wire<"pt_s0_g_1":1>
    "func.return"(%5, %6, %7) : (!rtl.wire<"pt_p_0":1>, !rtl.wire<"pt_g_0":1>, !rtl.wire<"pt_s0_g_1":1>) -> ()
  }) {logic.region_kind = "arith.prefix_tree", sym_name = "pt", function_type = (!rtl.wire<"A[0]":1>, !rtl.wire<"B[0]":1>, !rtl.wire<"pt_p_1":1>, !rtl.wire<"pt_g_0":1>, !rtl.wire<"pt_g_1":1>) -> (!rtl.wire<"pt_p_0":1>, !rtl.wire<"pt_g_0":1>, !rtl.wire<"pt_s0_g_1":1>), sym_visibility = "private"} : () -> ()
}) : () -> ()
