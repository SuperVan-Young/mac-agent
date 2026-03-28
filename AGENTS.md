# Agent Entry

## Environment Setup

1. Install/check the OpenROAD conda environment:
   - `bash env/setup_conda.sh`
   - or `bash env/setup_conda.sh --prefix /tmp/mac-agent-openroad-env --skip-install`
   - Python-side dependencies such as `xdsl` are installed from the repo-root `requirements.txt`
2. Ensure common tools are available in `PATH`:
   - `python3`, `iverilog`, `vvp`, `conda`
3. Baseline synthesis additionally requires:
   - `genus` (only for `DESIGN_TYPE=baseline` synthesis flow)

## How To Run Tests

- Full candidate evaluation:
  - `make clean && make all`
- Generate candidate RTL only:
  - `make generate`
  - default generated DUT: `results/fixed/generated/mac16x16p32.v`
- Full baseline evaluation:
  - `make clean && make all DESIGN_NAME=baseline DESIGN_TYPE=baseline DUT=$(pwd)/rtl/baseline.v CHECK_ENABLE=0`
- Common partial targets:
  - `make check`
  - `make sim`
  - `make timing`
  - `make area`

All workflow defaults come from `env/config.mk` and can be overridden with CLI vars or `CONFIG=<path>`.

## Project Motivation

This repository evaluates and iterates integer MAC implementations for:

- Function: `D = A * B + C`
- Canonical top: `mac16x16p32`
- Candidate contract: fixed unsigned `16x16 -> 32` interface
- Baseline path: configurable width/pipeline, synthesized by Genus, then compared with the same eval stack

The goal is reproducible quality comparison across correctness, timing, and area.

## Code Architecture

- `rtl/`: baseline RTL plus candidate RTL generator/compiler sources
- `eval/check/`: candidate legality checks
- `eval/sim/`: simulation driver, vector generator, and testbench
- `eval/syn/`: baseline synthesis flow (Genus Tcl)
- `eval/timing/`: timing analysis wrappers and OpenSTA templates
- `eval/area/`: area analysis wrappers and report parsers
- `eval/summary/`: summary/report aggregation
- `env/`: default config and environment setup
- `tech/`: ASAP7 libs/LEFs and related tech assets
- `agents/`: model role definitions and AI-facing debug guides
  - `agents/roles/`: scheduler/worker/refactor role specs
  - `agents/guides/`: AI-facing debug guides
- `docs/`: user-facing guides and compiler docs
- `Makefile`: top-level orchestrator for baseline/candidate flows

## Role Dispatch

- Main agent: read `agents/roles/scheduler.md`
- Worker/sub-agent: read `agents/roles/worker.md`
