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
  %0 = "logic.input"() : () -> !rtl.wire<"A":1>
  %1 = "logic.input"() : () -> !rtl.wire<"B":1>
  %2, %3 = "logic.instance"(%0, %1) {instance_name = "stage0_inst", callee = "stage0"} : (!rtl.wire<"A":1>, !rtl.wire<"B":1>) -> (!rtl.wire<"X":1>, !rtl.wire<"Y":1>)
  %4, %5 = "logic.instance"(%2, %3) {instance_name = "stage1_inst", callee = "stage1"} : (!rtl.wire<"X":1>, !rtl.wire<"Y":1>) -> (!rtl.wire<"D0":1>, !rtl.wire<"D1":1>)
  "func.func"() ({
    %6 = "logic.input"() : () -> !rtl.wire<"A":1>
    %7 = "logic.input"() : () -> !rtl.wire<"B":1>
    %8 = "asap7.and2"(%6, %7) {instance_name = "g0", cell = "AND2x2_ASAP7_75t_R", owner = "stage0"} : (!rtl.wire<"A":1>, !rtl.wire<"B":1>) -> !rtl.wire<"X":1>
    %9 = "asap7.and2"(%6, %7) {instance_name = "g1", cell = "AND2x2_ASAP7_75t_R", owner = "stage0"} : (!rtl.wire<"A":1>, !rtl.wire<"B":1>) -> !rtl.wire<"y1":1>
    %10 = "asap7.and2"(%9, %7) {instance_name = "g2", cell = "AND2x2_ASAP7_75t_R", owner = "stage0"} : (!rtl.wire<"y1":1>, !rtl.wire<"B":1>) -> !rtl.wire<"y2":1>
    %11 = "asap7.and2"(%10, %7) {instance_name = "g3", cell = "AND2x2_ASAP7_75t_R", owner = "stage0"} : (!rtl.wire<"y2":1>, !rtl.wire<"B":1>) -> !rtl.wire<"y3":1>
    %12 = "asap7.and2"(%11, %7) {instance_name = "g4", cell = "AND2x2_ASAP7_75t_R", owner = "stage0"} : (!rtl.wire<"y3":1>, !rtl.wire<"B":1>) -> !rtl.wire<"Y":1>
    "logic.output"(%8) : (!rtl.wire<"X":1>) -> ()
    "logic.output"(%12) : (!rtl.wire<"Y":1>) -> ()
    "func.return"() : () -> ()
  }) {logic.input_ports = ["input:A:1", "input:B:1"], logic.output_ports = ["output:X:1", "output:Y:1"], logic.region_kind = "stage0", sym_name = "stage0", function_type = () -> (), sym_visibility = "private"} : () -> ()
  "func.func"() ({
    %13 = "logic.input"() : () -> !rtl.wire<"X":1>
    %14 = "logic.input"() : () -> !rtl.wire<"Y":1>
    %15 = "asap7.xor2"(%13, %13) {instance_name = "h0a", cell = "XOR2x2_ASAP7_75t_R", owner = "stage1"} : (!rtl.wire<"X":1>, !rtl.wire<"X":1>) -> !rtl.wire<"t0":1>
    %16 = "asap7.xor2"(%15, %13) {instance_name = "h0b", cell = "XOR2x2_ASAP7_75t_R", owner = "stage1"} : (!rtl.wire<"t0":1>, !rtl.wire<"X":1>) -> !rtl.wire<"D0":1>
    %17 = "asap7.and2"(%14, %14) {instance_name = "h1", cell = "AND2x2_ASAP7_75t_R", owner = "stage1"} : (!rtl.wire<"Y":1>, !rtl.wire<"Y":1>) -> !rtl.wire<"D1":1>
    "logic.output"(%16) : (!rtl.wire<"D0":1>) -> ()
    "logic.output"(%17) : (!rtl.wire<"D1":1>) -> ()
    "func.return"() : () -> ()
  }) {logic.input_ports = ["input:X:1", "input:Y:1"], logic.output_ports = ["output:D0:1", "output:D1:1"], logic.region_kind = "stage1", sym_name = "stage1", function_type = () -> (), sym_visibility = "private"} : () -> ()
}) {func_name = "top", input_ports = ["input:A:1", "input:B:1"], output_ports = ["output:D0:1", "output:D1:1"]} : () -> ()
""".strip()
    )

    liberty_model = load_default_liberty_model()
    stage1_func = next(op for op in module.ops if isinstance(op, FuncOp) and op.sym_name.data == "stage1")
    isolated = analyze_func_timing(stage1_func, liberty_model)
    analysis = analyze_module_timing(module, liberty_model)

    stage1 = analysis.func_reports["stage1"]
    assert set(isolated.keep_fast_instances) == {"h0a", "h0b"}
    assert stage1.max_delay_ns > 0.0
    assert {"h0a", "h0b"} <= set(stage1.keep_fast_instances)
    assert max(stage1.port_paths, key=lambda path: path.delay_ns).output_ref in {"D0", "D1"}
