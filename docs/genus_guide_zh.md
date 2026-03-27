# Genus 综合指南

## 目标

对 baseline RTL 做综合，生成参考门级网表和报告。

当前脚本：

- [syn/run.tcl](/home/xuechenhao/mac-agent/syn/run.tcl)

## 默认输入

- RTL：`rtl/baseline.v`
- 顶层：`mac16x16p32`
- 工艺库：repo-local ASAP7 TT/RVT liberty bundle

## 基本用法

```bash
genus -no_gui -files syn/run.tcl
```

## Dry run

只检查脚本解析和默认路径，不真正综合：

```bash
GENUS_DRY_RUN=1 tclsh syn/run.tcl
```

## 可覆盖环境变量

- `GENUS_TOP`
- `GENUS_RTL`
- `GENUS_LIB`
- `GENUS_CLK_PERIOD`
- `GENUS_A_WIDTH`
- `GENUS_B_WIDTH`
- `GENUS_ACC_WIDTH`
- `GENUS_PIPELINE_CYCLES`
- `GENUS_OUT_DIR`
- `GENUS_RPT_DIR`

例如：

```bash
GENUS_CLK_PERIOD=0.8 genus -no_gui -files syn/run.tcl
```

位宽和流水示例：

```bash
GENUS_A_WIDTH=16 \
GENUS_B_WIDTH=16 \
GENUS_ACC_WIDTH=32 \
GENUS_PIPELINE_CYCLES=1 \
genus -no_gui -files syn/run.tcl
```

## 默认输出

- `syn/outputs/baseline_mapped.v`
- `syn/reports/baseline_timing.rpt`
- `syn/reports/baseline_area.rpt`

## 当前已验证

本机已真实跑通一次 baseline 综合，当前结果可在以下路径查看：

- [syn/outputs/baseline_mapped.v](/home/xuechenhao/mac-agent/syn/outputs/baseline_mapped.v)
- [syn/reports/baseline_timing.rpt](/home/xuechenhao/mac-agent/syn/reports/baseline_timing.rpt)
- [syn/reports/baseline_area.rpt](/home/xuechenhao/mac-agent/syn/reports/baseline_area.rpt)

## 当前 baseline 参考结果

- Cell area: `152.930`
- 最差 slack: `-376 ps`
