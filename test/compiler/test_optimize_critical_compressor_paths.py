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
    "asap7.xor2"() {instance_name = "sk0", cell = "XOR2x2_ASAP7_75t_R", output = "n0", lhs = "X", rhs = "Y", owner = "skew_stage"} : () -> ()
    "asap7.xor2"() {instance_name = "sk1", cell = "XOR2x2_ASAP7_75t_R", output = "n1", lhs = "n0", rhs = "Y", owner = "skew_stage"} : () -> ()
    "asap7.xor2"() {instance_name = "sk2", cell = "XOR2x2_ASAP7_75t_R", output = "A_SKEW", lhs = "n1", rhs = "Y", owner = "skew_stage"} : () -> ()
  }) {logic.input_ports = ["input:X:1", "input:Y:1"], logic.output_ports = ["output:A_SKEW:1"], logic.region_kind = "skew_stage", sym_name = "skew_stage_0", function_type = () -> (), sym_visibility = "private"} : () -> ()
  "func.func"() ({
    "asap7.xor2"() {instance_name = "fa0_xor_ab", cell = "XOR2x2_ASAP7_75t_R", output = "fa0_ab_xor", lhs = "A", rhs = "B", owner = "compressor_tree"} : () -> ()
    "asap7.xor2"() {instance_name = "fa0_xor_sum", cell = "XOR2x2_ASAP7_75t_R", output = "SUM", lhs = "fa0_ab_xor", rhs = "C", owner = "compressor_tree"} : () -> ()
    "asap7.and2"() {instance_name = "fa0_and_ab", cell = "AND2x2_ASAP7_75t_R", output = "fa0_ab_and", lhs = "A", rhs = "B", owner = "compressor_tree"} : () -> ()
    "asap7.ao21"() {instance_name = "fa0_ao21_carry", cell = "AO21x2_ASAP7_75t_R", output = "CARRY", and_lhs = "fa0_ab_xor", and_rhs = "C", or_rhs = "fa0_ab_and", owner = "compressor_tree"} : () -> ()
  }) {logic.input_ports = ["input:A:1", "input:B:1", "input:C:1", "input:D:1"], logic.output_ports = ["output:SUM:1", "output:CARRY:1"], logic.region_kind = "arith.compressor_tree", sym_name = "compressor_tree_0", function_type = () -> (), sym_visibility = "private"} : () -> ()
  "func.func"() ({
    "asap7.xor2"() {instance_name = "pref0", cell = "XOR2x2_ASAP7_75t_R", output = "n0", lhs = "SUM", rhs = "D", owner = "prefix_tree"} : () -> ()
    "asap7.xor2"() {instance_name = "pref1", cell = "XOR2x2_ASAP7_75t_R", output = "n1", lhs = "n0", rhs = "D", owner = "prefix_tree"} : () -> ()
    "asap7.xor2"() {instance_name = "pref2", cell = "XOR2x2_ASAP7_75t_R", output = "Y", lhs = "n1", rhs = "CARRY", owner = "prefix_tree"} : () -> ()
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
    assert ops_by_name["fa0_xor_sum"].rhs.data == "A"
    assert ops_by_name["fa0_ao21_carry"].and_rhs.data == "A"
