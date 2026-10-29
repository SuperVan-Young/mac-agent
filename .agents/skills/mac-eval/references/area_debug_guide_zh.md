# Area 排查

```bash
python eval/run.py candidate.v --dev --stage area --area-detail
```

基础输出为 `area/area.json`、`area/design_area.rpt`、`area/cell_usage.rpt` 和 `area/openroad.log`。详细模式额外生成：

- `instance_area.csv`：实例到工艺单元的映射。
- `cell_area_breakdown.rpt`：按 cell type 聚合。
- `module_area_breakdown.rpt`：按保留的 Verilog 层次聚合。
- `instance_group_area_breakdown.rpt`：按实例命名前缀启发式聚合。

先看 cell type 的面积贡献，再看实例组。checker 会展开用户层次，因此正式测量的模块层次报告可能为空；不要把展开后的实例名前缀当成严格模块统计。没有层次并非评测失败。

XOR/FA/HA/MAJ 的贡献可帮助定位算术结构成本，BUF/INV 的贡献可提示扇出与驱动代价。总面积和详细归因分别来自 OpenROAD 与 Liberty；使用详细报告时留意面积单位和归一化方式。

默认面积上限未设置；area 数值有效不等于面积优于 baseline。
