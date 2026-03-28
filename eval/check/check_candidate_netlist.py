#!/usr/bin/env python3
"""Candidate netlist contract checks for structural MAC submissions."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass


CANONICAL_TOP = "mac16x16p32"
CANONICAL_PORTS = ("A", "B", "C", "D")
CANONICAL_DIRECTIONS = {"A": "input", "B": "input", "C": "input", "D": "output"}
CANONICAL_WIDTHS = {"A": 16, "B": 16, "C": 32, "D": 32}

DEFAULT_ALLOWED_PRIMITIVES = {
    "and",
    "or",
    "xor",
    "xnor",
    "nand",
    "nor",
    "not",
    "buf",
}

DEFAULT_REPO_LIBERTIES = (
    "tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib",
    "tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib",
    "tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib",
    "tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib",
    "tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
)

FORBIDDEN_OPERATOR_PATTERNS = (
    re.compile(r"(?<!\w)\*(?!\w)"),
    re.compile(r"(?<!\w)\+(?!\w)"),
)

FORBIDDEN_BEHAVIORAL_PATTERNS = (
    re.compile(r"\balways(_comb|_ff|_latch)?\b"),
    re.compile(r"\balways\s*@"),
)

MODULE_RE = re.compile(
    r"\bmodule\s+([A-Za-z_]\w*)\s*(?:#\s*\([^;]*?\)\s*)?\((.*?)\)\s*;(.*?)\bendmodule\b",
    re.S,
)
INSTANTIATION_RE = re.compile(
    r"^\s*([A-Za-z_]\w*)\s*(?:#\s*\([^;]*?\)\s*)?([A-Za-z_]\w*)\s*(?:\[[^\]]+\])?\s*\(",
    re.M,
)
ATTRIBUTE_RE = re.compile(r"\(\*.*?\*\)", re.S)
COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.S)
COMMENT_LINE_RE = re.compile(r"//.*?$", re.M)
LIB_CELL_RE = re.compile(r"\bcell\s*\(\s*([^)]+?)\s*\)\s*\{", re.I)


@dataclass
class ModuleInfo:
    name: str
    header_raw: str
    header_ports: list[str]
    body: str


def strip_comments(text: str) -> str:
    text = COMMENT_BLOCK_RE.sub("", text)
    return COMMENT_LINE_RE.sub("", text)


def load_allowlist(path: pathlib.Path | None) -> set[str]:
    allowed = set(DEFAULT_ALLOWED_PRIMITIVES)
    if not path:
        return allowed
    raw = path.read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        allowed.add(line.split()[0])
    return allowed


def load_allowlist_from_liberties(liberty_arg: str | None) -> set[str]:
    allowed = set(DEFAULT_ALLOWED_PRIMITIVES)
    if not liberty_arg:
        return allowed
    for part in liberty_arg.split(":"):
        path = pathlib.Path(part)
        if not path.exists():
            continue
        raw = path.read_text(encoding="utf-8", errors="ignore")
        for match in LIB_CELL_RE.finditer(raw):
            allowed.add(match.group(1).strip().strip('"'))
    return allowed


def parse_modules(text: str) -> list[ModuleInfo]:
    modules: list[ModuleInfo] = []
    for match in MODULE_RE.finditer(text):
        name = match.group(1)
        header = match.group(2)
        body = match.group(3)
        ports = [p.strip().split()[-1] for p in header.split(",") if p.strip()]
        modules.append(ModuleInfo(name=name, header_raw=header, header_ports=ports, body=body))
    return modules


def parse_port_declarations(body: str) -> dict[str, tuple[str, int]]:
    declarations: dict[str, tuple[str, int]] = {}
    for statement in body.split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        token = stmt.split()
        if not token:
            continue
        if token[0] not in {"input", "output", "inout"}:
            continue
        direction = token[0]
        width = 1
        width_match = re.search(r"\[(\d+)\s*:\s*(\d+)\]", stmt)
        if width_match:
            msb = int(width_match.group(1))
            lsb = int(width_match.group(2))
            width = abs(msb - lsb) + 1
        # Remove qualifiers and packed dimensions.
        stmt_clean = re.sub(r"\b(input|output|inout|wire|reg|logic|signed|unsigned)\b", " ", stmt)
        stmt_clean = re.sub(r"\[[^\]]+\]", " ", stmt_clean)
        for name in stmt_clean.split(","):
            pname = name.strip()
            if pname:
                declarations[pname] = (direction, width)
    return declarations


def parse_port_declarations_from_header(header: str) -> dict[str, tuple[str, int]]:
    declarations: dict[str, tuple[str, int]] = {}
    for part in header.split(","):
        item = part.strip()
        if not item:
            continue
        tokens = item.split()
        if not tokens:
            continue
        if tokens[0] not in {"input", "output", "inout"}:
            continue
        direction = tokens[0]
        width = 1
        width_match = re.search(r"\[(\d+)\s*:\s*(\d+)\]", item)
        if width_match:
            msb = int(width_match.group(1))
            lsb = int(width_match.group(2))
            width = abs(msb - lsb) + 1
        name = tokens[-1]
        declarations[name] = (direction, width)
    return declarations


def check_interface(module: ModuleInfo, errors: list[str]) -> None:
    if module.header_ports != list(CANONICAL_PORTS):
        errors.append(
            f"Top port order must be {CANONICAL_PORTS}, found {tuple(module.header_ports)}"
        )

    decls = parse_port_declarations(module.body)
    if not decls:
        decls = parse_port_declarations_from_header(module.header_raw)
    if set(decls) != set(CANONICAL_PORTS):
        errors.append(f"Top declarations must contain exactly {CANONICAL_PORTS}, found {tuple(sorted(decls))}")
        return
    for port in CANONICAL_PORTS:
        direction, width = decls[port]
        if direction != CANONICAL_DIRECTIONS[port]:
            errors.append(f"Port {port} direction must be {CANONICAL_DIRECTIONS[port]}, found {direction}")
        if width != CANONICAL_WIDTHS[port]:
            errors.append(f"Port {port} width must be {CANONICAL_WIDTHS[port]}, found {width}")


def check_forbidden_arithmetic(module_body: str, errors: list[str]) -> None:
    scan = ATTRIBUTE_RE.sub("", module_body)
    for pattern in FORBIDDEN_BEHAVIORAL_PATTERNS:
        if pattern.search(scan):
            errors.append("Behavioral always block is not allowed in candidate top module")
            break
    for pattern in FORBIDDEN_OPERATOR_PATTERNS:
        if pattern.search(scan):
            op = "*" if "*" in pattern.pattern else "+"
            errors.append(f"Forbidden arithmetic operator detected in top module: {op}")


def collect_instantiations(module_body: str) -> list[str]:
    instances: list[str] = []
    skip_prefixes = {"module", "input", "output", "inout", "wire", "reg", "logic", "assign"}
    for match in INSTANTIATION_RE.finditer(module_body):
        cell = match.group(1)
        if cell in skip_prefixes:
            continue
        instances.append(cell)
    return instances


def check_cells(module_body: str, allowlist: set[str], errors: list[str]) -> None:
    cells = collect_instantiations(module_body)
    if not cells:
        errors.append("Top module has no cell instantiations")
        return
    disallowed = sorted({c for c in cells if c not in allowlist})
    if disallowed:
        errors.append(
            "Found cell/module instantiations not present in allowlist: "
            + ", ".join(disallowed)
        )


def check_basic_top_validation(module: ModuleInfo, errors: list[str]) -> None:
    if re.search(r"\bblackbox\b", module.body, re.I):
        errors.append("Top module appears to be marked as blackbox")
    if re.search(r"\binout\b", module.body):
        errors.append("inout ports are not allowed in candidate top module")


def run_checks(netlist_path: pathlib.Path, allowlist_path: pathlib.Path | None) -> tuple[bool, list[str]]:
    raw = netlist_path.read_text(encoding="utf-8")
    text = strip_comments(raw)
    modules = parse_modules(text)
    errors: list[str] = []

    top_modules = [m for m in modules if m.name == CANONICAL_TOP]
    if len(top_modules) != 1:
        errors.append(f"Expected exactly one top module named {CANONICAL_TOP}, found {len(top_modules)}")
        return False, errors
    top = top_modules[0]

    allowlist = load_allowlist(allowlist_path)
    check_interface(top, errors)
    check_basic_top_validation(top, errors)
    check_forbidden_arithmetic(top.body, errors)
    check_cells(top.body, allowlist, errors)
    return not errors, errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Contract checker for candidate structural netlists."
    )
    parser.add_argument("netlist", type=pathlib.Path, help="Candidate netlist Verilog file")
    parser.add_argument(
        "--allowlist",
        type=pathlib.Path,
        help="Optional allowed primitive/cell list file (one cell per line)",
    )
    parser.add_argument(
        "--liberty",
        help="Colon-separated liberty file list used to derive an allowed cell set",
    )
    return parser.parse_args(argv)


def resolve_default_liberty_bundle() -> str | None:
    existing = [str(pathlib.Path(path)) for path in DEFAULT_REPO_LIBERTIES if pathlib.Path(path).exists()]
    if not existing:
        return None
    return ":".join(existing)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    liberty_arg = args.liberty or resolve_default_liberty_bundle()
    if liberty_arg:
        derived_allowlist = load_allowlist_from_liberties(liberty_arg)
        tmp_allowlist = pathlib.Path("/tmp/candidate_allowlist.txt")
        tmp_allowlist.write_text(
            "\n".join(sorted(derived_allowlist)) + "\n", encoding="utf-8"
        )
        allowlist = tmp_allowlist
    else:
        allowlist = args.allowlist if (args.allowlist and args.allowlist.exists()) else None
    ok, errors = run_checks(args.netlist, allowlist)
    if ok:
        print(f"PASS: {args.netlist}")
        return 0
    print(f"FAIL: {args.netlist}")
    for error in errors:
        print(f" - {error}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
