# Task Breakdown

本目录将整体框架拆解为若干可独立推进的子任务。拆分原则如下：

- 每个子任务只关注一个明确职责边界。
- 尽量通过“接口规范”解耦，减少文件和脚本之间的相互依赖。
- 每个子任务都定义明确的输入、输出和验收标准。
- 除前置规范任务外，其余任务尽量可并行推进。

## 任务列表

1. `task_01_interface_contract.md`
   - 固定顶层接口、语义、命名、目录与结果格式。
   - 这是其余任务的最小前置项。

2. `task_02_baseline_rtl.md`
   - 准备 `rtl/baseline.v` 的 DesignWare baseline。

3. `task_03_baseline_dc_flow.md`
   - 为 baseline 建立最简 DC 综合脚本和输出约定。

4. `task_04_simulation_harness.md`
   - 建立功能仿真 testbench、向量和运行脚本。

5. `task_05_eval_sta_flow.md`
   - 建立 `eval/` 下的 OpenTimer / OpenROAD 时序评估流程。

6. `task_06_area_and_reporting.md`
   - 建立面积统计和统一结果汇总脚本。

7. `task_07_candidate_contract_and_checks.md`
   - 定义 agent candidate 网表提交格式、合法性检查和准入规则。

## 推荐执行顺序

推荐先完成：

1. `task_01_interface_contract.md`

然后并行推进：

2. `task_02_baseline_rtl.md`
3. `task_03_baseline_dc_flow.md`
4. `task_04_simulation_harness.md`
5. `task_05_eval_sta_flow.md`
6. `task_06_area_and_reporting.md`
7. `task_07_candidate_contract_and_checks.md`

## 依赖关系

- `task_01_interface_contract.md` 是公共前置任务。
- `task_03_baseline_dc_flow.md` 依赖 `task_02_baseline_rtl.md` 至少提供可读入的 baseline 顶层。
- `task_06_area_and_reporting.md` 依赖 `task_03_baseline_dc_flow.md` 与 `task_05_eval_sta_flow.md` 的输出格式，但实现时可先并行开发再联调。
- `task_07_candidate_contract_and_checks.md` 仅依赖 `task_01_interface_contract.md`，应尽量不依赖 baseline 具体实现。

## 完成定义

当以下条件同时满足时，可认为框架的计划拆解完成并具备进入实现阶段的条件：

- 每个子任务文件都有明确范围、交付物、风险和验收标准。
- 任一开发者仅阅读对应子任务文件，就能开始实现该部分。
- 任务之间的接口和输出路径没有明显冲突。
