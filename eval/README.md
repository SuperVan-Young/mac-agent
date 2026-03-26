# STA Eval Flow (Task 05)

This directory provides a minimal STA evaluation flow that is decoupled from `sim/`.

## Entry Script

`run_timer.sh` accepts a generic interface:

- `--netlist <path>`
- `--liberty <path>`
- `--sdc <path>`

Optional flags:

- `--out-dir <path>` (default: `results/<netlist_basename>/eval_sta`)
- `--top <module>` (default: `mac16x16p32`)
- `--tool auto|openroad|opentimer`
- `--conda-prefix <path>` (default: `/tmp/mac-agent-openroad-env`)
- `--timeout-sec <n>` (default: `90`)
- `--dry-run`

## Outputs

Stable report names under output directory:

- `timing_summary.rpt`
- `critical_path.rpt`
- `sta.log`

## Environment

Conda environment template and setup helper are under `env/`:

Example:

```bash
./env/setup_openroad_conda.sh
```

`run_timer.sh` resolves OpenROAD in this order:
1. `openroad` in current `PATH` (activated env supported)
2. `conda run -p /tmp/mac-agent-openroad-env openroad` (or custom `--conda-prefix`)

## Example

```bash
./eval/run_timer.sh \
  --netlist syn/outputs/baseline_mapped.v \
  --liberty path/to/tech.lib \
  --sdc eval/templates/minimal.sdc \
  --tool auto \
  --conda-prefix /tmp/mac-agent-openroad-env
```
