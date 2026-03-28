// RUN: compiler-opt --pass lower-multiplier-to-arith-parts
// CHECK: "arith.partial_product_generator"()
// CHECK: terms = ["pp_0_0=A[0],B[0]"
// CHECK: "arith.compressor_tree"()
// CHECK: reduction_type = "dadda"
// CHECK: "arith.prefix_tree"()
// CHECK: output_name = "D"
// CHECK-NOT: "arith.multiplier"()
"builtin.module"() ({
  "arith.multiplier"() {implementation = "array"} : () -> ()
}) {func_name = "mac16x16p32", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]} : () -> ()
