---
name: mac-eval
description: 在 mac-agent 仓库运行 MAC 正确性仿真、Genus 综合、OpenROAD timing/area 评估，或排查相关报告与评估流程。
---

# MAC 评估

在仓库根目录操作；流程实现与默认配置分别在 `eval/Makefile`、`eval/config.mk`。

- 运行评估、重新综合或切换 DUT 时，读 [评估流程](references/baseline_flow_zh.md)。
- 分析关键路径或指定端点查询时，读 [Timing 排查](references/timing_debug_guide_zh.md)。
- 分析 cell、层次或实例组面积时，读 [Area 排查](references/area_debug_guide_zh.md)。

默认评估 `rtl/baseline/baseline.synth.v`；`rtl/baseline/baseline.v` 是可参数化的综合源文件。`make all` 不调用综合或生成器。`make syn` 的输出位于运行目录，后续评估须显式用 `DUT` 指向该网表。

比较设计时保持工艺库、位宽、流水级、时序约束和仿真配置一致。固定 baseline 网表只对应 unsigned 16×16→32、组合逻辑；修改配置不会改变已保存网表的结构。

区分仿真通过、时序达标和工具执行成功。报告结论时给出 DUT、配置、结果路径、正确性、延迟和面积；缺失的评估项明确说明。历史记录 `eval/history/` 是留档，不代表当前工作区结果。
