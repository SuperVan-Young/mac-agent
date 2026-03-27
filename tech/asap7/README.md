# ASAP7 Minimal Tech Drop

This directory vendors a minimal ASAP7 technology subset for this repository's
current synthesis/evaluation flows.

## Why This Exists

The locally installed `litex-hub::openroad` conda package provides the OpenROAD
binary, but does not include ASAP7 technology collateral (liberty/lef/verilog
tech files). This was verified locally from:

- `/tmp/mac-agent-openroad-env/conda-meta/openroad-*.json` package file lists
- direct file search under `/tmp/mac-agent-openroad-env`

## Source of Truth

Sourced from the official OpenROAD-flow-scripts ASAP7 platform provided locally:

- `/tmp/openroad-flow-scripts-asap7/flow/platforms/asap7`

## Included Subset

For current eval/synthesis needs, we vendor one RVT TT NLDM liberty bundle:

- `lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib`
- `lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib`
- `lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib`
- `lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib`
- `lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib`

These files are used together as the default repo-local ASAP7 bundle for
Genus synthesis and OpenROAD timing evaluation.

For OpenROAD area analysis, we also vendor a minimal LEF set:

- `lef/asap7_tech_1x_201209.lef`
- `lef/asap7sc7p5t_28_L_1x_220121a.lef`
- `lef/asap7sc7p5t_28_R_1x_220121a.lef`
- `lef/asap7sc7p5t_28_SL_1x_220121a.lef`
- `lef/asap7sc7p5t_DFFHQNH2V2X.lef`
- `lef/asap7sc7p5t_DFFHQNV2X.lef`
- `lef/asap7sc7p5t_DFFHQNV4X.lef`

The bundle is sourced from ASAP7 NLDM libraries:

- `asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz`
- `asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz`
- `asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz`
- `asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz`
- `asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib`

No full ASAP7 platform tree is vendored here.
