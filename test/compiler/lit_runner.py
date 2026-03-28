from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import shlex

from xdsl.parser import Parser
from xdsl.printer import Printer

from rtl.compiler.passes.emit_verilog import emit_verilog
from rtl.compiler.passes.lower_arith_to_logic import LowerArithToLogicPass
from rtl.compiler.passes.lower_logic_to_asap7 import LowerLogicToAsap7Pass
from rtl.compiler.passes.lower_multiplier_to_arith_parts import LowerMultiplierToArithPartsPass
from rtl.compiler.passes.region_scoped_cell_sizing import RegionScopedCellSizingPass
from rtl.compiler.pipeline import build_context
from rtl.compiler.passes.verify_post_arith_to_logic import PostArithToLogicVerificationPass
from rtl.compiler.passes.verify_post_logic_to_physical import PostLogicToPhysicalVerificationPass


@dataclass(frozen=True)
class RunSpec:
    passes: tuple[str, ...]
    emit: str


@dataclass(frozen=True)
class CheckSpec:
    kind: str
    pattern: str


def discover_mlir_tests(root: Path) -> list[Path]:
    return sorted(root.rglob("*.mlir"))


def parse_test_file(path: Path) -> tuple[RunSpec, list[CheckSpec], str]:
    run_spec: RunSpec | None = None
    checks: list[CheckSpec] = []
    source_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("// RUN:"):
            run_spec = parse_run_line(stripped[len("// RUN:") :].strip())
            continue
        if stripped.startswith("// CHECK-NOT:"):
            checks.append(CheckSpec(kind="CHECK-NOT", pattern=stripped[len("// CHECK-NOT:") :].strip()))
            continue
        if stripped.startswith("// CHECK:"):
            checks.append(CheckSpec(kind="CHECK", pattern=stripped[len("// CHECK:") :].strip()))
            continue
        source_lines.append(line)
    if run_spec is None:
        raise AssertionError(f"{path}: missing // RUN: directive")
    if not checks:
        raise AssertionError(f"{path}: missing // CHECK: directives")
    source = "\n".join(source_lines).strip() + "\n"
    return run_spec, checks, source


def parse_run_line(text: str) -> RunSpec:
    argv = shlex.split(text)
    if not argv or argv[0] != "compiler-opt":
        raise AssertionError(f"Unsupported RUN command: {text}")

    passes: list[str] = []
    emit = "ir"
    idx = 1
    while idx < len(argv):
        token = argv[idx]
        if token == "--pass":
            idx += 1
            if idx >= len(argv):
                raise AssertionError(f"Missing pass name in RUN command: {text}")
            passes.append(argv[idx])
        elif token == "--emit":
            idx += 1
            if idx >= len(argv):
                raise AssertionError(f"Missing emit target in RUN command: {text}")
            emit = argv[idx]
        else:
            raise AssertionError(f"Unsupported RUN option {token!r} in: {text}")
        idx += 1
    return RunSpec(passes=tuple(passes), emit=emit)


def run_mlir_test(path: Path) -> None:
    run_spec, checks, source = parse_test_file(path)
    output = execute_run_spec(run_spec, source)
    check_output(path, output, checks)


def execute_run_spec(run_spec: RunSpec, source: str) -> str:
    ctx = build_context()
    module = Parser(ctx, source, name="<test>").parse_module()
    emit = run_spec.emit

    for pass_name in run_spec.passes:
        if pass_name == "lower-multiplier-to-arith-parts":
            LowerMultiplierToArithPartsPass().apply(ctx, module)
        elif pass_name == "lower-arith-to-logic":
            LowerArithToLogicPass().apply(ctx, module)
        elif pass_name == "verify-post-arith-to-logic":
            PostArithToLogicVerificationPass().apply(ctx, module)
        elif pass_name == "lower-logic-to-asap7":
            LowerLogicToAsap7Pass().apply(ctx, module)
        elif pass_name == "region-scoped-cell-sizing":
            RegionScopedCellSizingPass().apply(ctx, module)
        elif pass_name == "verify-post-logic-to-physical":
            PostLogicToPhysicalVerificationPass().apply(ctx, module)
        elif pass_name == "emit-verilog":
            emit = "verilog"
        else:
            raise AssertionError(f"Unsupported pass {pass_name!r}")

    if emit == "ir":
        stream = StringIO()
        Printer(stream=stream, print_generic_format=True, print_properties_as_attributes=True).print_op(
            module
        )
        return stream.getvalue()
    if emit == "verilog":
        return emit_verilog(module)
    raise AssertionError(f"Unsupported emit target {emit!r}")


def check_output(path: Path, output: str, checks: list[CheckSpec]) -> None:
    cursor = 0
    for check in checks:
        if check.kind == "CHECK":
            position = output.find(check.pattern, cursor)
            if position < 0:
                raise AssertionError(
                    f"{path}: missing CHECK pattern {check.pattern!r}\n--- output ---\n{output}"
                )
            cursor = position + len(check.pattern)
        elif check.kind == "CHECK-NOT":
            if check.pattern in output:
                raise AssertionError(
                    f"{path}: forbidden CHECK-NOT pattern {check.pattern!r} found\n--- output ---\n{output}"
                )
        else:
            raise AssertionError(f"{path}: unsupported check kind {check.kind!r}")
