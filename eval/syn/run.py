#!/usr/bin/env python3
"""Explicit Genus baseline synthesis, independent of candidate evaluation."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, EvaluationError, execute, load_config, new_run, tool, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtl", type=Path, default=ROOT / "rtl/baseline/baseline.v")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--widths", nargs=3, type=int, default=(16, 16, 32))
    parser.add_argument("--cycles", type=int, default=1)
    args = parser.parse_args()
    if min(args.widths) < 1 or args.cycles < 1:
        parser.error("Widths and cycles must be positive")
    config = load_config()
    out = new_run(args.output)
    env = {"GENUS_TOP": config["top"], "GENUS_RTL": args.rtl.resolve(),
           "GENUS_LIB": ":".join(str(ROOT / p) for p in config["liberty"]),
           "GENUS_CLK_PERIOD": config["timing"]["period_ns"],
           "GENUS_A_WIDTH": args.widths[0], "GENUS_B_WIDTH": args.widths[1],
           "GENUS_ACC_WIDTH": args.widths[2], "GENUS_PIPELINE_CYCLES": args.cycles,
           "GENUS_OUT_DIR": out, "GENUS_RPT_DIR": out, "GENUS_DRY_RUN": 0}
    try:
        execute([tool("genus", config), "-no_gui", "-batch", "-files", ROOT / "eval/syn/run.tcl"],
                out / "console.log", config["timeouts_sec"]["syn"], cwd=out, env=env)
        if not (out / "baseline_mapped.v").is_file():
            raise EvaluationError("Genus produced no mapped netlist")
    except EvaluationError as exc:
        write_json(out / "synthesis.json", {"status": exc.status, "error": str(exc)})
        return 1
    write_json(out / "synthesis.json", {"status": "completed", "widths": args.widths, "cycles": args.cycles})
    print(out / "baseline_mapped.v")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
