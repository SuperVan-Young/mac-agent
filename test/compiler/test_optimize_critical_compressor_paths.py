from __future__ import annotations

from xdsl.dialects.func import FuncOp

from rtl.compiler.analysis import analyze_module_timing, load_default_liberty_model
from rtl.compiler.passes.optimize_critical_compressor_paths import (
    OptimizeCriticalCompressorPathsPass,
)
from rtl.compiler.pipeline import build_context, parse_module


def test_critical_compressor_rebinds_latest_input_to_cin() -> None:
    module = parse_module(
        """
"builtin.module"() ({
  "logic.instance"() {instance_name = "skew_stage_0_inst", callee = "skew_stage_0", input_connections = ["X=X", "Y=SKEW_SEED"], output_connections = ["A_SKEW=A_SKEW"]} : () -> ()
  "logic.instance"() {instance_name = "compressor_tree_0_inst", callee = "compressor_tree_0", input_connections = ["A=A_SKEW", "B=B", "C=C", "D=D"], output_connections = ["SUM=sum_out", "CARRY=carry_out"]} : () -> ()
  "logic.instance"() {instance_name = "prefix_tree_0_inst", callee = "prefix_tree_0", input_connections = ["SUM=sum_out", "CARRY=carry_out"], output_connections = ["Y=Y"]} : () -> ()
  "func.func"() ({
    %0 = "logic.input"() {port_name = "X"} : () -> !rtl.wire<1>
    %1 = "logic.input"() {port_name = "Y"} : () -> !rtl.wire<1>
    %2 = "asap7.xor2"(%0, %1) {instance_name = "sk0", cell = "XOR2x2_ASAP7_75t_R", output_name = "n0", owner = "skew_stage"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %3 = "asap7.xor2"(%2, %1) {instance_name = "sk1", cell = "XOR2x2_ASAP7_75t_R", output_name = "n1", owner = "skew_stage"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %4 = "asap7.xor2"(%3, %1) {instance_name = "sk2", cell = "XOR2x2_ASAP7_75t_R", output_name = "A_SKEW", owner = "skew_stage"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    "logic.output"(%4) {port_name = "A_SKEW"} : (!rtl.wire<1>) -> ()
    "func.return"() : () -> ()
  }) {logic.input_ports = ["input:X:1", "input:Y:1"], logic.output_ports = ["output:A_SKEW:1"], logic.region_kind = "skew_stage", sym_name = "skew_stage_0", function_type = () -> (), sym_visibility = "private"} : () -> ()
  "func.func"() ({
    %5 = "logic.input"() {port_name = "A"} : () -> !rtl.wire<1>
    %6 = "logic.input"() {port_name = "B"} : () -> !rtl.wire<1>
    %7 = "logic.input"() {port_name = "C"} : () -> !rtl.wire<1>
    %8 = "logic.input"() {port_name = "D"} : () -> !rtl.wire<1>
    %9 = "asap7.xor2"(%5, %6) {instance_name = "fa0_xor_ab", cell = "XOR2x2_ASAP7_75t_R", output_name = "fa0_ab_xor", owner = "compressor_tree"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %10 = "asap7.xor2"(%9, %7) {instance_name = "fa0_xor_sum", cell = "XOR2x2_ASAP7_75t_R", output_name = "SUM", owner = "compressor_tree"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %11 = "asap7.and2"(%5, %6) {instance_name = "fa0_and_ab", cell = "AND2x2_ASAP7_75t_R", output_name = "fa0_ab_and", owner = "compressor_tree"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %12 = "asap7.ao21"(%9, %7, %11) {instance_name = "fa0_ao21_carry", cell = "AO21x2_ASAP7_75t_R", output_name = "CARRY", owner = "compressor_tree"} : (!rtl.wire<1>, !rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    "logic.output"(%10) {port_name = "SUM"} : (!rtl.wire<1>) -> ()
    "logic.output"(%12) {port_name = "CARRY"} : (!rtl.wire<1>) -> ()
    "func.return"() : () -> ()
  }) {logic.input_ports = ["input:A:1", "input:B:1", "input:C:1", "input:D:1"], logic.output_ports = ["output:SUM:1", "output:CARRY:1"], logic.region_kind = "arith.compressor_tree", sym_name = "compressor_tree_0", function_type = () -> (), sym_visibility = "private"} : () -> ()
  "func.func"() ({
    %13 = "logic.input"() {port_name = "SUM"} : () -> !rtl.wire<1>
    %14 = "logic.input"() {port_name = "CARRY"} : () -> !rtl.wire<1>
    %15 = "logic.input"() {port_name = "D"} : () -> !rtl.wire<1>
    %16 = "asap7.xor2"(%13, %15) {instance_name = "pref0", cell = "XOR2x2_ASAP7_75t_R", output_name = "n0", owner = "prefix_tree"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %17 = "asap7.xor2"(%16, %15) {instance_name = "pref1", cell = "XOR2x2_ASAP7_75t_R", output_name = "n1", owner = "prefix_tree"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %18 = "asap7.xor2"(%17, %14) {instance_name = "pref2", cell = "XOR2x2_ASAP7_75t_R", output_name = "Y", owner = "prefix_tree"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    "logic.output"(%18) {port_name = "Y"} : (!rtl.wire<1>) -> ()
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

    compressor = next(
        op for op in module.ops if isinstance(op, FuncOp) and op.sym_name.data == "compressor_tree_0"
    )
    ops_by_name = {
        op.instance_name.data: op
        for op in compressor.body.block.ops
        if hasattr(op, "instance_name")
    }
    input_a = next(
        op for op in compressor.body.block.ops if op.name == "logic.input" and op.port_name.data == "A"
    )
    assert ops_by_name["fa0_xor_sum"].rhs.owner is input_a
    assert ops_by_name["fa0_ao21_carry"].and_rhs.owner is input_a
