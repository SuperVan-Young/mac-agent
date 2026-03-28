# Area 调试接口

本文档给 AI/worker 使用，说明如何使用 `make area-debug` 查看更细的面积贡献报告。

## 默认行为

默认 `make area` 只生成调度和汇总需要的基础产物：

- `results/fixed/eval_sta/design_area.rpt`
- `results/fixed/eval_sta/cell_usage.rpt`
- `results/fixed/area.json`

其中 `area.json` 仍然只包含总面积、utilization、cell usage count 和总 cell count，适合做固定指标比较。

## 什么时候开细分分析

只有在下面这些场景，才建议 AI 跑 `make area-debug`：

- 总 area 变差了，但不知道是哪些 cell 或哪类逻辑导致
- 想判断优化是不是把面积集中推到了某一簇实例
- 想做定性分析，给下一轮优化提供方向，而不是只看单个总数值

## 基本调用

需要详细 area 报告时，直接在仓库根目录执行：

```bash
make area-debug
```

如果要分析 baseline 或非默认 netlist，和 `make area` 一样覆盖变量即可，例如：

```bash
make area-debug DESIGN_NAME=baseline DESIGN_TYPE=baseline DUT=$(pwd)/rtl/baseline.v CHECK_ENABLE=0
```

## 额外产物

开启细分分析后，除了基础 area 报告，还会得到：

- `instance_area.csv`
  逐实例导出的 `inst_name, master_name`
- `cell_area_breakdown.rpt`
  按 cell type 聚合的 `count/unit_area/total_area/ratio_percent`
- `module_area_breakdown.rpt`
  按 Verilog hierarchy 聚合的模块面积贡献
- `instance_group_area_breakdown.rpt`
  扁平网表下，按实例名前缀启发式聚合的面积贡献
- `area.json`
  同时包含基础字段和 `top_cells`、`top_modules`、`top_instance_groups`

## 如何解读结果

### 1. 先看 `cell_area_breakdown.rpt`

如果面积大头集中在某几种 cell：

- `XNOR/XOR/FA/HA/MAJ` 很大：通常说明算术结构本身占主导
- `BUF/INV` 很大：通常说明驱动、扇出或综合修复代价高
- `DFF` 很大：通常说明流水级数或寄存策略带来主要面积

### 2. 再看 `module_area_breakdown.rpt`

只有当网表保留层次时，这个报告才可靠。

如果文件里写的是：

```text
No hierarchical module instances found in the input netlist.
```

说明当前网表已经基本扁平化，不能再把模块贡献当成严格层次结果来解释。

### 3. 扁平网表看 `instance_group_area_breakdown.rpt`

这个报告是启发式的，不是严格 hierarchy。

适合回答这类问题：

- 是不是某一组实例名前缀特别大
- 某轮优化后，是不是面积集中堆到了某个局部簇

不适合回答这类问题：

- 某个 RTL module 的精确面积是多少

## 推荐给 AI 的分析顺序

1. 先跑默认 `make area`，确认总 area 指标变化
2. 如果需要解释变化原因，再跑 `make area-debug`
3. 先看 `cell_area_breakdown.rpt` 找主要面积来源
4. 如果网表有层次，再看 `module_area_breakdown.rpt`
5. 如果网表扁平，就改看 `instance_group_area_breakdown.rpt`
6. 输出结论时明确区分：
   - 这是严格 cell type 统计
   - 这是 hierarchy 模块统计
   - 这是实例名前缀启发式统计

## 适用场景

- 默认总面积指标不够解释问题
- 想给下一轮结构优化提供方向
- 想判断面积增长来自算术逻辑、寄存器，还是综合插入的辅助单元
