"""Icarus simulation; standalone mode also supports the parameterized baseline."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, EvaluationError, execute, load_config, tool
from sim.vectors import directed_vectors, random_vectors


def simulate(dut, out, config, widths=(16, 16, 32), cycles=1):
    out.mkdir(parents=True, exist_ok=True)
    sanitized = out / "stdcell"
    sanitized.mkdir()
    sources = []
    for source in sorted((ROOT / "tech/asap7/verilog").rglob("*.v")):
        target = sanitized / source.name
        target.write_text(re.sub(r"(?is)\bspecify\b.*?\bendspecify\b", "", source.read_text()))
        sources.append(target)
    a, b, acc = widths
    defines = [f"-DMAC_A_WIDTH={a}", f"-DMAC_B_WIDTH={b}",
               f"-DMAC_ACC_WIDTH={acc}", f"-DMAC_PIPELINE_CYCLES={cycles}"]
    if cycles > 1:
        defines.append("-DMAC_USE_CLK=1")
    binary = out / "simv"
    timeout = config["timeouts_sec"]["sim"]
    execute([tool("iverilog", config), "-g2012", *defines, "-s", "tb_mac", "-o", binary,
             *sources, dut, ROOT / "eval/sim/tb_mac.sv"], out / "compile.log", timeout,
            cwd=out, failure="invalid")
    settings = config["simulation"]

    def one_seed(seed):
        folder = out / f"seed-{seed}"
        folder.mkdir()
        vectors = directed_vectors(a, b, acc) + random_vectors(settings["random_count"], seed, a, b, acc)
        vector_file = folder / "vectors.txt"
        vector_file.write_text("".join(f"{k} {av:X} {bv:X} {cv:X} {expected:X}\n"
                                      for k, av, bv, cv, expected in vectors))
        log = folder / "sim.log"
        execute([tool("vvp", config), binary, f"+VEC_FILE={vector_file}",
                 f"+DUT_NAME={dut.name}", f"+PIPELINE_LATENCY={cycles - 1}"], log, timeout,
                cwd=folder, failure="invalid")
        lines = log.read_text().splitlines()
        # A successful process exit alone is not a correctness verdict.
        if "RESULT: FAIL" in lines or lines.count("RESULT: PASS") != 1:
            raise EvaluationError(f"Missing or conflicting simulation verdict: {log}", "invalid")
        if not any(line.endswith(f"VECTORS={len(vectors)}") for line in lines):
            raise EvaluationError(f"Incomplete simulation: {log}", "invalid")
        return {"seed": seed, "vectors": len(vectors), "status": "pass"}

    seeds = settings["seeds"]
    if not seeds or len(set(seeds)) != len(seeds) or any(not isinstance(s, int) or s < 0 for s in seeds):
        raise EvaluationError("Simulation requires distinct nonnegative seeds")
    if settings["random_count"] < 0:
        raise EvaluationError("random_count must be nonnegative")
    with ThreadPoolExecutor(max_workers=max(1, settings["jobs"])) as pool:
        results = list(pool.map(one_seed, seeds))
    return {"status": "pass", "method": "directed_and_random_simulation", "seeds": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dut", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--widths", nargs=3, type=int, default=(16, 16, 32))
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--random-count", type=int, default=5000)
    args = parser.parse_args()
    if min(args.widths) < 1 or not 1 <= args.cycles <= 256:
        parser.error("Widths must be positive; cycles must be 1..256")
    config = load_config()
    config["simulation"]["random_count"] = args.random_count
    try:
        args.output.resolve().mkdir(parents=True, exist_ok=False)
        simulate(args.dut.resolve(), args.output.resolve(), config, args.widths, args.cycles)
    except (EvaluationError, OSError) as exc:
        print(f"SIMULATION_STATUS=FAIL: {exc}", file=sys.stderr)
        return 1
    print("SIMULATION_STATUS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
