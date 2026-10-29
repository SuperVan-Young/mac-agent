#!/usr/bin/env python3
"""Evaluate one MAC netlist using a pinned Git revision, or explicitly in development mode."""
from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time

from common import ROOT, EvaluationError, digest, execute, load_config, new_run, provenance, tool, write_json


def evaluate(args):
    from check.run import check_netlist
    from sim.run import simulate
    from timing.run import timing
    from area.run import area
    from report import finish

    output = new_run(args.output)
    args.output = output
    config = load_config()
    result = {"schema_version": 1, "mode": "development", "execution_status": "running",
              "candidate_sha256": None, "failed_stage": None, "stages": {}, "metrics": None,
              "correctness": {"status": "not_run"}, "tool_versions": {}, "requested_stage": args.stage}
    started = time.monotonic()
    active_stage = "setup"
    try:
        if args.config:
            config = load_config(args.config)
        dut = output / "candidate.v"
        shutil.copyfile(args.candidate.resolve(), dut)
        result["candidate_sha256"] = digest(dut)
        write_json(output / "config.json", config)
        write_json(output / "manifest.json", provenance(config))
        write_json(output / "summary.json", result)
        for name, flag in [("yosys", "-V"), ("iverilog", "-V"), ("vvp", "-V"),
                           ("sta", "-version"), ("openroad", "-version")]:
            path = tool(name, config)
            log = output / "tools" / f"{name}.log"
            execute([path, flag], log, 15, cwd=output)
            result["tool_versions"][name] = {"path": path, "sha256": digest(path),
                                             "version": log.read_text().strip()}
        sequence = ["check"]
        if args.stage != "check":
            sequence.append("sim")
        if args.stage in ("all", "timing"):
            sequence.append("timing")
        if args.stage in ("all", "area"):
            sequence.append("area")
        mapped = None
        metrics = {}
        for stage in sequence:
            active_stage = stage
            before = time.monotonic()
            if stage == "check":
                mapped = check_netlist(dut, output / "check", config)
                result["evaluated_netlist_sha256"] = digest(mapped)
            elif stage == "sim":
                result["correctness"] = simulate(mapped, output / "sim", config)
            elif stage == "timing":
                query = None
                if args.from_pin or args.to_pin or args.max_paths != 1:
                    query = {"from": args.from_pin, "to": args.to_pin, "max_paths": args.max_paths}
                metrics.update(timing(mapped, output / "timing", config, query))
            elif stage == "area":
                metrics.update(area(mapped, output / "area", config, args.area_detail))
            result["stages"][stage] = {"status": "pass", "runtime_sec": time.monotonic() - before}
        if digest(dut) != result["candidate_sha256"] or digest(mapped) != result["evaluated_netlist_sha256"]:
            raise EvaluationError("Netlist changed during evaluation")
        result["metrics"] = metrics or None
        result["execution_status"] = "completed"
    except EvaluationError as exc:
        result["execution_status"] = "completed" if exc.status == "invalid" else exc.status
        result["failed_stage"] = active_stage
        result["stages"][active_stage] = {"status": exc.status, "message": str(exc)}
        if active_stage == "sim":
            result["correctness"] = {"status": "fail" if exc.status == "invalid" else exc.status}
        result["metrics"] = None
    except Exception as exc:
        result["execution_status"] = "error"
        result["failed_stage"] = active_stage
        result["stages"][active_stage] = {"status": "error", "message": f"{type(exc).__name__}: {exc}"}
        result["metrics"] = None
    result["runtime_sec"] = time.monotonic() - started
    finish(result, output, config)
    print(output / "summary.json")
    if result["execution_status"] == "timeout":
        return 3
    if result["execution_status"] == "error":
        return 2
    if args.stage != "all" and not result["failed_stage"]:
        return 0  # Stage succeeded; summary still does not claim full acceptance.
    return 0 if result["pass"] else 1


