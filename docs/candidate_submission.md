# Candidate Submission Contract (Task 07)

This document defines the submission and admission checks for candidate structural netlists, based on `docs/contract.md`.

## Scope

Candidate files are direct-evaluation DUT netlists and must not require DC remapping before simulation or STA/area evaluation.

## Required File/Form

- Candidate filename pattern: `rtl/candidate_<tag>.v`
- `<tag>` character set: lowercase letters, digits, `_`
- Netlist must contain exactly one top module named `mac16x16p32`

## Top Interface Requirements

The candidate top module must match:

```verilog
module mac16x16p32 (
    input  [15:0] A,
    input  [15:0] B,
    input  [31:0] C,
    output [31:0] D
);
```

Checks enforce:

- module name is exactly `mac16x16p32`
- top port order is exactly `A, B, C, D`
- declarations contain only `A/B/C/D` with exact direction and width
- no `inout`, no blackbox marker in top module

## Structural Restrictions

Candidate top logic must be structural/restricted gate-level Verilog:

- forbidden arithmetic operators in top body: `*`, `+`
- forbidden behavioral forms in top body: `always`, `always @`, `always_comb`, `always_ff`, `always_latch`
- trivial `assign` passthrough wiring is allowed if it does not use forbidden arithmetic

## Cell Allowlist Rules

Candidate top module can only instantiate cells/primitives in an allowlist:

- default allowlist file: `tools/allowed_cells.txt`
- can be overridden by CLI argument
- if any instantiated cell is not in allowlist, candidate is rejected

## Scripted Checks

Checker entry:

```bash
python3 tools/check_candidate_netlist.py <candidate.v>
```

Optional custom allowlist:

```bash
python3 tools/check_candidate_netlist.py <candidate.v> --allowlist <cells.txt>
```

Exit code:

- `0`: pass
- `1`: fail with explicit violation list
