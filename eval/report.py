"""Atomic single-run result serialization; no scoring or historical ranking."""
import csv
from common import write_json


def finish(result, output, config):
    stages = result["stages"]
    result["validity"] = "not_established"
    result["constraints"] = {"timing": "not_run", "area": "not_set"}
    result["pass"] = False
    if result["execution_status"] == "completed":
        if all(stages.get(s, {}).get("status") == "pass" for s in ("check", "sim", "timing", "area")):
            result["validity"] = "valid"
            metrics = result["metrics"]
            result["constraints"]["timing"] = (
                "pass" if metrics["wns_ns"] >= config["limits"]["min_wns_ns"] else "fail")
            limit = config["limits"]["max_area_um2"]
            if limit is not None:
                result["constraints"]["area"] = "pass" if metrics["area_um2"] <= limit else "fail"
            result["pass"] = "fail" not in result["constraints"].values()
        elif result.get("failed_stage"):
            result["validity"] = "invalid"
    write_json(output / "summary.json", result)
    with (output / "summary.csv").open("w", newline="") as stream:
        row = {"execution_status": result["execution_status"], "validity": result["validity"],
               "pass": result["pass"], "failed_stage": result.get("failed_stage"),
               **(result["metrics"] or {})}
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
