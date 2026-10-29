"""Validate a self-contained, PDK-mapped combinational MAC using Yosys IR."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import ROOT, EvaluationError, execute, tool, yosys_quote


def check_netlist(dut, out, config):
    out.mkdir(parents=True)
    raw = dut.read_text()
    # These lexical exclusions prevent external inputs and tool-dependent preprocessing.
    # Syntax, operators, hierarchy, pin types and connectivity are checked on Yosys IR.
    source = re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*',
                    lambda m: m.group() if m.group().startswith('"') else ' ', raw, flags=re.S)
    if '`' in source or re.search(r'\$[A-Za-z_]', source):
        raise EvaluationError("Candidate must be self-contained: no directives or system functions/tasks", "invalid")
    timeout = config["timeouts_sec"]["check"]
    yosys = tool("yosys", config)
    library = out / "library.json"
    all_library = out / "all_library.json"
    library_script = out / "library.ys"
    library_script.write_text("\n".join(
        f"read_liberty -lib {yosys_quote(ROOT / name)}"
        for name in config["liberty"]
    ) + f"\nwrite_json {yosys_quote(all_library)}\ndesign -reset\n" + "\n".join(
        f"read_liberty -lib {yosys_quote(ROOT / name)}"
        for name in config["liberty"][:config["combinational_liberty_count"]]
    ) + f"\nwrite_json {yosys_quote(library)}\n")
    execute([yosys, "-Q", "-T", "-s", library_script], out / "library.log", timeout, cwd=out)
    allowed = json.loads(library.read_text())["modules"]
    parsed = out / "candidate.json"
    script = out / "parse.ys"
    script.write_text(f"read_verilog -noautowire -nosynthesis {yosys_quote(dut)}\n"
                      f"write_json {yosys_quote(parsed)}\n")
    execute([yosys, "-Q", "-T", "-s", script], out / "parse.log", timeout, cwd=out, failure="invalid")
    modules = json.loads(parsed.read_text())["modules"]
    collisions = set(modules) & set(json.loads(all_library.read_text())["modules"])
    if collisions:
        raise EvaluationError(f"Candidate redefines PDK cells: {sorted(collisions)}", "invalid")
    top = modules.get(config["top"])
    if top is None:
        raise EvaluationError("Missing canonical top module", "invalid")
    actual_ports = {name: [port["direction"], len(port["bits"])] for name, port in top["ports"].items()}
    if actual_ports != config["ports"] or any(p.get("signed", 0) for p in top["ports"].values()):
        raise EvaluationError(f"Expected unsigned MAC interface; found {actual_ports}", "invalid")
    visited = set()

    def visit(name, stack):
        if name in stack:
            raise EvaluationError("Recursive module hierarchy", "invalid")
        if name in visited:
            return
        mod = modules[name]
        if any(int(str(mod.get("attributes", {}).get(a, "0")), 2)
               for a in ("blackbox", "whitebox")):
            raise EvaluationError(f"Candidate-defined blackbox/whitebox: {name}", "invalid")
        if mod.get("memories"):
            raise EvaluationError("Memories are not mapped combinational cells", "invalid")
        for net in mod.get("netnames", {}).values():
            if "init" in net.get("attributes", {}):
                raise EvaluationError("Initial state is not permitted", "invalid")
            if any(bit in ("x", "z") for bit in net["bits"]):
                raise EvaluationError("X/Z constants are not permitted", "invalid")
        for cell in mod.get("cells", {}).values():
            kind = cell["type"]
            if kind in modules:
                visit(kind, (*stack, name))
            elif kind not in allowed:
                raise EvaluationError(f"Unmapped or unsupported cell: {kind}", "invalid")
            else:
                if cell.get("parameters"):
                    raise EvaluationError(f"PDK cell parameters are not permitted: {kind}", "invalid")
                pins = allowed[kind]["ports"]
                if set(cell["connections"]) != set(pins):
                    raise EvaluationError(f"PDK pin set mismatch: {kind}", "invalid")
                for pin, bits in cell["connections"].items():
                    if len(bits) != len(pins[pin]["bits"]) or any(b in ("x", "z") for b in bits):
                        raise EvaluationError(f"Invalid PDK pin connection: {kind}.{pin}", "invalid")
        visited.add(name)

    visit(config["top"], ())
    mapped = out / "mapped.v"
    script = out / "validate.ys"
    script.write_text(f"read_json {yosys_quote(library)}\nread_json {yosys_quote(parsed)}\n"
                      f"hierarchy -check -top {config['top']}\nflatten\n"
                      "check -mapped -assert\nscc -all_cell_types -expect 0\n"
                      f"write_verilog -noattr -noexpr {yosys_quote(mapped)}\n")
    execute([yosys, "-Q", "-T", "-s", script], out / "validate.log", timeout, cwd=out, failure="invalid")
    return mapped
