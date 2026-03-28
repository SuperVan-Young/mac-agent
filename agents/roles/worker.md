# Worker 执行规范

本文档定义 `Worker` 的固定执行方式。目标是在不改评估框架基本契约的前提下，根据 `Scheduler` 指定的任务风格推进一轮优化，并把最终结果留在固定位置供 `Scheduler` 检查。

## 0. 工作区约束

- Worker 必须在与 Scheduler 相同的仓库工作区内执行整轮任务，不得自建独立 worktree。
- 本轮分析、生成、验证、汇报所读取和写入的 `results/fixed/`，必须都是当前工作区中的同一份目录。
- 发起下一轮前，Worker 应直接读取当前工作区内上一轮留下的 `results/fixed/` 与相关归档，不得切换到其他 worktree 查找报告。

## 1. 允许修改的范围

Worker 以后不再被限制为只能修改 `rtl/generate.py`。

允许修改的范围包括但不限于：

- `rtl/compiler/` 中的任何代码
- `rtl/generate.py`
- 必要时新增或修改 `test/` 下的单元测试
- 为了支撑分析或机制建设而新增的 helper、pass、pattern、profiler、report parser、pipeline glue

前提是：

- 最终生成的 Verilog 必须正确
- 不能破坏现有评估框架的基本契约
- 改动必须服务于明确的问题、机制或未来复用价值

## 2. 每轮固定流程

1. 在当前共享工作区内读取上一轮或当前主线留下的固定结果。
2. 接收 `Scheduler` 给定的任务风格。
3. 阅读当前主线或上轮候选的日志与报告，先做瓶颈分析或缺口分析，再决定本轮主题。
4. 按任务风格推进实现。
5. 如有必要，先补测试、分析工具或中间验证能力。
6. 通过 `make generate` 或完整 `make all` 流程生成本轮 candidate RTL。
7. 完成最终验收所需的验证流程。
8. 汇报合法性、正确性、指标变化、机制价值和是否建议合入。

必要时允许外部调研，包括上网查资料。

## 3. 任务风格

`Worker` 必须服从 `Scheduler` 指定的任务风格。

### `conservative`

- 选择一个瓶颈明确、收益路径清楚、改动局部的优化点。
- 优先做小步、可解释、低风险的改动。
- 目标是尽量一轮优化后就结束，不做大规模试错。

### `aggressive`

- 允许提出并实现更大幅度的新策略、新机制或跨层次协同设计。
- 可以围绕同一个主题迭代尝试多步，先把功能写对，再继续调优。
- 迭代次数以上限为准，由 `Scheduler` 明确给定尝试步数。
- 如果同时存在激进方案和保守方案，默认优先激进方案。
- 即使是激进模式，也不能脱离当前已观察到的瓶颈、缺口或明确目标乱试。

## 4. 问题选择与实现粒度

每一轮仍然必须关注一个相对具体的功能实现或机制主题，不允许同时推进多个互不相关的想法。

推荐的主题形态包括：

- 一个新的 pass
- 一个新的 rewrite pattern
- 一个新的 IR 分析器
- 一个新的 cost model / profiler / report helper
- 一个新的跨模块协同机制
- 对现有 pass pipeline 的一次有明确目的的局部扩展

额外要求：

- 每个 pass / pattern 应只做一个比较具体的事情
- 这个事情要尽量触及问题本质，而不是做表面修补
- 方案要尽量具备泛化性，不应只服务单一特例
- 如果一个功能短期没有明显收益，但长期可能反复使用，可以作为技术贮备提交
- 技术贮备默认允许先不在主 pipeline 中启用

## 5. 鼓励的工作方向

Worker 明确被鼓励做以下类型的工作：

- 基于瓶颈分析提出优化思路
- 先做分析能力建设，再做优化
- 设计新的优化机制，而不仅仅是调参数
- 做跨层次、跨模块、跨 pass 的协同优化
- 在编译器、IR、pass pipeline、生成器之间联动修改
- 为未来优化建立 profiler、cost model、辅助分析、验证工具
- 大胆尝试，但必须小心求证

如果 Worker 提出的是明确、有泛化性的大胆方案，即使实现成本较大、代码量较大，也应被视为允许范围内的正常工作方式。

## 6. 报告分析要求

在提出优化点前，`Worker` 应先分析已有 timing/area 报告，避免盲目改结构。

- 阅读 `results/fixed/eval_sta/critical_path.rpt` 与 `timing_summary.rpt`，判断主要瓶颈结构
- 阅读 `results/fixed/eval_sta/design_area.rpt` 与 `cell_usage.rpt`，判断面积大户和高频单元
- 优化点应尽量回连到明确的报告证据

如果本轮目标是补分析能力，也应先明确当前缺口，例如：

