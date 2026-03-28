from __future__ import annotations

from xdsl.dialects.func import FuncOp

from rtl.compiler.analysis import (
    analyze_func_timing,
    analyze_module_timing,
    load_default_liberty_model,
)
from rtl.compiler.pipeline import parse_module


def test_hierarchical_input_arrival_propagation_changes_critical_instances() -> None:
    module = parse_module(
        """
"builtin.module"() ({
  "logic.instance"() {instance_name = "stage0_inst", callee = "stage0", input_connections = ["A=A", "B=B"], output_connections = ["X=n0", "Y=n1"]} : () -> ()
  "logic.instance"() {instance_name = "stage1_inst", callee = "stage1", input_connections = ["X=n0", "Y=n1"], output_connections = ["D0=D0", "D1=D1"]} : () -> ()
  "func.func"() ({
    "asap7.and2"() {instance_name = "g0", cell = "AND2x2_ASAP7_75t_R", output = "X", lhs = "A", rhs = "B", owner = "stage0"} : () -> ()
    "asap7.and2"() {instance_name = "g1", cell = "AND2x2_ASAP7_75t_R", output = "y1", lhs = "A", rhs = "B", owner = "stage0"} : () -> ()
    "asap7.and2"() {instance_name = "g2", cell = "AND2x2_ASAP7_75t_R", output = "y2", lhs = "y1", rhs = "B", owner = "stage0"} : () -> ()
    "asap7.and2"() {instance_name = "g3", cell = "AND2x2_ASAP7_75t_R", output = "y3", lhs = "y2", rhs = "B", owner = "stage0"} : () -> ()
    "asap7.and2"() {instance_name = "g4", cell = "AND2x2_ASAP7_75t_R", output = "Y", lhs = "y3", rhs = "B", owner = "stage0"} : () -> ()
  }) {logic.input_ports = ["input:A:1", "input:B:1"], logic.output_ports = ["output:X:1", "output:Y:1"], sym_name = "stage0", function_type = () -> (), sym_visibility = "private"} : () -> ()
  "func.func"() ({
    "asap7.xor2"() {instance_name = "h0a", cell = "XOR2x2_ASAP7_75t_R", output = "t0", lhs = "X", rhs = "X", owner = "stage1"} : () -> ()
    "asap7.xor2"() {instance_name = "h0b", cell = "XOR2x2_ASAP7_75t_R", output = "D0", lhs = "t0", rhs = "X", owner = "stage1"} : () -> ()
    "asap7.and2"() {instance_name = "h1", cell = "AND2x2_ASAP7_75t_R", output = "D1", lhs = "Y", rhs = "Y", owner = "stage1"} : () -> ()
  }) {logic.input_ports = ["input:X:1", "input:Y:1"], logic.output_ports = ["output:D0:1", "output:D1:1"], sym_name = "stage1", function_type = () -> (), sym_visibility = "private"} : () -> ()
}) {func_name = "top", input_ports = ["input:A:1", "input:B:1"], output_ports = ["output:D0:1", "output:D1:1"]} : () -> ()
""".strip()
    )

    liberty_model = load_default_liberty_model()
    stage1_func = next(
        op for op in module.ops if isinstance(op, FuncOp) and op.sym_name.data == "stage1"
    )
    isolated = analyze_func_timing(stage1_func, liberty_model)
    analysis = analyze_module_timing(module, liberty_model)

    stage1 = analysis.func_reports["stage1"]
    assert set(isolated.keep_fast_instances) == {"h0a", "h0b"}
    assert stage1.max_delay_ns > 0.0
    assert "h1" in stage1.keep_fast_instances
    assert max(stage1.port_paths, key=lambda path: path.delay_ns).output_ref == "D1"
