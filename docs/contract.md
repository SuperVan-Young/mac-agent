# Integer MAC Framework Contract

## Scope

This document defines the shared interface and artifact contract for the integer MAC evaluation framework.

All baseline, candidate, simulation, evaluation, and reporting flows must comply with this contract.

## Functional Definition

The target function is:

```text
D = A * B + C
```

Signal semantics for the first implementation are fixed as `unsigned`.

Bit widths are fixed as:

- `A`: 16-bit
- `B`: 16-bit
- `C`: 32-bit
- `D`: 32-bit

The mathematical reference model is:

```text
D = ((unsigned(A) * unsigned(B)) + unsigned(C)) mod 2^32
```

## Top-Level Interface

The canonical top-level module name is:

```text
mac16x16p32
```

The canonical port list is:

```verilog
module mac16x16p32 (
    input  [15:0] A,
    input  [15:0] B,
    input  [31:0] C,
    output [31:0] D
);
```

The first framework version assumes a combinational design.

There is no clock or reset in the canonical interface.

## Design Categories

Two design categories are supported:

1. Baseline RTL
   - Source file: `rtl/baseline.v`
   - Purpose: simple reference RTL used to derive a mapped baseline netlist through Genus.

2. Candidate netlist
   - Source file pattern: `rtl/candidate_<tag>.v`
   - Purpose: Agent-produced structural Verilog that is evaluated directly without Genus remapping.

## Candidate Rules

Candidate designs must satisfy all of the following rules:

- The top-level module name must be `mac16x16p32`.
- The top-level ports and widths must exactly match the canonical interface.
- The design must be structural Verilog or restricted gate-level Verilog.
- The design must not rely on Genus to infer arithmetic structure.
- The design must not contain behavioral multiplication or addition in the DUT body.
- The design must only instantiate allowed primitives or cells present in the target liberty allowlist.

Disallowed constructs inside candidate DUT logic include:

- `*`
- high-level arithmetic `+` used to implement the datapath
- inferred `always` blocks implementing combinational arithmetic

Allowed non-datapath wrappers are limited to trivial net assignments needed for port hookup.

## Baseline Outputs

The baseline Genus flow must generate:

- `syn/outputs/baseline_mapped.v`
- `syn/reports/baseline_timing.rpt`
- `syn/reports/baseline_area.rpt`

These outputs are regenerated only when the library, constraints, or baseline RTL changes.

## Simulation Contract

Simulation flows under `sim/` must:

- accept a DUT file path
- compile against the canonical top-level interface
- use the unsigned reference model defined in this document
- produce an explicit pass/fail result

The minimum failure payload must include:

- DUT name
- vector index or test case name
- `A`
- `B`
- `C`
- expected `D`
- observed `D`

## Evaluation Contract

Evaluation flows under `eval/` must:

- be separate from `sim/`
- accept a netlist path, liberty path, and constraint path
- analyze both baseline mapped netlists and candidate netlists through the same interface

The minimum timing outputs are:

- timing status
- WNS
- TNS when available
- critical path delay when derivable

The minimum area outputs are:

- total area
- cell count

## Results Layout

Per-design result directories must use:

```text
results/<design_name>/
```

Recommended examples:

- `results/baseline/`
- `results/candidate_adder_tree_a/`

The minimum machine-readable summary files are:

- `results/<design_name>/summary.json`
- optional `results/<design_name>/summary.csv`

## Summary Schema

Every summary record must include these fields:

- `design_name`
- `design_type`
- `correctness`
- `timing_status`
- `wns`
- `tns`
- `critical_delay`
- `area`
- `cell_count`
- `sim_runtime_sec`
- `eval_runtime_sec`
- `total_runtime_sec`

Suggested values:

- `design_type`: `baseline` or `candidate`
- `correctness`: `pass`, `fail`, or `not_run`
- `timing_status`: `pass`, `fail`, or `not_run`

## Naming Rules

- Baseline RTL file name is fixed: `baseline.v`
- Candidate file name pattern is fixed: `candidate_<tag>.v`
- The `<tag>` must contain only lowercase letters, digits, and underscores
- Report file names should be stable and deterministic

## Acceptance Checks

Any implementation claiming compliance with this contract must pass the following checks:

1. The top-level interface exactly matches `mac16x16p32(A, B, C, D)`.
2. The unsigned reference model is used consistently in simulation.
3. Baseline output paths match the fixed `syn/outputs` and `syn/reports` naming rules.
4. Candidate designs can enter simulation and evaluation without any Genus remapping step.
5. Result summaries expose the full required schema.
