# Task 02: Baseline RTL

## 目标

在 `rtl/baseline.v` 中提供一个基于 Synopsys DesignWare 的 baseline MAC 设计，作为后续功能和 PPA 对比基准。

## 范围

本任务只负责 baseline RTL 本身，不负责 DC 脚本、仿真脚本或 PPA 汇总。

## 输入

- `task_01_interface_contract.md` 定义的顶层接口和语义

## 输出

- `rtl/baseline.v`

## 设计要求

- 必须符合公共接口规范。
- 必须明确使用 Synopsys DesignWare 风格实现。
- 若存在库依赖或宏定义要求，应在文件头部或配套说明中写清楚。
- 代码应保持最小化，避免加入和 baseline 无关的包装逻辑。

## 独立性设计

- 该任务只产生 baseline RTL 文件。
- 不负责 candidate 生成规范。
- 不负责任何仿真器或综合器环境搭建。

## 风险

- baseline 若依赖特定 DesignWare 组件，DC 读入可能需要额外 `link_library` 或 `synthetic_library` 配置。
- 行为级写法与 DesignWare 推断风格不匹配时，可能得不到预期 baseline。

## 验收标准

- 存在文件 `rtl/baseline.v`。
- 顶层模块名与端口和公共接口规范完全一致。
- 文件能被 DC `analyze/elaborate` 或 `read_verilog` 正常读入。
- 文件可被 RTL 仿真器正常编译。
