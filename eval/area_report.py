#!/usr/bin/env python3
"""Compute netlist area by summing liberty cell areas."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.S)
COMMENT_LINE_RE = re.compile(r"//.*?$", re.M)
ATTRIBUTE_RE = re.compile(r"\(\*.*?\*\)", re.S)
MODULE_RE = re.compile(
    r"\bmodule\s+([A-Za-z_]\w*)\s*(?:#\s*\([^;]*?\)\s*)?\((.*?)\)\s*;(.*?)\bendmodule\b",
    re.S,
)
INSTANCE_RE = re.compile(
    r"^\s*([\\A-Za-z_][\\\w$./\[\]:-]*)\s*(?:#\s*\((.*?)\)\s*)?([\\A-Za-z_][\\\w$./\[\]:-]*)\s*(?:\[[^\]]+\])?\s*\(",
    re.S,
)
AREA_RE = re.compile(r"\barea\s*:\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s*;?", re.I)

SKIP_PREFIXES = {
    "assign",
    "always",
    "always_comb",
    "always_ff",
    "always_latch",
    "input",
    "output",
    "inout",
    "wire",
    "reg",
    "logic",
    "parameter",
    "localparam",
    "function",
    "task",
    "if",
    "for",
    "case",
    "generate",
    "endgenerate",
}


def _strip_comments(text: str) -> str:
    text = COMMENT_BLOCK_RE.sub("", text)
    text = COMMENT_LINE_RE.sub("", text)
    return ATTRIBUTE_RE.sub("", text)


def _find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    for idx in range(open_index, len(text)):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return idx
    return -1


def parse_liberty_areas(liberty_text: str) -> dict[str, float]:
    """Extract cell area map from liberty text."""
    text = _strip_comments(liberty_text)
    areas: dict[str, float] = {}
    pos = 0
    while True:
        match = re.search(r"\bcell\s*\(\s*([^)]+?)\s*\)\s*\{", text[pos:], re.I)
        if not match:
            break
        cell = match.group(1).strip().strip('"')
        block_open = pos + match.end() - 1
        block_close = _find_matching_brace(text, block_open)
        if block_close < 0:
            break
        block = text[block_open : block_close + 1]
        area_match = AREA_RE.search(block)
        if area_match:
            areas[cell] = float(area_match.group(1))
        pos = block_close + 1
    return areas


def parse_multiple_liberty_areas(liberty_texts: list[str]) -> dict[str, float]:
    areas: dict[str, float] = {}
    for liberty_text in liberty_texts:
        areas.update(parse_liberty_areas(liberty_text))
    return areas


def _extract_module_bodies(netlist_text: str) -> dict[str, str]:
    modules: dict[str, str] = {}
    for match in MODULE_RE.finditer(netlist_text):
        modules[match.group(1)] = match.group(3)
    return modules


def _extract_instance_types_from_body(body: str) -> list[str]:
    instance_types: list[str] = []
    for statement in body.split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        first = stmt.split(None, 1)[0].lower() if stmt.split(None, 1) else ""
        if first in SKIP_PREFIXES:
            continue
        instance_match = INSTANCE_RE.match(stmt)
        if not instance_match:
            continue
        instance_types.append(instance_match.group(1))
    return instance_types


def _add_counts(dst: dict[str, int], src: dict[str, int]) -> None:
    for key, value in src.items():
        dst[key] = dst.get(key, 0) + value


def _count_module_cell_types(
    module_name: str,
    module_instances: dict[str, list[str]],
    memo: dict[str, dict[str, int]],
    visiting: set[str],
) -> dict[str, int]:
    if module_name in memo:
        return dict(memo[module_name])
    if module_name in visiting:
        return {}

    visiting.add(module_name)
    counts: dict[str, int] = {}
    for instance_type in module_instances.get(module_name, []):
        if instance_type in module_instances:
            sub_counts = _count_module_cell_types(instance_type, module_instances, memo, visiting)
            _add_counts(counts, sub_counts)
        else:
            counts[instance_type] = counts.get(instance_type, 0) + 1
    visiting.remove(module_name)
    memo[module_name] = dict(counts)
    return counts


def count_netlist_cells(netlist_text: str, top: str) -> tuple[dict[str, int], str | None, bool]:
    """Count leaf cell types under top. Expands instantiated user modules recursively."""
    text = _strip_comments(netlist_text)
    modules = _extract_module_bodies(text)
    if not modules:
        return {}, None, False

    module_instances: dict[str, list[str]] = {
        name: _extract_instance_types_from_body(body) for name, body in modules.items()
    }
    top_found = top in modules
    resolved_top = top if top_found else next(iter(modules))
    memo: dict[str, dict[str, int]] = {}
    counts = _count_module_cell_types(resolved_top, module_instances, memo, set())
    return counts, resolved_top, top_found


def compute_area(netlist_text: str, liberty_texts: list[str], top: str) -> dict[str, Any]:
    areas = parse_multiple_liberty_areas(liberty_texts)
    cell_counts, resolved_top, top_found = count_netlist_cells(netlist_text, top=top)

    area_total = 0.0
    known_cells = 0
    unknown_cells: dict[str, int] = {}
    breakdown: dict[str, dict[str, float | int]] = {}

    for cell, count in sorted(cell_counts.items()):
        unit_area = areas.get(cell)
        if unit_area is None:
            unknown_cells[cell] = count
            continue
        known_cells += count
        area_total += unit_area * count
        breakdown[cell] = {
            "count": count,
            "unit_area": unit_area,
            "total_area": unit_area * count,
        }

    status = "ok"
    if not cell_counts:
        status = "no_instances"
    elif unknown_cells:
        status = "unknown_cells"

    warnings: list[str] = []
    if resolved_top is None:
        warnings.append("no_module_found_in_netlist")
    elif not top_found:
        warnings.append(f"top_not_found_fallback:{top}->{resolved_top}")

    return {
        "status": status,
        "top": top,
        "resolved_top": resolved_top,
        "area": round(area_total, 6),
        "cell_count": sum(cell_counts.values()),
        "known_cell_count": known_cells,
        "unknown_cell_count": sum(unknown_cells.values()),
        "unknown_cells": unknown_cells,
        "cell_breakdown": breakdown,
        "warnings": warnings,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute netlist area from liberty cell areas.")
    parser.add_argument("--netlist", required=True, type=Path, help="Input netlist (.v)")
    parser.add_argument(
        "--liberty",
        required=True,
        help="Input liberty (.lib) path, or a colon-separated list of liberty files",
    )
    parser.add_argument("--top", default="mac16x16p32", help="Top module name")
    parser.add_argument("--out", type=Path, help="Output JSON path (default: stdout)")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    liberty_paths = [Path(part) for part in args.liberty.split(":") if part]
    result: dict[str, Any] = {
        "netlist": str(args.netlist),
        "liberty": [str(path) for path in liberty_paths],
        "top": args.top,
    }
    errors: list[str] = []

    if not args.netlist.exists():
        errors.append(f"netlist_not_found:{args.netlist}")
    if not liberty_paths:
        errors.append("liberty_not_found:<empty>")
    for liberty_path in liberty_paths:
        if not liberty_path.exists():
            errors.append(f"liberty_not_found:{liberty_path}")

    if errors:
        result.update(
            {
                "status": "missing_input",
                "error_count": len(errors),
                "errors": errors,
                "area": None,
                "cell_count": 0,
                "known_cell_count": 0,
                "unknown_cell_count": 0,
                "unknown_cells": {},
                "cell_breakdown": {},
            }
        )
        payload = json.dumps(result, indent=2, sort_keys=True)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(payload + "\n", encoding="utf-8")
        else:
            print(payload)
        return 2

    try:
        netlist_text = args.netlist.read_text(encoding="utf-8", errors="ignore")
        liberty_texts = [
            liberty_path.read_text(encoding="utf-8", errors="ignore")
            for liberty_path in liberty_paths
        ]
        result.update(compute_area(netlist_text, liberty_texts, top=args.top))
    except Exception as exc:  # pragma: no cover - defensive runtime path
        result.update(
            {
                "status": "parse_error",
                "error_count": 1,
                "errors": [str(exc)],
                "area": None,
                "cell_count": 0,
                "known_cell_count": 0,
                "unknown_cell_count": 0,
                "unknown_cells": {},
                "cell_breakdown": {},
            }
        )
        payload = json.dumps(result, indent=2, sort_keys=True)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(payload + "\n", encoding="utf-8")
        else:
            print(payload)
        return 3

    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
