#!/usr/bin/env python3
"""Generate the canonical MAC candidate netlist through the xDSL compiler."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rtl.compiler import compile_file, compile_text


DEFAULT_PASSES = (
    "lower-multiplier-to-arith-parts",
    "lower-arith-to-logic",
    "verify-post-arith-to-logic",
    "lower-logic-to-asap7",
    "optimize-critical-compressor-paths",
    "annotate-func-port-criticality",
    "region-scoped-cell-sizing",
    "verify-post-logic-to-physical",
)

DEFAULT_TOP = "mac16x16p32"
DEFAULT_COMPRESSOR_OPT_ITERATIONS = 3


def _build_default_mlir(top_name: str) -> str:
    arg_bindings = ', '.join(
        [
            '%0: !rtl.wire<"A":16>',
            '%1: !rtl.wire<"B":16>',
            '%2: !rtl.wire<"C":32>',
        ]
    )
    operand_types = ', '.join(
        [
            '!rtl.wire<"A":16>',
            '!rtl.wire<"B":16>',
            '!rtl.wire<"C":32>',
        ]
    )
    result_binding = "%3"
    result_type = '!rtl.wire<"D":32>'
    return f'''"builtin.module"() ({{
  "func.func"() ({{
  ^bb0({arg_bindings}):
    {result_binding} = "arith.multiplier"(%0, %1, %2) {{implementation = #arith.multiplier_impl<array>}} : ({operand_types}) -> {result_type}
    "func.return"({result_binding}) : ({result_type}) -> ()
  }}) {{sym_name = "{top_name}", function_type = ({operand_types}) -> {result_type}}} : () -> ()
}}) : () -> ()
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-mlir",
        type=Path,
        help="Read the compiler input from a .mlir file instead of using the canonical MAC front-end.",
    )
    parser.add_argument(
        "--output-verilog",
        type=Path,
        default=Path(f"{DEFAULT_TOP}.v"),
        help="Output Verilog path.",
    )
    parser.add_argument(
        "--output-ir",
        type=Path,
        help="Optional path for dumping the post-pass MLIR.",
    )
    parser.add_argument(
        "--top-name",
        default=DEFAULT_TOP,
        help="Top module name for the built-in canonical MAC front-end.",
    )
    parser.add_argument(
        "--compressor-opt-iterations",
        type=int,
        default=DEFAULT_COMPRESSOR_OPT_ITERATIONS,
        help="Maximum ASAP7 compressor critical-path rewrite iterations.",
    )
    args = parser.parse_args()
    if args.compressor_opt_iterations < 0:
        raise AssertionError("--compressor-opt-iterations must be non-negative")

    os.environ["MAC_AGENT_COMPRESSOR_OPT_MAX_ITERATIONS"] = str(args.compressor_opt_iterations)

    if args.input_mlir is not None:
        result = compile_file(args.input_mlir, DEFAULT_PASSES)
    else:
        result = compile_text(_build_default_mlir(args.top_name), DEFAULT_PASSES)

    args.output_verilog.parent.mkdir(parents=True, exist_ok=True)
    args.output_verilog.write_text(result.verilog_text, encoding="utf-8")
    if args.output_ir is not None:
        args.output_ir.parent.mkdir(parents=True, exist_ok=True)
        args.output_ir.write_text(result.ir_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
