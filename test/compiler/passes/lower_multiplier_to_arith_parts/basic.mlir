// RUN: compiler-opt --pass lower-multiplier-to-arith-parts
// CHECK: "logic.input"() : () -> !rtl.wire<"A[0]":1>
// CHECK: "arith.partial_product_generator"(
// CHECK: !rtl.wire<"pp_0_0":1>
// CHECK: "arith.compressor_tree"(
// CHECK: implementation = "dadda"
// CHECK: !rtl.wire<"ct_lhs":32>
// CHECK: "arith.prefix_tree"(
// CHECK: implementation = "kogge_stone"
// CHECK: !rtl.wire<"D":32>
// CHECK-NOT: "arith.multiplier"()
"builtin.module"() ({
  "arith.multiplier"() {implementation = "array"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]} : () -> ()