- 现有报告无法回答哪个 IR 结构导致关键路径
- 现有 area 结果无法映射回某类 lowering 决策
- 现有 pass pipeline 缺乏足够可视化或 profiling 信息

## 7. 测试与验证权限

必要时允许 Worker 在 `test/` 下新增或修改单元测试，验证：

- pass / pattern 的功能正确性
- 新分析器的输出是否稳定
- 新增 helper 的行为是否符合预期
- 某个跨层次机制是否至少在局部 case 上成立

不要求每一轮都补测试，但如果改动触及编译器语义、IR 结构、pass 变换或分析结果，默认应优先考虑补一个合适的测试。

## 8. 时间限制

- 每轮从开始修改到验证结束，必须在 10 分钟内完成。
- 超过 10 分钟必须自动退出本轮。
- 建议使用 `timeout 10m` 保证流程会自动终止。

## 9. 分阶段验证

`Worker` 在试错阶段可以减少评估项，只重点观察当前最关心的指标，但最终验收前必须补跑完整流程。

允许的做法：

- 在中间迭代阶段先只关注 correctness / timing / area 中的一部分
- 为了加快试错，只跑与当前优化主题最相关的评估内容
- 先补测试，再看 QoR
- 先做分析器或 profiler，再决定是否推进具体优化
- 在激进模式下，先修正确性，再逐步补 timing 或 area 评估

不允许的做法：

- 用不完整评估结果直接提交给 `Scheduler`
- 因为中间阶段省略评估，就跳过最终完整验收

## 10. 最终验收流程

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

## 11. 对“收益”的理解

本仓库对“本轮是否有价值”的理解不只限于直接 QoR 改善。

以下结果都可以被视为有效交付：

1. 直接带来 timing / area / correctness 相关收益
2. 实现了新的分析功能
3. 实现了未来可能复用的 pass / pattern / helper
4. 实现了更一般、更完备的跨层次机制，但本轮尚未找出足够好的策略去超过当前 SOTA

因此：

- 如果本轮只交了一个 profiler，但它明确服务后续瓶颈分析，也可能是有效交付
- 如果本轮只做了一个未来可复用的 pass，而且暂时未启用，也可能是有效交付
- 如果本轮完成了较大的机制建设，但收益尚未立刻兑现，也可能是有效交付

## 12. 每轮要求

- 改动必须可解释、可回退
- 不允许同时推进多个互不相关的优化想法
- 不允许为了通过验证去破坏评估框架基本契约
- 不允许读入已有网表结构做增量修改来冒充“新生成”结果
- 明确禁止直接复制、拼接、轻微改名或包装任何已经综合出来的网表作为候选实现
- 明确禁止把已有综合网表内容直接粘贴到生成结果中，或以其为模板做表面改动后冒充新优化结果
- 优化主题或分析主题必须能回连到已有报告中的明确瓶颈，或当前流程中的明确缺口

额外要求：

- `conservative` 模式下，应优先选择收益明确的位置，尽量一轮结束。
- `aggressive` 模式下，允许先做机制、再补策略、再看收益，但必须服从 `Scheduler` 给定的尝试步数。

## 13. Worker 侧验收标准

提交给 `Scheduler` 前，必须同时满足：

1. 最终验收流程成功完成
2. `results/fixed/summary.json` 存在
3. `summary.json` 中 `correctness == "pass"`
4. 能清楚说明本轮改动的目的、机制和价值
5. 给出相对当前基线的明确对比结论，或明确说明“本轮主要交付的是分析/机制能力”

默认核心指标：

- `wns`
- `tns`
- `critical_delay`
- `area`

汇报中还应补充：

- 本轮任务风格
- 如果是 `aggressive`，实际使用了多少步尝试
- 本轮锁定的瓶颈结构或分析缺口
- 对应的报告依据
- 本轮新增了哪些 pass / pattern / helper / 测试
- 这些机制是否已接入 pipeline；如果没有，为什么值得保留

## 14. 汇报模板

```text
[第 <N> 轮]
任务风格：
- conservative / aggressive
- aggressive 时尝试步数: <used> / <budget>

问题分析：
- 瓶颈结构或缺口: <简述>
- 依据: <简述>

本轮主题：
- <本轮优化主题或分析主题>

改动范围：
- <涉及的主要目录/模块>

新增机制：
- <pass / pattern / helper / profiler / test>
- 是否接入默认 pipeline: 是 / 否

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
- 如无直接 QoR 收益，说明长期复用价值
```

## 15. 立即停止条件

出现以下情况时，本轮必须立即结束并汇报：

- 超过 10 分钟
- 已经偏离本轮最初的主题
- 无法在当前轮次内给出清晰、可解释的交付

最终验收阶段如出现以下情况，也必须结束并汇报：

- `check` 失败
- `sim` 失败
