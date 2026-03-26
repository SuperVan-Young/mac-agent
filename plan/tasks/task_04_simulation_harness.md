# Task 04: Simulation Harness

## 目标

建立独立的功能仿真框架，对 baseline 和 candidate 使用统一 testbench 和统一向量验证 MAC 正确性。

## 范围

本任务只负责 `sim/` 下的功能仿真，不包含 PPA 评估。

## 输入

- `task_01_interface_contract.md` 定义的接口和语义
- `rtl/baseline.v` 或任意 `rtl/candidate_*.v`

## 输出

- `sim/tb_mac.sv`
- `sim/vectors.py`
- `sim/run_rtl_sim.sh`
- 可选：`sim/run_gate_sim.sh`

## 设计要求

- baseline 与 candidate 使用同一 testbench。
- 向量必须包含：
  - 边界定向样例
  - 小规模随机样例
- 失败时输出最小必要上下文：
  - 当前输入值
  - 期望值
  - 实际值

## 时间约束

- 默认配置下单次仿真应控制在 1 分钟以内。

## 独立性设计

- 只依赖公共接口，不依赖 DC 或 OpenTimer。
- 能对任意符合接口规范的 DUT 独立运行。

## 风险

- 若 candidate 是纯门级网表，仿真编译选项可能与 RTL 略有差异。
- 若 signed/unsigned 语义和参考模型不一致，会出现伪失败。

## 验收标准

- `sim/run_rtl_sim.sh` 能对 `rtl/baseline.v` 跑通。
- 仿真输出明确给出 pass/fail。
- 至少包含一组边界测试和一组随机测试。
- baseline 通过后，更换为符合接口的 candidate 文件也能复用同一脚本。
