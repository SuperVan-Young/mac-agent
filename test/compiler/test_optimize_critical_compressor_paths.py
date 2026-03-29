from __future__ import annotations

from xdsl.dialects.func import FuncOp

from rtl.compiler.analysis import analyze_module_timing, load_default_liberty_model
from rtl.compiler.passes.optimize_critical_compressor_paths import OptimizeCriticalCompressorPathsPass
from rtl.compiler.pipeline import build_context, parse_module


def test_critical_compressor_rebinds_latest_input_to_cin() -> None:
    module = parse_module(
        """
"builtin.module"() ({
  %0 = "logic.input"() : () -> !rtl.wire<"X":1>
  %1 = "logic.input"() : () -> !rtl.wire<"B":1>
  %2 = "logic.input"() : () -> !rtl.wire<"C":1>
  %3 = "logic.input"() : () -> !rtl.wire<"D":1>
  %4 = "logic.input"() : () -> !rtl.wire<"SKEW_SEED":1>
  %5 = "logic.instance"(%0, %4) {instance_name = "skew_stage_0_inst", callee = "skew_stage_0", region_kind = "skew_stage", input_ports = ["X", "Y"], output_ports = ["A"]} : (!rtl.wire<"X":1>, !rtl.wire<"SKEW_SEED":1>) -> !rtl.wire<"A":1>
  %6, %7 = "logic.instance"(%5, %1, %2, %3) {instance_name = "compressor_tree_0_inst", callee = "compressor_tree_0", region_kind = "arith.compressor_tree", input_ports = ["A", "B", "C", "D"], output_ports = ["SUM", "CARRY"]} : (!rtl.wire<"A":1>, !rtl.wire<"B":1>, !rtl.wire<"C":1>, !rtl.wire<"D":1>) -> (!rtl.wire<"SUM":1>, !rtl.wire<"CARRY":1>)
  %8 = "logic.instance"(%6, %7) {instance_name = "prefix_tree_0_inst", callee = "prefix_tree_0", region_kind = "arith.prefix_tree", input_ports = ["SUM", "CARRY"], output_ports = ["Y"]} : (!rtl.wire<"SUM":1>, !rtl.wire<"CARRY":1>) -> !rtl.wire<"Y":1>
  "func.func"() ({
    %9 = "logic.input"() : () -> !rtl.wire<"X":1>
    %10 = "logic.input"() : () -> !rtl.wire<"Y":1>
    %11 = "asap7.xor2"(%9, %10) {instance_name = "sk0", cell = "XOR2x2_ASAP7_75t_R", owner = "skew_stage"} : (!rtl.wire<"X":1>, !rtl.wire<"Y":1>) -> !rtl.wire<"n0":1>
    %12 = "asap7.xor2"(%11, %10) {instance_name = "sk1", cell = "XOR2x2_ASAP7_75t_R", owner = "skew_stage"} : (!rtl.wire<"n0":1>, !rtl.wire<"Y":1>) -> !rtl.wire<"n1":1>
    %13 = "asap7.xor2"(%12, %10) {instance_name = "sk2", cell = "XOR2x2_ASAP7_75t_R", owner = "skew_stage"} : (!rtl.wire<"n1":1>, !rtl.wire<"Y":1>) -> !rtl.wire<"A":1>
    "logic.output"(%13) : (!rtl.wire<"A":1>) -> ()
    "func.return"() : () -> ()
  }) {logic.input_ports = ["input:X:1", "input:Y:1"], logic.output_ports = ["output:A:1"], logic.region_kind = "skew_stage", sym_name = "skew_stage_0", function_type = () -> (), sym_visibility = "private"} : () -> ()
  "func.func"() ({
    %14 = "logic.input"() : () -> !rtl.wire<"A":1>
    %15 = "logic.input"() : () -> !rtl.wire<"B":1>
    %16 = "logic.input"() : () -> !rtl.wire<"C":1>
    %17 = "logic.input"() : () -> !rtl.wire<"D":1>
    %18 = "asap7.xor2"(%14, %15) {instance_name = "fa0_xor_ab", cell = "XOR2x2_ASAP7_75t_R", owner = "compressor_tree"} : (!rtl.wire<"A":1>, !rtl.wire<"B":1>) -> !rtl.wire<"fa0_ab_xor":1>
    %19 = "asap7.xor2"(%18, %16) {instance_name = "fa0_xor_sum", cell = "XOR2x2_ASAP7_75t_R", owner = "compressor_tree"} : (!rtl.wire<"fa0_ab_xor":1>, !rtl.wire<"C":1>) -> !rtl.wire<"SUM":1>
    %20 = "asap7.and2"(%14, %15) {instance_name = "fa0_and_ab", cell = "AND2x2_ASAP7_75t_R", owner = "compressor_tree"} : (!rtl.wire<"A":1>, !rtl.wire<"B":1>) -> !rtl.wire<"fa0_ab_and":1>
    %21 = "asap7.ao21"(%18, %16, %20) {instance_name = "fa0_ao21_carry", cell = "AO21x2_ASAP7_75t_R", owner = "compressor_tree"} : (!rtl.wire<"fa0_ab_xor":1>, !rtl.wire<"C":1>, !rtl.wire<"fa0_ab_and":1>) -> !rtl.wire<"CARRY":1>
    "logic.output"(%19) : (!rtl.wire<"SUM":1>) -> ()
    "logic.output"(%21) : (!rtl.wire<"CARRY":1>) -> ()
    "func.return"() : () -> ()
  }) {logic.input_ports = ["input:A:1", "input:B:1", "input:C:1", "input:D:1"], logic.output_ports = ["output:SUM:1", "output:CARRY:1"], logic.region_kind = "arith.compressor_tree", sym_name = "compressor_tree_0", function_type = () -> (), sym_visibility = "private"} : () -> ()
  "func.func"() ({
    %22 = "logic.input"() : () -> !rtl.wire<"SUM":1>
    %23 = "logic.input"() : () -> !rtl.wire<"CARRY":1>
    %24 = "asap7.xor2"(%22, %22) {instance_name = "pref0", cell = "XOR2x2_ASAP7_75t_R", owner = "prefix_tree"} : (!rtl.wire<"SUM":1>, !rtl.wire<"SUM":1>) -> !rtl.wire<"n0":1>
    %25 = "asap7.xor2"(%24, %22) {instance_name = "pref1", cell = "XOR2x2_ASAP7_75t_R", owner = "prefix_tree"} : (!rtl.wire<"n0":1>, !rtl.wire<"SUM":1>) -> !rtl.wire<"n1":1>
    %26 = "asap7.xor2"(%25, %23) {instance_name = "pref2", cell = "XOR2x2_ASAP7_75t_R", owner = "prefix_tree"} : (!rtl.wire<"n1":1>, !rtl.wire<"CARRY":1>) -> !rtl.wire<"Y":1>
    "logic.output"(%26) : (!rtl.wire<"Y":1>) -> ()
    "func.return"() : () -> ()
  }) {logic.input_ports = ["input:SUM:1", "input:CARRY:1"], logic.output_ports = ["output:Y:1"], logic.region_kind = "arith.prefix_tree", sym_name = "prefix_tree_0", function_type = () -> (), sym_visibility = "private"} : () -> ()
}) {func_name = "top", input_ports = ["input:X:1", "input:B:1", "input:C:1", "input:D:1", "input:SKEW_SEED:1"], output_ports = ["output:Y:1"]} : () -> ()
""".strip()
    )

    analysis = analyze_module_timing(module, load_default_liberty_model())
    report = analysis.func_reports["compressor_tree_0"]
    assert report.signal_arrivals_ns["A"] > report.signal_arrivals_ns["B"]
    assert report.signal_arrivals_ns["A"] > report.signal_arrivals_ns["C"]

    OptimizeCriticalCompressorPathsPass().apply(build_context(), module)

    compressor = next(op for op in module.ops if isinstance(op, FuncOp) and op.sym_name.data == "compressor_tree_0")
    ops_by_name = {op.instance_name.data: op for op in compressor.body.block.ops if hasattr(op, "instance_name")}
    input_a = next(op for op in compressor.body.block.ops if op.name == "logic.input" and op.output.type.wire_name.data == "A")
    assert ops_by_name["fa0_xor_sum"].rhs.owner is input_a
    assert ops_by_name["fa0_ao21_carry"].and_rhs.owner is input_a
