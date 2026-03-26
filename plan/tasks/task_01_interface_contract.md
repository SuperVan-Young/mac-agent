# Task 01: Interface Contract

## 目标

固定整个项目的公共接口和约束，避免 baseline、仿真、PPA、candidate 检查各自做出不兼容假设。

## 范围

本任务只定义规范，不实现具体功能脚本。

需要明确的内容：

- 顶层模块名
- 端口名与位宽
- `signed` / `unsigned` 语义
- 时钟/复位是否存在
- candidate 文件命名规范
- baseline 输出文件命名规范
- `results/` 结果目录命名规范
- 仿真通过/失败的统一返回格式
- PPA 汇总表字段定义

## 建议默认值

- 顶层模块名：`mac16x16p32`
- 语义：`unsigned`
- 输入输出：
  - `input  [15:0] A`
  - `input  [15:0] B`
  - `input  [31:0] C`
  - `output [31:0] D`
- 第一版默认组合逻辑 MAC，不引入时钟和复位

## 交付物

- 一份接口规范文档
- 一份结果字段规范文档或在同一文档中给出表格定义

建议落盘位置：

- `plan/tasks/task_01_interface_contract.md` 作为计划
- 后续实现时可补充到 `docs/contract.md`

## 独立性设计

- 本任务不依赖任何工具安装。
- 本任务完成后，其余任务只依赖该规范，不依赖彼此内部实现。

## 风险

- 若 `signed/unsigned` 未明确，后续 baseline 与仿真结果会不一致。
- 若 candidate 输出接口不统一，自动化评估脚本会频繁分支处理。

## 验收标准

- 文档中明确给出模块名、端口定义、数据语义。
- 文档中明确给出 baseline/candidate/results 的命名规范。
- 文档中明确给出汇总报告至少包含：
  - design name
  - correctness
  - delay 或 WNS
  - area
  - cell count
  - runtime
- 其余任务无需再自行猜测接口细节。
