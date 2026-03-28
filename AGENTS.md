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

- `rtl/`: baseline and candidate DUT netlists/RTL
- `syn/`: baseline synthesis flow (Genus Tcl)
- `check/`: candidate legality checks
- `sim/`: simulation driver and testbench flow
- `eval/`: timing/area runners and report parsers
- `env/`: default config and environment setup
- `tech/`: ASAP7 libs/LEFs and related tech assets
- `docs/`: user-facing guides and contract docs
- `Makefile`: top-level orchestrator for baseline/candidate flows

## Role Dispatch

- Main agent: read `scheduler.md`
- Worker/sub-agent: read `worker.md`
