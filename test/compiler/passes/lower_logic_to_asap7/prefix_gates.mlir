// RUN: compiler-opt --pass lower-logic-to-asap7 --pass verify-post-logic-to-physical
// CHECK: instance_name = "pt_b0_xor_p"
// CHECK: instance_name = "pt_b0_and_g"
// CHECK: instance_name = "pt_s0_ao21_g_1"
// CHECK-NOT: "logic.xor2"()
// CHECK-NOT: "logic.and2"()
// CHECK-NOT: "logic.ao21"()
"builtin.module"() ({
  %0 = "logic.input"() {port_name = "A[0]"} : () -> !rtl.wire<1>
  %1 = "logic.input"() {port_name = "B[0]"} : () -> !rtl.wire<1>
  %2 = "logic.input"() {port_name = "pt_p_1"} : () -> !rtl.wire<1>
  %3 = "logic.input"() {port_name = "pt_g_0"} : () -> !rtl.wire<1>
  %4 = "logic.input"() {port_name = "pt_g_1"} : () -> !rtl.wire<1>
  %5 = "logic.xor2"(%0, %1) {instance_name = "pt_b0_xor_p", region_kind = "prefix_tree", output_name = "pt_p_0"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
  %6 = "logic.and2"(%0, %1) {instance_name = "pt_b0_and_g", region_kind = "prefix_tree", output_name = "pt_g_0"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
  %7 = "logic.ao21"(%2, %3, %4) {instance_name = "pt_s0_ao21_g_1", region_kind = "prefix_tree", output_name = "pt_s0_g_1"} : (!rtl.wire<1>, !rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
}) {func_name = "mac16x16p32", input_ports = ["input:A:4", "input:B:4"], output_ports = ["output:D:4"]} : () -> ()
