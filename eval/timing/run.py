"""OpenSTA measurement and optional path diagnostics; all units are ns."""
import math
from pathlib import Path
import re

from common import ROOT, EvaluationError, execute, tool


def timing(dut, out, config, query=None):
    out.mkdir(parents=True)
    settings = config["timing"]
    sdc = out / "constraints.sdc"
    sdc.write_text(f"create_clock -name VCLK -period {settings['period_ns']}\n"
                   f"set_input_delay {settings['input_delay_ns']} -clock VCLK [get_ports {{A[*] B[*] C[*]}}]\n"
                   f"set_output_delay {settings['output_delay_ns']} -clock VCLK [get_ports {{D[*]}}]\n")
    env = {
        "NETLIST_PATH": dut, "LIBERTY_PATHS": ":".join(str(ROOT / p) for p in config["liberty"]),
        "SDC_PATH": sdc, "TOP_MODULE": config["top"],
        "TIMING_SUMMARY_REPORT": out / "timing_summary.rpt",
        "CRITICAL_PATH_REPORT": out / "critical_path.rpt",
        # Always score the full design; filtered queries are separate diagnostics.
        "TIMING_QUERY_MAX_PATHS": 1, "TIMING_QUERY_ENDPOINT_COUNT": "",
        "TIMING_QUERY_FROM": "", "TIMING_QUERY_TO": "", "TIMING_QUERY_OUTPUT_REPORT": "",
    }
    command = [tool("sta", config), "-no_init", "-exit", ROOT / "eval/timing/openroad_sta.tcl"]
    execute(command, out / "sta.log", config["timeouts_sec"]["timing"], cwd=out, env=env)
    log = (out / "sta.log").read_text()
    if re.search(r"(?m)^Error[: ]", log):
        raise EvaluationError("OpenSTA reported an error; see timing/sta.log")
    text = (out / "timing_summary.rpt").read_text()
    metrics = {}
    for key, pattern in {
        "wns_ns": r"(?m)^worst slack\s+([-+\d.eE]+)",
        "tns_ns": r"(?m)^tns\s+([-+\d.eE]+)",
        "arrival_time_ns": r"(?m)^arrival_time_ns=([-+\d.eE]+)",
    }.items():
        match = re.search(pattern, text)
        if not match or not math.isfinite(float(match[1])):
            raise EvaluationError(f"Missing or invalid timing metric: {key}")
        metrics[key] = float(match[1])
    if metrics["arrival_time_ns"] < 0:
        raise EvaluationError("Invalid negative arrival time")
    metrics["input_external_delay_ns"] = settings["input_delay_ns"]
    metrics["measurement"] = "pre_layout_no_extracted_parasitics"
    if query:
        env.update({"TIMING_QUERY_MAX_PATHS": query.get("max_paths", 1),
                    "TIMING_QUERY_FROM": query.get("from", ""), "TIMING_QUERY_TO": query.get("to", ""),
                    "TIMING_QUERY_OUTPUT_REPORT": out / "query_paths.rpt",
                    "TIMING_SUMMARY_REPORT": out / "query_summary.rpt"})
        execute(command, out / "query.log", config["timeouts_sec"]["timing"], cwd=out, env=env)
        if re.search(r"(?m)^Error[: ]", (out / "query.log").read_text()):
            raise EvaluationError("OpenSTA query failed; see timing/query.log")
    return metrics
