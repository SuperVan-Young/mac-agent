// RUN: compiler-opt --pass lower-arith-to-logic --pass verify-post-arith-to-logic
// CHECK: "logic.instance"() {instance_name = "compressor_tree_0_inst"
// CHECK: callee = "mac16x16p32__compressor_tree_0"
// CHECK: "func.func"() ({
// CHECK: "logic.half_adder"() {instance_name = "ct_demo_ha"
// CHECK: region_kind = "compressor_tree"
// CHECK: "logic.full_adder"() {instance_name = "ct_demo_fa"
// CHECK: logic.region_kind = "arith.compressor_tree"
// CHECK: sym_name = "mac16x16p32__compressor_tree_0"
// CHECK: sym_visibility = "private"
// CHECK-NOT: "arith.compressor_tree"()
"builtin.module"() ({
  "arith.compressor_tree"() {reduction_type = "dadda", columns = ["c1=pp_0_1,pp_1_0", "c2=pp_0_2,pp_1_1,C[2]"], stages = ["ha:ct_demo_ha:pp_0_1:pp_1_0::ct_c1_sum:ct_c2_carry", "fa:ct_demo_fa:pp_0_2:pp_1_1:C[2]:ct_c2_sum:ct_c3_carry"], owner = "arith.compressor_tree"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]} : () -> ()
