# Agent Working Agreement

本文档定义本仓库中用于优化 `candidate design` 的两类 agent 角色行为规范。

目标对象固定为：

- `rtl/candidate_*.v`
- 功能：`D = A * B + C`
- 顶层：`mac16x16p32`

## Roles

本流程只允许两类角色：

1. `Scheduler`
2. `Worker`

除非明确说明，`Scheduler` 为主 agent，`Worker` 为子 agent。

## Scheduler

`Scheduler` 是主调度 agent，负责统筹多个 `Worker` 的候选方案，并决定是否自动合入。

### Scheduler Responsibilities

- 生成和分配任务，明确每个 `Worker` 的优化方向。
- 检查 `Worker` 的提交内容是否满足权限边界。
- 检查 `Worker` 的评估结果是否完整、可复现、可比较。
- 以当前已合入的 candidate 结果作为基线，比较新方案是否带来提升。
- 当新方案满足自动合入条件时，负责以线性历史方式合入。
- 每次合入后，必须在 `archive/` 下保留本次提交的 RTL 和评估结果。
- 维护“当前生效 candidate”与“已归档候选”的对应关系。

### Scheduler Allowed Changes

`Scheduler` 可以修改：

- `rtl/candidate_*.v`
- `archive/`
- 与归档、记录、调度直接相关的说明性文件

`Scheduler` 不应随意修改评估框架本身，除非用户单独提出新的框架维护任务。

### Scheduler Merge Policy

`Scheduler` 只可合入满足以下全部条件的 `Worker` 结果：

1. 功能正确：
   `correctness == pass`
2. 流程完整：
   必须提供仿真、STA、面积、summary
3. 结果可比：
   与当前基线使用同一套评估脚本和同一工艺库
4. 指标提升：
   至少一个核心 eval 指标优于当前基线，且不存在不可接受退化

默认核心 eval 指标为：

- `wns` 更大
- `tns` 更大
- `critical_delay` 更小
- `area` 更小

### Scheduler Auto-merge Rule

若无用户额外指定权重，`Scheduler` 默认按以下原则自动合入：

- 必须先保证 `correctness == pass`
- 若时序改善且面积不变差太多，可合入
- 若面积改善且时序不变差太多，可合入
- 若时序与面积都改善，优先合入
- 若只是噪声级变化，不应合入

“不变差太多” 由 `Scheduler` 结合当前比较对象判断，但必须在合入说明中写明比较依据。

### Scheduler Archive Rule

每一次被合入的结果，都必须在 `archive/` 下保存一个独立目录。

推荐目录格式：

```text
archive/<timestamp>_<tag>/
```

目录内至少包含：

- `candidate.v`
- `summary.json`
- `summary.csv`（若存在）
- `sim.log`
- `eval_sta/timing_summary.rpt`
- `eval_sta/critical_path.rpt`
- `area.json`
- `metadata.json`

其中 `metadata.json` 至少记录：

- source worker
- source commit
- promoted commit
- comparison baseline
- merge rationale

`Scheduler` 在自动合入后，应将被接受版本同步到当前工作 candidate 文件。

## Worker

`Worker` 是执行优化的子 agent，只负责在 candidate design 上做最小修改，并提交可验证的改进结果。

### Worker Responsibilities

- 在当前 candidate 基础上做最小改动。
- 只改 design 本体，必要时可写 Python 脚本自动生成 design。
- 运行完整评估流程，确认功能正确。
- 确认评估结果相对当前基线有提升。
- 将修改后的 RTL、生成方式、评估结果和对比结论汇报给 `Scheduler`。

### Worker Allowed Changes

`Worker` 只允许修改以下内容：

- `rtl/candidate_*.v`
- 为生成 candidate 而新增或修改的 Python 脚本

如果使用 Python 自动生成 candidate，则脚本必须只服务于 candidate design 生成，不得改变评估框架行为。

### Worker Forbidden Changes

`Worker` 不允许修改代码仓中的其他任何代码，包括但不限于：

- `sim/`
- `eval/`
- `syn/`
- `check/`
- `env/`
- `tech/`
- `README.md`
- `docs/`
- `plan/`
- `AGENTS.md`

`Worker` 也不允许通过修改评估脚本来“制造提升”。

### Worker Change Strategy

`Worker` 必须遵循“小步修改”原则：

- 每次尝试只引入一个明确设计意图
- 优先做局部、可解释、可回退的结构修改
- 不允许无边界大改

如果设计由脚本生成，也应保证生成规则的变化是最小且可解释的。

### Worker Validation Requirement

`Worker` 提交给 `Scheduler` 前，必须至少完成：

1. candidate 合法性检查
2. RTL/门级仿真
3. STA
4. 面积统计
5. summary 汇总

### Worker Success Condition

`Worker` 只有在以下条件同时满足时，才应报告“可合入候选”：

1. `correctness == pass`
2. 未修改 candidate design 之外的仓库代码
3. 与当前基线相比，eval 指标有明确提升

若功能正确但没有提升，`Worker` 也应汇报，但必须明确标记为“不建议合入”。

## Shared Rules

### Evaluation Consistency

所有比较必须基于同一套默认流程：

- candidate legality check
- `sim/run_rtl_sim.sh`
- `eval/run_timer.sh`
- `eval/area_report.py`
- `eval/parse_reports.py`

除非用户明确批准，否则不得切换工艺库、约束、top 接口、summary 字段。

### Commit Discipline

- `Worker` 产出应以独立提交或清晰 patch 的形式交给 `Scheduler`
- `Scheduler` 自动合入时保持线性历史
- 不使用 merge commit

### Result Integrity

任何声称“提升”的结果，都必须附带：

- 对比对象
- 对比指标
- 原始 summary
- 必要的仿真与 STA 关键报告

### Priority of Truth

若 `Worker` 的口头结论与实际报告不一致，以实际评估结果为准。

若评估结果不完整，`Scheduler` 不得自动合入。
