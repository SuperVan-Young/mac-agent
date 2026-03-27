#!/usr/bin/env python3
"""Aggregate simulation, timing, and area results into a unified summary."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from area_report import compute_area  # noqa: E402


KEY_VALUE_RE = re.compile(r"^\s*([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$")
FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

SUMMARY_FIELDS = [
    "design_name",
    "design_type",
    "correctness",
    "timing_status",
    "wns",
    "tns",
    "critical_delay",
    "area",
    "cell_count",
    "sim_runtime_sec",
    "eval_runtime_sec",
    "total_runtime_sec",
]


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text.upper() == "NA":
        return None
    try:
        return float(text)
    except ValueError:
        match = FLOAT_RE.search(text)
        if match:
            return float(match.group(0))
    return None


def parse_sim_log(path: Path | None) -> dict[str, Any]:
    result = {"correctness": "not_run"}
    if not path:
        return result
    if not path.exists():
        result["correctness"] = "not_run"
        result["sim_error"] = f"missing_sim_log:{path}"
        return result

    text = path.read_text(encoding="utf-8", errors="ignore")
    if "SIMULATION_STATUS=PASS" in text or "RESULT: PASS" in text:
        result["correctness"] = "pass"
    elif "SIMULATION_STATUS=FAIL" in text or "RESULT: FAIL" in text:
        result["correctness"] = "fail"
    else:
        result["correctness"] = "unknown"
    return result


def parse_timing_summary(path: Path | None, critical_path_path: Path | None) -> dict[str, Any]:
    result = {
        "timing_status": "not_run",
        "wns": None,
        "tns": None,
        "critical_delay": None,
    }
    if not path:
        return result
    if not path.exists():
        result["timing_status"] = "not_run"
        result["timing_error"] = f"missing_timing_summary:{path}"
        return result

    text = path.read_text(encoding="utf-8", errors="ignore")
    kv: dict[str, str] = {}
    for line in text.splitlines():
        match = KEY_VALUE_RE.match(line)
        if match:
            kv[match.group(1).lower()] = match.group(2).strip()

    result["wns"] = _to_float(kv.get("wns"))
    result["tns"] = _to_float(kv.get("tns"))
    result["critical_delay"] = _to_float(kv.get("critical_delay"))

    if result["wns"] is None:
        for line in text.splitlines():
            lower = line.lower()
            if "worst slack" in lower or lower.startswith("wns") or "slack:=" in lower:
                result["wns"] = _to_float(line)
                if result["wns"] is not None:
                    break

    if result["tns"] is None:
        for line in text.splitlines():
            lower = line.lower()
            if "tns" in lower:
                result["tns"] = _to_float(line)
                if result["tns"] is not None:
                    break

    if result["critical_delay"] is None and critical_path_path and critical_path_path.exists():
        ctext = critical_path_path.read_text(encoding="utf-8", errors="ignore")
        for line in ctext.splitlines():
            lower = line.lower()
            if "data arrival time" in lower or "arrival" in lower or "delay" in lower:
                result["critical_delay"] = _to_float(line)
                if result["critical_delay"] is not None:
                    break
    if result["critical_delay"] is None:
        arrival = None
        required = None
        for line in text.splitlines():
            lower = line.lower()
            if "arrival:=" in lower:
                arrival = _to_float(line)
            elif "required time:=" in lower:
                required = _to_float(line)
        if arrival is not None and required is not None:
            result["critical_delay"] = arrival

    if result["wns"] is None:
        result["timing_status"] = "unknown"
    elif result["wns"] >= 0.0:
        result["timing_status"] = "pass"
    else:
        result["timing_status"] = "fail"

    return result


def compute_area_from_inputs(netlist: Path | None, liberty: str | None, top: str) -> dict[str, Any]:
    result = {"area": None, "cell_count": 0, "area_status": "not_run"}
    if not netlist or not liberty:
        return result
    liberty_paths = [Path(part) for part in liberty.split(":") if part]
    if not netlist.exists() or not liberty_paths or any(not path.exists() for path in liberty_paths):
        result["area_status"] = "missing_input"
        return result

    payload = compute_area(
        netlist.read_text(encoding="utf-8", errors="ignore"),
        [path.read_text(encoding="utf-8", errors="ignore") for path in liberty_paths],
        top=top,
    )
    result["area"] = payload.get("area")
    result["cell_count"] = payload.get("cell_count", 0)
    result["area_status"] = payload.get("status", "unknown")
    result["area_details"] = payload
    return result


def load_area_json(path: Path | None) -> dict[str, Any]:
    result = {"area": None, "cell_count": 0, "area_status": "not_run"}
    if not path:
        return result
    if not path.exists():
        result["area_status"] = "missing_input"
        return result

    data = json.loads(path.read_text(encoding="utf-8"))
    result["area"] = data.get("area")
    result["cell_count"] = data.get("cell_count", 0)
    result["area_status"] = data.get("status", "unknown")
    result["area_details"] = data
    return result


def write_csv(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerow({field: summary.get(field) for field in SUMMARY_FIELDS})


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate sim/timing/area outputs.")
    parser.add_argument("--design-name", required=True, help="Summary design name")
    parser.add_argument("--design-type", required=True, choices=["baseline", "candidate"])
    parser.add_argument("--top", default="mac16x16p32", help="Top module name")
    parser.add_argument("--results-dir", type=Path, help="Override results/<design_name> output dir")
    parser.add_argument("--sim-log", type=Path, help="Simulation log path")
    parser.add_argument("--timing-summary", type=Path, help="Timing summary report path")
    parser.add_argument("--critical-path", type=Path, help="Critical path report path")
    parser.add_argument("--area-json", type=Path, help="Existing area report JSON path")
    parser.add_argument("--netlist", type=Path, help="Netlist path for area calculation")
    parser.add_argument(
        "--liberty",
        help="Liberty path or colon-separated liberty file list for area calculation",
    )
    parser.add_argument("--sim-runtime-sec", type=float)
    parser.add_argument("--eval-runtime-sec", type=float)
    parser.add_argument("--write-csv", action="store_true", help="Also emit summary.csv")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    out_dir = args.results_dir or Path("results") / args.design_name
    out_dir.mkdir(parents=True, exist_ok=True)

    sim_info = parse_sim_log(args.sim_log)
    timing_info = parse_timing_summary(args.timing_summary, args.critical_path)
    if args.area_json:
        area_info = load_area_json(args.area_json)
    else:
        area_info = compute_area_from_inputs(args.netlist, args.liberty, args.top)

    sim_runtime = args.sim_runtime_sec
    eval_runtime = args.eval_runtime_sec
    total_runtime = None
    if sim_runtime is not None or eval_runtime is not None:
        total_runtime = (sim_runtime or 0.0) + (eval_runtime or 0.0)

    summary = {
        "design_name": args.design_name,
        "design_type": args.design_type,
        "correctness": sim_info.get("correctness", "not_run"),
        "timing_status": timing_info.get("timing_status", "not_run"),
        "wns": timing_info.get("wns"),
        "tns": timing_info.get("tns"),
        "critical_delay": timing_info.get("critical_delay"),
        "area": area_info.get("area"),
        "cell_count": area_info.get("cell_count", 0),
        "sim_runtime_sec": sim_runtime,
        "eval_runtime_sec": eval_runtime,
        "total_runtime_sec": total_runtime,
        "sim": sim_info,
        "timing": timing_info,
        "area_report": area_info.get("area_details"),
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.write_csv:
        write_csv(out_dir / "summary.csv", summary)

    print(f"Wrote {summary_path}")
    if args.write_csv:
        print(f"Wrote {out_dir / 'summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
