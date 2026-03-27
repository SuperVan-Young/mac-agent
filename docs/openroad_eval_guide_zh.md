# Timing 评估指南

## 目标

对综合网表或 candidate 网表做时序分析和面积统计。
推荐入口是仓库根目录的 `Makefile`。

## 环境准备

安装或检查 OpenROAD conda 环境：

```bash
bash env/setup_openroad_conda.sh
```

如果环境已安装，只检查：

```bash
bash env/setup_openroad_conda.sh --prefix /tmp/mac-agent-openroad-env --skip-install
```

## 默认配置

项目默认超参数放在：

- [env/config.mk](/home/xuechenhao/mac-agent/env/config.mk)

其中包括：

- conda 环境路径
- 顶层模块名
- 目标周期
- 输入输出 delay
- 默认 liberty bundle
- 默认输入输出路径

如果要复现实验，可额外准备一份覆盖配置：

```bash
make all CONFIG=archive/<tag>/config.mk
```

## 默认工艺库

当前默认使用 repo-local ASAP7 TT/RVT liberty bundle：

- `tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib`
- `tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib`
- `tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib`
- `tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib`
- `tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib`

OpenROAD 面积分析还会读取 repo-local ASAP7 LEF：

- `tech/asap7/lef/asap7_tech_1x_201209.lef`
- `tech/asap7/lef/asap7sc7p5t_28_L_1x_220121a.lef`
- `tech/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef`
- `tech/asap7/lef/asap7sc7p5t_28_SL_1x_220121a.lef`

## Make 入口

完整评估：

```bash
make all
```

只跑 timing：

```bash
make timing
```

打印当前配置：

```bash
make print-config
```

## 底层 timing 入口

```bash
bash eval/run_timer.sh openroad
```

这个脚本通常不需要手工调用，由 `make timing` 负责注入环境变量。
项目不再维护单独的 `opentimer` 后端。

## 底层 area 入口

```bash
bash eval/run_area.sh
```

这个脚本通常不需要手工调用，由 `make area` 负责注入环境变量。

## 输出

默认输出目录：

```text
results/<netlist_basename>/eval_sta/
```

主要文件：

- `timing_summary.rpt`
- `critical_path.rpt`
- `sta.log`

## 面积统计（OpenROAD）

`make area` 会调用 OpenROAD，输出：

- `results/<design>/eval_sta/design_area.rpt`
- `results/<design>/eval_sta/cell_usage.rpt`
- `results/<design>/area.json`

`area.json` 中包含：

- `area`（OpenROAD `report_design_area` 总面积）
- `cell_breakdown`（OpenROAD `report_cell_usage` 分类统计）
- `cell_count`（分类统计求和）

说明：这条口径与“纯 liberty 单元面积求和”不同。
OpenROAD 结果依赖 LEF/库映射与工具统计方式，数值可用于同口径横向比较，但不要和旧的 liberty-sum 结果直接混比。

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
