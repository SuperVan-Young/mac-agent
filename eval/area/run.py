"""OpenROAD cell area measurement and optional detailed diagnostics."""
import json
import math
import sys

from common import ROOT, EvaluationError, execute, tool


def area(dut, out, config, detail=False):
    out.mkdir(parents=True)
    env = {"NETLIST_PATH": dut, "TOP_MODULE": config["top"],
           "LIBERTY_PATHS": ":".join(str(ROOT / p) for p in config["liberty"]),
           "LEF_PATHS": ":".join(str(ROOT / p) for p in config["lef"]),
           "AREA_DETAIL_ENABLE": int(detail), "AREA_INSTANCE_CSV": out / "instance_area.csv"}
    log = out / "openroad.log"
    execute([tool("openroad", config), "-no_init", "-exit", "-log", log,
             ROOT / "eval/area/openroad_area.tcl"], out / "console.log",
            config["timeouts_sec"]["area"], cwd=out, env=env)
    args = [sys.executable, ROOT / "eval/area/openroad_area_report.py",
            "--openroad-log", log, "--design-area-rpt", out / "design_area.rpt",
            "--cell-usage-rpt", out / "cell_usage.rpt", "--out", out / "area.json"]
    if detail:
        args += ["--detail", "--netlist", dut, "--liberty-paths", env["LIBERTY_PATHS"],
                 "--top-module", config["top"], "--instance-area-csv", out / "instance_area.csv",
                 "--cell-area-rpt", out / "cell_area_breakdown.rpt",
                 "--module-area-rpt", out / "module_area_breakdown.rpt",
                 "--group-area-rpt", out / "instance_group_area_breakdown.rpt"]
    execute(args, out / "parse.log", config["timeouts_sec"]["area"], cwd=out)
    result = json.loads((out / "area.json").read_text())
    value = result.get("area")
    if (result.get("status") != "ok" or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0 or result.get("cell_count", 0) <= 0):
        raise EvaluationError("Missing or invalid area metrics")
    return {"area_um2": value, "cell_count": result["cell_count"]}
