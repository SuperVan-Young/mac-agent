#!/usr/bin/env python3
"""Generate the canonical MAC candidate netlist through the xDSL compiler."""

from __future__ import annotations

import argparse
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
    "region-scoped-cell-sizing",
    "verify-post-logic-to-physical",
)

DEFAULT_TOP = "mac16x16p32"


def _build_default_mlir(top_name: str) -> str:
    return f'''"builtin.module"() ({{
  "arith.multiplier"() {{implementation = "array"}} : () -> ()
}}) {{func_name = "{top_name}", input_ports = ["input:A:16", "input:B:16", "input:C:32"], output_ports = ["output:D:32"]}} : () -> ()
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
    args = parser.parse_args()

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
