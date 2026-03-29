// RUN: compiler-opt --pass lower-multiplier-to-arith-parts
// CHECK: "arith.partial_product_generator"(%0, %1)
// CHECK: !rtl.wire<"A":16>
// CHECK: !rtl.wire<"B":16>
// CHECK: !rtl.wire<"pp_0_0":1>
// CHECK: "arith.compressor_tree"(
// CHECK: implementation = #arith.compressor_impl<dadda>
// CHECK: !rtl.wire<"C":32>
// CHECK: !rtl.wire<"ct_lhs":32>
// CHECK: "arith.prefix_tree"(
// CHECK: implementation = #arith.prefix_impl<kogge_stone>
// CHECK: !rtl.wire<"D":32>
// CHECK-NOT: "arith.multiplier"()
"builtin.module"() ({
  "func.func"() ({
  ^bb0(%0: !rtl.wire<"A":16>, %1: !rtl.wire<"B":16>, %2: !rtl.wire<"C":32>):
    %3 = "arith.multiplier"(%0, %1, %2) {implementation = #arith.multiplier_impl<array>} : (!rtl.wire<"A":16>, !rtl.wire<"B":16>, !rtl.wire<"C":32>) -> !rtl.wire<"D":32>
    "func.return"(%3) : (!rtl.wire<"D":32>) -> ()
  }) {sym_name = "mac16x16p32", function_type = (!rtl.wire<"A":16>, !rtl.wire<"B":16>, !rtl.wire<"C":32>) -> !rtl.wire<"D":32>} : () -> ()
}) : () -> ()