def official(args):
    if args.config or args.stage != "all" or args.from_pin or args.to_pin or args.max_paths != 1:
        raise EvaluationError("Official evaluation uses the committed config and full workflow; use --dev for diagnostics")
    # Resolve once: refs may move while tools are running.
    rev = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--verify",
                                   args.harness_ref + "^{commit}"], text=True).strip()
    with tempfile.TemporaryDirectory(prefix="mac-harness-") as temp:
        snapshot = Path(temp)
        archive = subprocess.check_output(["git", "-C", str(ROOT), "archive", rev, "eval", "tech"])
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            # Only regular files/directories. PDK must be part of the selected revision.
            for member in tar.getmembers():
                if member.issym() or member.islnk() or member.name.startswith("/") or ".." in Path(member.name).parts:
                    raise EvaluationError("Harness archive contains unsafe paths or links")
            tar.extractall(snapshot, filter="data")
        worker = snapshot / "eval/run.py"
        if not worker.exists():
            raise EvaluationError(f"Revision {rev} has no Python harness; commit the harness first, or use --dev")
        output = Path(args.output).resolve() if args.output else ROOT / "results" / ("official-" + snapshot.name)
        args.output = output
        if output.exists():
            raise EvaluationError(f"Output already exists: {output}")
        # Take the candidate snapshot before invoking any evaluator subprocess.
        candidate = snapshot / "submission.v"
        shutil.copyfile(args.candidate.resolve(), candidate)
        expected_hash = digest(candidate)
        command = [sys.executable, str(worker), str(candidate), "--dev", "--output", str(output)]
        if args.area_detail:
            command.append("--area-detail")
        # Avoid importing code from the working checkout through PYTHONPATH.
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        completed = subprocess.run(command, cwd=snapshot, env=env)
        summary = output / "summary.json"
        if not summary.exists():
            raise EvaluationError(f"Pinned evaluator produced no result (exit {completed.returncode})")
        result = json.loads(summary.read_text())
        result.update(mode="official", harness_commit=rev)
        if result.get("candidate_sha256") != expected_hash:
            result.update(execution_status="error", validity="not_established", **{"pass": False},
                          failed_stage="snapshot", metrics=None)
            write_json(summary, result)
            return 2
        write_json(summary, result)
        # Keep the exact evaluator sources available for replay; original PDK hashes are in manifest.
        shutil.copytree(snapshot / "eval", output / "harness", ignore=shutil.ignore_patterns("__pycache__"))
        return completed.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, help="New run directory; existing directories are rejected")
    parser.add_argument("--dev", action="store_true", help="Use working-tree evaluator; not a formal result")
    parser.add_argument("--harness-ref", default="HEAD", help="Committed evaluator revision (default: HEAD)")
    parser.add_argument("--config", type=Path, help="Development-only JSON configuration")
    parser.add_argument("--stage", choices=["all", "check", "sim", "timing", "area"], default="all")
    parser.add_argument("--area-detail", action="store_true")
    parser.add_argument("--max-paths", type=int, default=1)
    parser.add_argument("--from", dest="from_pin", default="")
    parser.add_argument("--to", dest="to_pin", default="")
    args = parser.parse_args()
    if args.max_paths < 1:
        parser.error("--max-paths must be positive")
    output_existed = args.output is not None and args.output.exists()
    try:
        return evaluate(args) if args.dev else official(args)
    except (EvaluationError, OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"Evaluation setup failed: {exc}", file=sys.stderr)
        if not output_existed:
            output = Path(args.output).resolve() if args.output else new_run()
            output.mkdir(parents=True, exist_ok=True)
            write_json(output / "summary.json", {
                "schema_version": 1, "mode": "development" if args.dev else "official",
                "requested_harness_ref": None if args.dev else args.harness_ref,
                "execution_status": "error", "validity": "not_established", "pass": False,
                "failed_stage": "setup", "error": str(exc), "metrics": None,
            })
            print(output / "summary.json")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
