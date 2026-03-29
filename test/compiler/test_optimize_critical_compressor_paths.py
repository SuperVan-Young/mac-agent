from __future__ import annotations

from xdsl.dialects.func import FuncOp

from rtl.compiler.analysis import analyze_module_timing, load_default_liberty_model
from rtl.compiler.passes.optimize_critical_compressor_paths import OptimizeCriticalCompressorPathsPass
from rtl.compiler.pipeline import build_context, parse_module


def test_critical_compressor_rebinds_latest_input_to_cin() -> None:
    module = parse_module(
        """
"builtin.module"() ({
  "func.func"() ({
  ^bb0(%0: !rtl.wire<"X":1>, %1: !rtl.wire<"B":1>, %2: !rtl.wire<"C":1>, %3: !rtl.wire<"D":1>, %4: !rtl.wire<"SKEW_SEED":1>):
    %5 = "logic.instance"(%0, %4) {instance_name = "skew_stage_0_inst", callee = "skew_stage_0"} : (!rtl.wire<"X":1>, !rtl.wire<"SKEW_SEED":1>) -> !rtl.wire<"A":1>
    %6, %7 = "logic.instance"(%5, %1, %2, %3) {instance_name = "compressor_tree_0_inst", callee = "compressor_tree_0"} : (!rtl.wire<"A":1>, !rtl.wire<"B":1>, !rtl.wire<"C":1>, !rtl.wire<"D":1>) -> (!rtl.wire<"SUM":1>, !rtl.wire<"CARRY":1>)
    %8 = "logic.instance"(%6, %7) {instance_name = "prefix_tree_0_inst", callee = "prefix_tree_0"} : (!rtl.wire<"SUM":1>, !rtl.wire<"CARRY":1>) -> !rtl.wire<"Y":1>
    "func.return"(%8) : (!rtl.wire<"Y":1>) -> ()
  }) {sym_name = "top", function_type = (!rtl.wire<"X":1>, !rtl.wire<"B":1>, !rtl.wire<"C":1>, !rtl.wire<"D":1>, !rtl.wire<"SKEW_SEED":1>) -> !rtl.wire<"Y":1>} : () -> ()
  "func.func"() ({
  ^bb0(%9: !rtl.wire<"X":1>, %10: !rtl.wire<"Y":1>):
    %11 = "asap7.xor2"(%9, %10) {instance_name = "sk0", cell = "XOR2x2_ASAP7_75t_R", owner = "skew_stage"} : (!rtl.wire<"X":1>, !rtl.wire<"Y":1>) -> !rtl.wire<"n0":1>
    %12 = "asap7.xor2"(%11, %10) {instance_name = "sk1", cell = "XOR2x2_ASAP7_75t_R", owner = "skew_stage"} : (!rtl.wire<"n0":1>, !rtl.wire<"Y":1>) -> !rtl.wire<"n1":1>
    %13 = "asap7.xor2"(%12, %10) {instance_name = "sk2", cell = "XOR2x2_ASAP7_75t_R", owner = "skew_stage"} : (!rtl.wire<"n1":1>, !rtl.wire<"Y":1>) -> !rtl.wire<"A":1>
    "func.return"(%13) : (!rtl.wire<"A":1>) -> ()
  }) {logic.region_kind = "skew_stage", sym_name = "skew_stage_0", function_type = (!rtl.wire<"X":1>, !rtl.wire<"Y":1>) -> !rtl.wire<"A":1>, sym_visibility = "private"} : () -> ()
  "func.func"() ({
  ^bb0(%14: !rtl.wire<"A":1>, %15: !rtl.wire<"B":1>, %16: !rtl.wire<"C":1>, %17: !rtl.wire<"D":1>):
    %18 = "asap7.xor2"(%14, %15) {instance_name = "fa0_xor_ab", cell = "XOR2x2_ASAP7_75t_R", owner = "compressor_tree"} : (!rtl.wire<"A":1>, !rtl.wire<"B":1>) -> !rtl.wire<"fa0_ab_xor":1>
    %19 = "asap7.xor2"(%18, %16) {instance_name = "fa0_xor_sum", cell = "XOR2x2_ASAP7_75t_R", owner = "compressor_tree"} : (!rtl.wire<"fa0_ab_xor":1>, !rtl.wire<"C":1>) -> !rtl.wire<"SUM":1>
    %20 = "asap7.and2"(%14, %15) {instance_name = "fa0_and_ab", cell = "AND2x2_ASAP7_75t_R", owner = "compressor_tree"} : (!rtl.wire<"A":1>, !rtl.wire<"B":1>) -> !rtl.wire<"fa0_ab_and":1>
    %21 = "asap7.ao21"(%18, %16, %20) {instance_name = "fa0_ao21_carry", cell = "AO21x2_ASAP7_75t_R", owner = "compressor_tree"} : (!rtl.wire<"fa0_ab_xor":1>, !rtl.wire<"C":1>, !rtl.wire<"fa0_ab_and":1>) -> !rtl.wire<"CARRY":1>
    "func.return"(%19, %21) : (!rtl.wire<"SUM":1>, !rtl.wire<"CARRY":1>) -> ()
  }) {logic.region_kind = "arith.compressor_tree", sym_name = "compressor_tree_0", function_type = (!rtl.wire<"A":1>, !rtl.wire<"B":1>, !rtl.wire<"C":1>, !rtl.wire<"D":1>) -> (!rtl.wire<"SUM":1>, !rtl.wire<"CARRY":1>), sym_visibility = "private"} : () -> ()
  "func.func"() ({
  ^bb0(%22: !rtl.wire<"SUM":1>, %23: !rtl.wire<"CARRY":1>):
    %24 = "asap7.xor2"(%22, %22) {instance_name = "pref0", cell = "XOR2x2_ASAP7_75t_R", owner = "prefix_tree"} : (!rtl.wire<"SUM":1>, !rtl.wire<"SUM":1>) -> !rtl.wire<"n0":1>
    %25 = "asap7.xor2"(%24, %22) {instance_name = "pref1", cell = "XOR2x2_ASAP7_75t_R", owner = "prefix_tree"} : (!rtl.wire<"n0":1>, !rtl.wire<"SUM":1>) -> !rtl.wire<"n1":1>
    %26 = "asap7.xor2"(%25, %23) {instance_name = "pref2", cell = "XOR2x2_ASAP7_75t_R", owner = "prefix_tree"} : (!rtl.wire<"n1":1>, !rtl.wire<"CARRY":1>) -> !rtl.wire<"Y":1>
    "func.return"(%26) : (!rtl.wire<"Y":1>) -> ()
  }) {logic.region_kind = "arith.prefix_tree", sym_name = "prefix_tree_0", function_type = (!rtl.wire<"SUM":1>, !rtl.wire<"CARRY":1>) -> !rtl.wire<"Y":1>, sym_visibility = "private"} : () -> ()
}) : () -> ()
""".strip()
    )

    analysis = analyze_module_timing(module, load_default_liberty_model())
    report = analysis.func_reports["compressor_tree_0"]
    assert report.signal_arrivals_ns["A"] > report.signal_arrivals_ns["B"]
    assert report.signal_arrivals_ns["A"] > report.signal_arrivals_ns["C"]

    OptimizeCriticalCompressorPathsPass().apply(build_context(), module)

    compressor = next(op for op in module.ops if isinstance(op, FuncOp) and op.sym_name.data == "compressor_tree_0")
    ops_by_name = {op.instance_name.data: op for op in compressor.body.block.ops if hasattr(op, "instance_name")}
    input_a = compressor.args[0]
    assert ops_by_name["fa0_xor_sum"].rhs is input_a
    assert ops_by_name["fa0_ao21_carry"].and_rhs is input_a
