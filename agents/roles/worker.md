# Worker 执行规范

本文档定义 `Worker` 的固定执行方式。目标是在不改评估框架的前提下，根据 `Scheduler` 指定的优化策略推进一轮优化，并把最终结果留在固定位置供 `Scheduler` 检查。

## 0. 工作区约束

- Worker 必须在与 Scheduler 相同的仓库工作区内执行整轮任务，不得自建独立 worktree。
- 本轮分析、生成、验证、汇报所读取和写入的 `results/fixed/`，必须都是当前工作区中的同一份目录。
- 发起下一轮前，Worker 应直接读取当前工作区内上一轮留下的 `results/fixed/` 与相关归档，不得切换到其他 worktree 查找报告。

## 1. 严格角色边界

`Worker` 只允许修改一个文件：

- `rtl/generate.py`

除 `rtl/generate.py` 外，仓库内任何其他路径都禁止修改。

## 2. 每轮固定流程

1. 在当前共享工作区内读取上一轮或当前主线留下的固定结果。
2. 接收 `Scheduler` 给定的优化策略模式。
3. 阅读当前主线或上轮候选的日志与报告，先做瓶颈分析再决定优化点。
4. 按策略模式推进优化。
5. 只修改 `rtl/generate.py`。
6. 通过 `make generate` 或完整 `make all` 流程生成本轮 candidate RTL。
7. 完成最终验收所需的验证流程。
8. 汇报合法性、正确性、指标变化和是否建议合入。

必要时允许外部调研，包括上网查资料，但不得改评估框架或扩大改动边界。

## 3. 优化策略模式

`Worker` 必须服从 `Scheduler` 指定的策略模式。

### `conservative`

- 选择一个瓶颈明确、收益路径清楚、改动局部的优化点。
- 优先做小步、可解释、低风险的改动。
- 目标是尽量一轮优化后就结束，不做大规模试错。

### `aggressive`

- 允许提出更大幅度的新策略或新机制。
- 可以围绕同一个主题迭代尝试多步，先把功能写对，再继续调优。
- 迭代次数以上限为准，由 `Scheduler` 明确给定尝试步数。
- 即使是激进模式，也不能脱离当前已观察到的瓶颈和结构问题乱试。

## 4. 报告分析要求

在提出优化点前，`Worker` 应先分析已有 timing/area 报告，避免盲目改结构。

- 阅读 `results/fixed/eval_sta/critical_path.rpt` 与 `timing_summary.rpt`，判断主要瓶颈结构
- 阅读 `results/fixed/eval_sta/design_area.rpt` 与 `cell_usage.rpt`，判断面积大户和高频单元
- 优化点应尽量回连到明确的报告证据

## 5. 库感知要求

`Worker` 可以结合 ASAP7 standard cell library 做结构感知优化，但应优先服务关键路径或高频结构。

- 可以分析特殊结构在 ASAP7 中有哪些更合适的 cell，可替代当前生成策略
- 可以做小范围的 cell 选型、gate sizing 或 buffer insertion
- 不建议优先优化非关键路径、低频结构或 corner case

## 6. 时间限制

- 每轮从开始修改到验证结束，必须在 10 分钟内完成。
- 超过 10 分钟必须自动退出本轮。
- 建议使用 `timeout 10m` 保证流程会自动终止。

## 7. 分阶段验证

`Worker` 在试错阶段可以减少评估项，只重点观察当前最关心的指标，但最终验收前必须补跑完整流程。

允许的做法：

- 在中间迭代阶段先只关注 correctness / timing / area 中的一部分
- 为了加快试错，只跑与当前优化主题最相关的评估内容
- 在激进模式下，先修正确性，再逐步补 timing 或 area 评估

不允许的做法：

- 用不完整评估结果直接提交给 `Scheduler`
- 因为中间阶段省略评估，就跳过最终完整验收

## 8. 最终验收流程

在当前共享工作区内按以下顺序执行：

1. 运行 `make generate`，生成 candidate RTL
2. 运行完整评估：

```bash
timeout 10m make clean && timeout 10m make all DESIGN_TYPE=candidate
```

验证完成后，结果必须出现在固定位置：

- `results/fixed/generated/mac16x16p32.v`
- `results/fixed/summary.json`
- `results/fixed/logs/check.log`
- `results/fixed/logs/sim.log`
- `results/fixed/eval_sta/timing_summary.rpt`
- `results/fixed/eval_sta/critical_path.rpt`
- `results/fixed/eval_sta/design_area.rpt`
- `results/fixed/area.json`

## 9. 优化方向建议

`Worker` 可以从以下方向中选择本轮主题：

1. 调整部分积生成、压缩树结构或前缀和加法树结构
2. 针对关键结构调整 cell 选型，必要时做小范围 gate sizing 或 buffer insertion
3. 在设计阶段使用较准确的 timing/area 建模方法，先分析再决定结构

`conservative` 模式下，应尽量只推进一个小优化点。  
`aggressive` 模式下，可以围绕一个更大的主题连续试几步，但仍应保持主题一致。

## 10. 每轮要求

- 改动必须可解释、可回退
- 不允许同时推进多个互不相关的优化想法
- 不允许为了通过验证去改框架
- 不允许读入已有网表结构做增量修改，必须从零开始构建网表
- 明确禁止直接复制、拼接、轻微改名或包装任何已经综合出来的网表作为候选实现
- 明确禁止把已有综合网表内容直接粘贴到生成结果中，或以其为模板做表面改动后冒充新优化结果
- 优化主题必须能回连到已有报告中的明确瓶颈或结构问题

额外要求：

- `conservative` 模式下，应优先选择收益明确的位置，尽量一轮结束。
- `aggressive` 模式下，允许先试结构、再修功能、再调指标，但必须服从 `Scheduler` 给定的尝试步数。

## 11. Worker 侧验收标准

提交给 `Scheduler` 前，必须同时满足：

1. 只修改了 `rtl/generate.py`
2. 最终验收流程成功完成
3. `results/fixed/summary.json` 存在
4. `summary.json` 中 `correctness == "pass"`
5. 给出相对当前基线的明确对比结论

默认核心指标：

- `wns`
- `tns`
- `critical_delay`
- `area`

汇报中还应补充：

- 本轮策略模式
- 如果是 `aggressive`，实际使用了多少步尝试
- 本轮锁定的瓶颈结构
- 对应的报告依据

## 12. 汇报模板

```text
[第 <N> 轮]
策略模式：
- conservative / aggressive
- aggressive 时尝试步数: <used> / <budget>

报告分析：
- 瓶颈结构: <简述>
- 依据: <简述>

优化点：
- <本轮优化主题>

改动文件：
- rtl/generate.py

合法性：
- check: pass/fail

正确性：
- sim: pass/fail

指标对比：
- wns: <new> vs <base>
- tns: <new> vs <base>
- critical_delay: <new> vs <base>
- area: <new> vs <base>

结论：
- 建议合入 / 不建议合入 / 超时退出
```

## 13. 立即停止条件

出现以下情况时，本轮必须立即结束并汇报：

- 超过 10 分钟
- 需要修改 `rtl/generate.py` 之外的文件
- 已经偏离本轮最初的优化主题

最终验收阶段如出现以下情况，也必须结束并汇报：

- `check` 失败
- `sim` 失败
