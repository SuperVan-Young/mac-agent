# Task 06: Area And Reporting

## 目标

建立面积统计和统一结果汇总机制，把 correctness、timing、area、runtime 汇总成统一表格，供 agent 排名和筛选。

## 范围

本任务不负责生成 baseline，不负责跑仿真，不负责跑 STA；只负责消费这些流程的输出并统一整理。

## 输入

- `sim/` 产出的 pass/fail 结果
- `eval/` 产出的 timing 报告
- liberty 文件
- baseline 或 candidate 网表

## 输出

- `eval/area_report.py`
- `eval/parse_reports.py`
- 统一摘要文件，例如：
  - `results/<design>/summary.json`
  - `results/<design>/summary.csv`

## 设计要求

- 面积统计统一按 liberty 单元面积求和。
- baseline 与 candidate 使用同一面积口径。
- 汇总输出应适合机器读取，不只输出纯文本。

## 建议字段

- design_name
- design_type
- correctness
- timing_status
- wns
- tns
- critical_delay
- area
- cell_count
- sim_runtime_sec
- eval_runtime_sec
- total_runtime_sec

## 独立性设计

- 脚本应只依赖标准输入文件和路径，不依赖具体实现过程。
- 即使未来更换仿真器或更换 STA 工具，只要报告格式兼容，汇总脚本仍可复用。

## 风险

- timing 报告格式在工具版本间可能有差异。
- candidate 网表中的黑盒或非法单元会影响面积统计。

## 验收标准

- 能对 baseline 产生统一 summary 输出。
- 能对任意一个合法 candidate 产生统一 summary 输出。
- baseline 与 candidate 汇总结果字段完全一致。
- 汇总脚本能检测并标记缺失报告，而不是静默失败。
