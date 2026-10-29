"""Shared process execution, immutable run directories, and provenance."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


class EvaluationError(Exception):
    def __init__(self, message, status="error"):
        super().__init__(message)
        self.status = status


def load_config(path=None):
    return json.loads(Path(path or ROOT / "eval/config.json").read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temp.replace(path)


def new_run(output=None):
    path = Path(output).resolve() if output else ROOT / "results" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
    )
    path.mkdir(parents=True, exist_ok=False)
    return path


def tool(name, config):
    # Preserve the existing simulation tool choice: PATH Icarus first.
    prefix = Path(config["tool_prefix"]) / "bin" / name
    found = shutil.which(name) if name in {"iverilog", "vvp", "genus"} else None
    if found:
        return found
    if prefix.is_file():
        return str(prefix)
    found = shutil.which(name)
    if not found:
        raise EvaluationError(f"Tool unavailable: {name}; run env/setup_conda.sh")
    return found


def execute(args, log, timeout, cwd=None, env=None, failure="error"):
    """Bound the entire process group; keep diagnostics even on failure."""
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    process_env = os.environ.copy()
    if env:
        process_env.update({key: str(value) for key, value in env.items()})
    started = time.monotonic()
    with log.open("w") as stream:
        try:
            proc = subprocess.Popen([str(a) for a in args], cwd=cwd, env=process_env,
                                    stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as exc:
            raise EvaluationError(str(exc)) from exc
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            raise EvaluationError(f"Timeout after {timeout}s; see {log}", "timeout") from exc
    if code:
        raise EvaluationError(f"Process exited {code}; see {log}", failure)
    return time.monotonic() - started


def provenance(config):
    files = {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "eval").rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts}
    assets = list(config["liberty"]) + list(config["lef"])
    assets += [str(p.relative_to(ROOT)) for p in sorted((ROOT / "tech/asap7/verilog").rglob("*.v"))]
    pdk = {name: digest(ROOT / name) for name in assets}
    return {"harness_files": files, "pdk_files": pdk,
            "config_sha256": hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()}


def yosys_quote(path):
    return json.dumps(str(path))
