# Task 05: Eval STA Flow

## 目标

在 `eval/` 下建立独立的 STA 评估流程，对 baseline mapped netlist 和 candidate 直接网表统一做 OpenTimer / OpenROAD 分析。

## 范围

本任务只负责时序分析流程，不负责功能仿真，不负责面积统计汇总逻辑。

## 输入

- baseline 或 candidate 网表
- liberty 文件
- SDC 约束

## 输出

- `eval/run_timer.sh`
- timing summary 报告
- 关键路径摘要报告

## 设计要求

- 必须与 `sim/` 解耦。
- 脚本能通过命令行接受网表、liberty、SDC 路径。
- 结果输出路径要稳定，便于后续 `parse_reports.py` 汇总。

## 环境要求

- 使用 conda 环境安装 OpenROAD / OpenTimer 或兼容工具链。
- 所需环境变量和启动命令应在脚本注释或配套说明中写明。

## 独立性设计

- 本任务不依赖 DC，只要求输入是可分析网表。
- baseline 与 candidate 使用同一 STA 入口。

## 风险

- OpenTimer / OpenROAD 安装方式在不同机器上可能有差异。
- candidate 如果实例化了 liberty 中不存在的单元，会导致 STA 失败。

## 验收标准

- `eval/run_timer.sh` 能对一个给定网表跑出 timing summary。
- baseline mapped netlist 可以通过该脚本得到时序结果。
- candidate 网表只要符合单元约束，也能通过该脚本分析。
- 默认一次 STA 运行应控制在 90 秒量级以内。
