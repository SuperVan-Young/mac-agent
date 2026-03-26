# Task 03: Baseline DC Flow

## 目标

为 `rtl/baseline.v` 提供一个最小可复现的 DC 综合流程，仅用于 baseline 的参考网表和参考 PPA 生成。

## 范围

本任务只负责 baseline 的 DC 脚本和输出规范，不处理 candidate。

## 输入

- `task_01_interface_contract.md` 的顶层定义
- `task_02_baseline_rtl.md` 提供的 `rtl/baseline.v`
- 当前 PDK 的 liberty 路径与 DesignWare 配置

## 输出

- `syn/run.tcl`
- `syn/outputs/baseline_mapped.v`
- `syn/reports/baseline_timing.rpt`
- `syn/reports/baseline_area.rpt`

## 脚本职责

- 读入 baseline RTL
- 设定 target library / link library / synthetic library
- 设定顶层
- 设定最简单时序约束
- 执行综合
- 导出映射后网表与基础 report

## 独立性设计

- 不处理 OpenTimer。
- 不处理功能仿真。
- 不处理 candidate 网表检查。

## 风险

- 不同 PDK / DC 版本下库变量设置方式不同。
- 若 baseline 引用 DesignWare，但环境没有正确配置 `dw_foundation.sldb`，综合会失败。

## 验收标准

- `syn/run.tcl` 可以在目标 DC 环境下独立执行。
- 执行后能生成 mapped netlist 和 timing/area report。
- 结果文件路径和命名符合接口规范。
- 脚本中没有将 candidate 纳入综合流程。
