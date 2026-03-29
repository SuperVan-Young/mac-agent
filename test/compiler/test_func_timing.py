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
    %0 = "logic.input"() {port_name = "A"} : () -> !rtl.wire<1>
    %1 = "logic.input"() {port_name = "B"} : () -> !rtl.wire<1>
    %2 = "asap7.and2"(%0, %1) {instance_name = "g0", cell = "AND2x2_ASAP7_75t_R", output_name = "X", owner = "stage0"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %3 = "asap7.and2"(%0, %1) {instance_name = "g1", cell = "AND2x2_ASAP7_75t_R", output_name = "y1", owner = "stage0"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %4 = "asap7.and2"(%3, %1) {instance_name = "g2", cell = "AND2x2_ASAP7_75t_R", output_name = "y2", owner = "stage0"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %5 = "asap7.and2"(%4, %1) {instance_name = "g3", cell = "AND2x2_ASAP7_75t_R", output_name = "y3", owner = "stage0"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %6 = "asap7.and2"(%5, %1) {instance_name = "g4", cell = "AND2x2_ASAP7_75t_R", output_name = "Y", owner = "stage0"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    "logic.output"(%2) {port_name = "X"} : (!rtl.wire<1>) -> ()
    "logic.output"(%6) {port_name = "Y"} : (!rtl.wire<1>) -> ()
    "func.return"() : () -> ()
  }) {logic.input_ports = ["input:A:1", "input:B:1"], logic.output_ports = ["output:X:1", "output:Y:1"], sym_name = "stage0", function_type = () -> (), sym_visibility = "private"} : () -> ()
  "func.func"() ({
    %7 = "logic.input"() {port_name = "X"} : () -> !rtl.wire<1>
    %8 = "logic.input"() {port_name = "Y"} : () -> !rtl.wire<1>
    %9 = "asap7.xor2"(%7, %7) {instance_name = "h0a", cell = "XOR2x2_ASAP7_75t_R", output_name = "t0", owner = "stage1"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %10 = "asap7.xor2"(%9, %7) {instance_name = "h0b", cell = "XOR2x2_ASAP7_75t_R", output_name = "D0", owner = "stage1"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    %11 = "asap7.and2"(%8, %8) {instance_name = "h1", cell = "AND2x2_ASAP7_75t_R", output_name = "D1", owner = "stage1"} : (!rtl.wire<1>, !rtl.wire<1>) -> !rtl.wire<1>
    "logic.output"(%10) {port_name = "D0"} : (!rtl.wire<1>) -> ()
    "logic.output"(%11) {port_name = "D1"} : (!rtl.wire<1>) -> ()
    "func.return"() : () -> ()
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
