#!/usr/bin/env python3
"""Parse OpenROAD log output into area reports and area JSON."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

AREA_RE = re.compile(
    r"Design area\s+([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)\s+(\S+)\s+([+-]?\d*\.?\d+)% utilization\.",
    re.I,
)
USAGE_RE = re.compile(r"^\s{2}(.+?)\s*:\s*(\d+)\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse OpenROAD area log.")
    parser.add_argument("--openroad-log", required=True, type=Path)
    parser.add_argument("--design-area-rpt", required=True, type=Path)
    parser.add_argument("--cell-usage-rpt", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result: dict[str, object] = {
        "status": "missing_input",
        "source": "openroad",
        "area": None,
        "area_unit": None,
        "utilization_percent": None,
        "cell_count": 0,
        "cell_breakdown": {},
    }

    if not args.openroad_log.exists():
        result["error"] = f"missing_log:{args.openroad_log}"
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return 0

    log_text = args.openroad_log.read_text(encoding="utf-8", errors="ignore")
    lines = log_text.splitlines()

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

    args.design_area_rpt.parent.mkdir(parents=True, exist_ok=True)
    args.cell_usage_rpt.parent.mkdir(parents=True, exist_ok=True)

    if area_line:
        args.design_area_rpt.write_text(area_line + "\n", encoding="utf-8")
        result["area"] = float(area_match.group(1))  # type: ignore[union-attr]
        result["area_unit"] = area_match.group(2)  # type: ignore[union-attr]
        result["utilization_percent"] = float(area_match.group(3))  # type: ignore[union-attr]
    else:
        args.design_area_rpt.write_text("", encoding="utf-8")
        result["error"] = "parse_error:design_area"

    if usage_lines:
        args.cell_usage_rpt.write_text("\n".join(usage_lines) + "\n", encoding="utf-8")
    else:
        args.cell_usage_rpt.write_text("", encoding="utf-8")

    breakdown: dict[str, dict[str, int]] = {}
    cell_count = 0
    for usage_line in usage_lines:
        match = USAGE_RE.match(usage_line)
        if not match:
            continue
        label = match.group(1).strip()
        count = int(match.group(2))
        breakdown[label] = {"count": count}
        cell_count += count

    result["cell_breakdown"] = breakdown
    result["cell_count"] = cell_count
    if result.get("area") is not None:
        result["status"] = "ok"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
