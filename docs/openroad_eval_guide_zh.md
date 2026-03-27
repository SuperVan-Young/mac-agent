# OpenROAD/OpenSTA 评估指南

## 目标

对综合网表或 candidate 网表做开源时序分析和面积统计。
当前默认通过 OpenROAD conda 环境中的 `sta` 执行时序分析。

## 环境准备

安装或检查 OpenROAD conda 环境：

```bash
bash env/setup_openroad_conda.sh
```

如果环境已安装，只检查：

```bash
bash env/setup_openroad_conda.sh --prefix /tmp/mac-agent-openroad-env --skip-install
```

## 默认工艺库

当前默认使用 repo-local ASAP7 TT/RVT liberty bundle：

- `tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib`
- `tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib`
- `tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib`
- `tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib`
- `tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib`

## STA 基本用法

```bash
bash eval/run_timer.sh \
  --netlist syn/outputs/baseline_mapped.v \
  --sdc eval/templates/minimal.sdc
```

## Dry run

```bash
bash eval/run_timer.sh \
  --netlist syn/outputs/baseline_mapped.v \
  --sdc eval/templates/minimal.sdc \
  --dry-run
```

## 输出

默认输出目录：

```text
results/<netlist_basename>/eval_sta/
```

主要文件：

- `timing_summary.rpt`
- `critical_path.rpt`
- `sta.log`

## 面积统计

```bash
python3 eval/area_report.py \
  --netlist syn/outputs/baseline_mapped.v \
  --liberty tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib:tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib \
  --out results/baseline/area.json
```

## 统一汇总

```bash
python3 eval/parse_reports.py \
  --design-name baseline \
  --design-type baseline \
  --sim-log results/baseline/sim.log \
  --timing-summary syn/reports/baseline_timing.rpt \
  --area-json results/baseline/area.json \
  --results-dir results/baseline \
  --write-csv
```

`timing_summary.rpt` 会输出 `wns/tns/critical_delay`，可直接被 `parse_reports.py` 汇总。
