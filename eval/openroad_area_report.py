#!/usr/bin/env python3
"""Parse OpenROAD area outputs into detailed reports and structured JSON."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

AREA_RE = re.compile(
    r"Design area\s+([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s+(\S+)\s+([+-]?\d*\.?\d+)% utilization\.",
    re.I,
)
USAGE_RE = re.compile(r"^\s{2}(.+?)\s*:\s*(\d+)\s*$")
COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.S)
COMMENT_LINE_RE = re.compile(r"//.*?$", re.M)
ATTRIBUTE_RE = re.compile(r"\(\*.*?\*\)", re.S)
MODULE_RE = re.compile(
    r"\bmodule\s+([A-Za-z_]\w*)\s*(?:#\s*\([^;]*?\)\s*)?\((.*?)\)\s*;(.*?)\bendmodule\b",
    re.S,
)
INSTANTIATION_RE = re.compile(
    r"^\s*([A-Za-z_]\w*)\s*(?:#\s*\([^;]*?\)\s*)?([A-Za-z_]\w*)\s*(?:\[[^\]]+\])?\s*\(",
    re.M,
)
AUTO_NAME_TOKEN_RE = re.compile(
    r"(?i)(?:g\d+|u\d+|x\d+|inst\d+|genblk\d+|i\d+|n\d+|\d+)"
)
AUTO_NAME_RE = re.compile(r"(?i)(?:g\d+|u\d+|x\d+|inst\d+)(?:_dup\d*|_dup)?$")
SKIP_PREFIXES = {
    "module",
    "input",
    "output",
    "inout",
    "wire",
    "reg",
    "logic",
    "assign",
    "if",
    "for",
    "case",
}


@dataclass(frozen=True)
class InstanceRecord:
    inst_name: str
    master_name: str


@dataclass(frozen=True)
class ModuleInstance:
    cell_type: str
    inst_name: str


@dataclass(frozen=True)
class ModuleInfo:
    name: str
    body: str
    instances: tuple[ModuleInstance, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse OpenROAD area outputs.")
    parser.add_argument("--detail", action="store_true", help="Enable detailed area breakdown parsing")
    parser.add_argument("--openroad-log", required=True, type=Path)
    parser.add_argument("--netlist", type=Path)
    parser.add_argument("--liberty-paths", help="Colon-separated liberty list")
    parser.add_argument("--top-module")
    parser.add_argument("--design-area-rpt", required=True, type=Path)
    parser.add_argument("--cell-usage-rpt", required=True, type=Path)
    parser.add_argument("--instance-area-csv", type=Path)
    parser.add_argument("--cell-area-rpt", type=Path)
    parser.add_argument("--module-area-rpt", type=Path)
    parser.add_argument("--group-area-rpt", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.detail:
        missing = [
            name
            for name in ("netlist", "liberty_paths", "top_module", "instance_area_csv", "cell_area_rpt", "module_area_rpt", "group_area_rpt")
            if getattr(args, name) in (None, "")
        ]
        if missing:
            parser.error("--detail requires " + ", ".join(f"--{name.replace('_', '-')}" for name in missing))
    return args


def strip_comments(text: str) -> str:
    text = COMMENT_BLOCK_RE.sub("", text)
    text = COMMENT_LINE_RE.sub("", text)
    return ATTRIBUTE_RE.sub("", text)


def load_liberty_areas(paths_arg: str) -> dict[str, float]:
    areas: dict[str, float] = {}
    cell_start_re = re.compile(r"\bcell\s*\(\s*([^)]+?)\s*\)\s*\{", re.I)
    area_re = re.compile(r"\barea\s*:\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*;", re.I)

    for path_str in paths_arg.split(":"):
        path = Path(path_str)
        if not path.exists():
            continue
        current_cell: str | None = None
        brace_depth = 0
        current_area: float | None = None
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if current_cell is None:
                match = cell_start_re.search(line)
                if not match:
                    continue
                current_cell = match.group(1).strip().strip('"')
                brace_depth = line.count("{") - line.count("}")
                area_match = area_re.search(line)
                current_area = float(area_match.group(1)) if area_match else None
                if brace_depth <= 0:
                    if current_area is not None:
                        areas[current_cell] = current_area
                    current_cell = None
                continue

            area_match = area_re.search(line)
            if area_match and current_area is None:
                current_area = float(area_match.group(1))
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                if current_area is not None:
                    areas[current_cell] = current_area
                current_cell = None
                current_area = None
                brace_depth = 0
    return areas


def parse_modules(netlist_path: Path) -> dict[str, ModuleInfo]:
    text = strip_comments(netlist_path.read_text(encoding="utf-8", errors="ignore"))
    modules: dict[str, ModuleInfo] = {}
    for match in MODULE_RE.finditer(text):
        name = match.group(1)
        body = match.group(3)
        instances: list[ModuleInstance] = []
        for inst_match in INSTANTIATION_RE.finditer(body):
            cell_type = inst_match.group(1)
            inst_name = inst_match.group(2)
            if cell_type in SKIP_PREFIXES:
                continue
            instances.append(ModuleInstance(cell_type=cell_type, inst_name=inst_name))
        modules[name] = ModuleInfo(name=name, body=body, instances=tuple(instances))
    return modules


def parse_openroad_log(path: Path) -> tuple[str | None, re.Match[str] | None, list[str]]:
    if not path.exists():
        return None, None, []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    area_line = None
    area_match = None
    for line in lines:
        match = AREA_RE.search(line)
        if match:
            area_line = line.strip()
            area_match = match
            break

    usage_lines: list[str] = []
    for idx, line in enumerate(lines):
        if line.strip() != "Cell usage report:":
            continue
        usage_lines.append("Cell usage report:")
        for follow in lines[idx + 1 :]:
            if not follow.startswith("  "):
                break
            usage_lines.append(follow.rstrip())
        break

    return area_line, area_match, usage_lines


def load_instance_records(path: Path) -> list[InstanceRecord]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            inst_name = (row.get("inst_name") or "").strip()
            master_name = (row.get("master_name") or "").strip()
            if not inst_name or not master_name:
                continue
            rows.append(InstanceRecord(inst_name=inst_name, master_name=master_name))
    return rows


def make_entry(
    name: str,
    count: int,
    total_area: float,
    grand_total: float,
    unit_area: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": name,
        "count": count,
        "total_area": total_area,
        "ratio_percent": (100.0 * total_area / grand_total) if grand_total > 0 else 0.0,
    }
    if unit_area is not None:
        entry["unit_area"] = unit_area
    if extra:
        entry.update(extra)
    return entry


def aggregate_cell_area(
    instances: list[InstanceRecord], liberty_areas: dict[str, float], grand_total: float
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], int, int]:
    grouped: dict[str, dict[str, Any]] = {}
    missing_area = 0
    for inst in instances:
        area = liberty_areas.get(inst.master_name)
        if area is None:
            missing_area += 1
            continue
        item = grouped.setdefault(
            inst.master_name,
            {"count": 0, "unit_area": area, "total_area": 0.0},
        )
        item["count"] += 1
        item["total_area"] += area

    sorted_items = sorted(grouped.items(), key=lambda item: item[1]["total_area"], reverse=True)
    ordered_breakdown: dict[str, dict[str, Any]] = {}
    top_entries: list[dict[str, Any]] = []
    cell_count = 0
    for name, stats in sorted_items:
        cell_count += int(stats["count"])
        entry = make_entry(
            name=name,
            count=int(stats["count"]),
            total_area=float(stats["total_area"]),
            grand_total=grand_total,
            unit_area=float(stats["unit_area"]),
        )
        ordered_breakdown[name] = entry
        top_entries.append(entry)
    return ordered_breakdown, top_entries, cell_count, missing_area


def infer_instance_group(name: str) -> str:
    if AUTO_NAME_RE.fullmatch(name):
        return "<auto_generated>"
    if "/" in name:
        parts = [part for part in name.split("/") if part]
        if len(parts) > 1:
            return "/".join(parts[:-1])
        return name
    if "." in name:
        parts = [part for part in name.split(".") if part]
        if len(parts) > 1:
            return ".".join(parts[:-1])
        return name
    parts = [part for part in name.split("_") if part]
    if len(parts) <= 1:
        return "<auto_generated>" if AUTO_NAME_TOKEN_RE.fullmatch(name) else name
    trimmed = parts[:]
    if trimmed[-1].lower().startswith("dup"):
        trimmed.pop()
    while len(trimmed) > 1 and AUTO_NAME_TOKEN_RE.fullmatch(trimmed[-1]):
        trimmed.pop()
    if len(trimmed) <= 1:
        return "<auto_generated>" if AUTO_NAME_TOKEN_RE.fullmatch(parts[0]) else parts[0]
    return "_".join(trimmed)


def aggregate_instance_groups(
    instances: list[InstanceRecord], liberty_areas: dict[str, float], grand_total: float
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, float | int]] = defaultdict(lambda: {"count": 0, "total_area": 0.0})
    for inst in instances:
        area = liberty_areas.get(inst.master_name)
        if area is None:
            continue
        key = infer_instance_group(inst.inst_name)
        grouped[key]["count"] = int(grouped[key]["count"]) + 1
        grouped[key]["total_area"] = float(grouped[key]["total_area"]) + area

    entries = [
        make_entry(name=name, count=int(stats["count"]), total_area=float(stats["total_area"]), grand_total=grand_total)
        for name, stats in grouped.items()
    ]
    entries.sort(key=lambda entry: entry["total_area"], reverse=True)
    return entries


def compute_module_hierarchy(
    modules: dict[str, ModuleInfo],
    liberty_areas: dict[str, float],
    top_module: str,
    grand_total: float,
) -> tuple[list[dict[str, Any]], list[str]]:
    unknown_types: set[str] = set()
    memo: dict[str, float] = {}
    module_entries: list[dict[str, Any]] = []

    def module_area(module_name: str, stack: tuple[str, ...]) -> float:
        if module_name in memo:
            return memo[module_name]
        if module_name in stack:
            unknown_types.add(f"recursive:{module_name}")
            return 0.0
        module = modules.get(module_name)
        if module is None:
            unknown_types.add(module_name)
            return 0.0
        total = 0.0
        for inst in module.instances:
            if inst.cell_type in liberty_areas:
                total += liberty_areas[inst.cell_type]
            elif inst.cell_type in modules:
                total += module_area(inst.cell_type, stack + (module_name,))
            else:
                unknown_types.add(inst.cell_type)
        memo[module_name] = total
        return total

    def walk(module_name: str, base_path: str) -> None:
        module = modules.get(module_name)
        if module is None:
            return
        for inst in module.instances:
            if inst.cell_type not in modules:
                continue
            path = f"{base_path}/{inst.inst_name}" if base_path else inst.inst_name
            total_area = module_area(inst.cell_type, ())
            entry = make_entry(
                name=path,
                count=1,
                total_area=total_area,
                grand_total=grand_total,
                extra={
                    "module_name": inst.cell_type,
                    "depth": path.count("/") + 1,
                },
            )
            module_entries.append(entry)
            walk(inst.cell_type, path)

    if top_module in modules:
        walk(top_module, "")
    module_entries.sort(key=lambda entry: entry["total_area"], reverse=True)
    return module_entries, sorted(unknown_types)


def write_text_report(
    path: Path,
    title: str,
    columns: tuple[tuple[str, str], ...],
    rows: list[dict[str, Any]],
    empty_message: str,
    limit: int | None = 50,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text(f"{title}\n{empty_message}\n", encoding="utf-8")
        return

    display_rows = rows if limit is None else rows[:limit]
    widths = []
    for key, header in columns:
        width = len(header)
        for row in display_rows:
            width = max(width, len(_format_value(row.get(key))))
        widths.append(width)

    lines = [title]
    header_line = "  ".join(
        header.ljust(width) for (_, header), width in zip(columns, widths, strict=True)
    )
    lines.append(header_line)
    lines.append("  ".join("-" * width for width in widths))
    for row in display_rows:
        lines.append(
            "  ".join(
                _format_value(row.get(key)).ljust(width)
                for (key, _), width in zip(columns, widths, strict=True)
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def parse_legacy_result(
    area_line: str | None,
    area_match: re.Match[str] | None,
    usage_lines: list[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "missing_input",
        "source": "openroad",
        "area": None,
        "area_unit": None,
        "utilization_percent": None,
        "cell_count": 0,
        "cell_breakdown": {},
    }

    usage_breakdown: dict[str, dict[str, int]] = {}
    cell_count = 0
    for usage_line in usage_lines:
        match = USAGE_RE.match(usage_line)
        if not match:
            continue
        count = int(match.group(2))
        usage_breakdown[match.group(1).strip()] = {"count": count}
        cell_count += count

    if area_line and area_match:
        result["area"] = float(area_match.group(1))
        result["area_unit"] = area_match.group(2)
        result["utilization_percent"] = float(area_match.group(3))
        result["status"] = "ok"
    else:
        result["error"] = "parse_error:design_area"

    result["cell_breakdown"] = usage_breakdown
    result["cell_count"] = cell_count
    return result


def main() -> int:
    args = parse_args()
    area_line, area_match, usage_lines = parse_openroad_log(args.openroad_log)

    args.design_area_rpt.parent.mkdir(parents=True, exist_ok=True)
    args.cell_usage_rpt.parent.mkdir(parents=True, exist_ok=True)

    if area_line and area_match:
        args.design_area_rpt.write_text(area_line + "\n", encoding="utf-8")
    else:
        args.design_area_rpt.write_text("", encoding="utf-8")

    if usage_lines:
        args.cell_usage_rpt.write_text("\n".join(usage_lines) + "\n", encoding="utf-8")
    else:
        args.cell_usage_rpt.write_text("", encoding="utf-8")

    if not args.detail:
        result = parse_legacy_result(area_line, area_match, usage_lines)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0

    result: dict[str, Any] = {
        "status": "missing_input",
        "source": "openroad",
        "area": float(area_match.group(1)) if area_match else None,
        "area_unit": area_match.group(2) if area_match else None,
        "utilization_percent": float(area_match.group(3)) if area_match else None,
        "cell_count": 0,
        "cell_breakdown": {},
        "top_cells": [],
        "module_breakdown": [],
        "top_modules": [],
        "instance_group_breakdown": [],
        "top_instance_groups": [],
        "hierarchy_available": False,
        "hierarchy_source": "verilog",
        "instance_area_source": str(args.instance_area_csv),
    }

    usage_breakdown: dict[str, dict[str, int]] = {}
    for usage_line in usage_lines:
        match = USAGE_RE.match(usage_line)
        if not match:
            continue
        usage_breakdown[match.group(1).strip()] = {"count": int(match.group(2))}

    liberty_areas = load_liberty_areas(args.liberty_paths or "")
    instances = load_instance_records(args.instance_area_csv)
    grand_total = float(result["area"] or 0.0)

    cell_breakdown, top_cells, cell_count, missing_cell_area = aggregate_cell_area(
        instances, liberty_areas, grand_total
    )
    instance_groups = aggregate_instance_groups(instances, liberty_areas, grand_total)
    modules = parse_modules(args.netlist) if args.netlist and args.netlist.exists() else {}
    module_entries, unknown_types = compute_module_hierarchy(
        modules, liberty_areas, args.top_module or "", grand_total
    )

    result["cell_breakdown"] = cell_breakdown or usage_breakdown
    result["top_cells"] = top_cells[:20]
    result["cell_count"] = cell_count or sum(item["count"] for item in usage_breakdown.values())
    result["instance_count"] = len(instances)
    result["instance_group_breakdown"] = instance_groups
    result["top_instance_groups"] = instance_groups[:20]
    result["module_breakdown"] = module_entries
    result["top_modules"] = module_entries[:20]
    result["hierarchy_available"] = bool(module_entries)
    result["missing_cell_area_count"] = missing_cell_area
    if unknown_types:
        result["unknown_cell_types"] = unknown_types
    if grand_total > 0.0:
        result["status"] = "ok"

    write_text_report(
        args.cell_area_rpt,
        "Cell Area Breakdown",
        (
            ("name", "cell_type"),
            ("count", "count"),
            ("unit_area", "unit_area"),
            ("total_area", "total_area"),
            ("ratio_percent", "ratio_percent"),
        ),
        top_cells,
        "No cell-level area data available.",
    )
    write_text_report(
        args.module_area_rpt,
        "Module Area Breakdown",
        (
            ("name", "inst_path"),
            ("module_name", "module"),
            ("depth", "depth"),
            ("total_area", "total_area"),
            ("ratio_percent", "ratio_percent"),
        ),
        module_entries,
        "No hierarchical module instances found in the input netlist.",
    )
    write_text_report(
        args.group_area_rpt,
        "Instance Group Area Breakdown",
        (
            ("name", "group"),
            ("count", "count"),
            ("total_area", "total_area"),
            ("ratio_percent", "ratio_percent"),
        ),
        instance_groups,
        "No instance grouping data available.",
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
