# Scheduler 合入与归档规则

本文只描述以下内容：

- 合入/准入规则
- 对 Worker 的任务风格分配规则
- 合法性审查方法
- 使用 sub-agent 时的模型分配要求
- 日志记录方法
- promote / reject 的日志更新方法
- 合入（promote）或拒绝（reject）后的工作区处理

本文不包含 Scheduler 如何自己产生优化思路。

## 0. 工作区约束

- Scheduler 与 Worker 必须始终在同一个仓库工作区内协作，不得为单轮任务切换到不同 worktree。
- Scheduler 审查的 `results/fixed/` 必须就是 Worker 本轮在同一工作区内刚生成的结果目录。
- Scheduler 不得假设其他 worktree 中存在“更完整”或“更新”的 `results/fixed/`，也不得跨 worktree 复制结果后再审查。
- 如需读取上一轮或当前主线的固定结果，必须直接在当前工作区内读取现成的 `results/fixed/` 与归档文件。

## 1. 合入与准入规则

1. Scheduler 不重新运行检查或评测流程。  
   Worker 已经在当前工作区执行过完整流程，Scheduler 仅审查当前工作区固定结果目录 `results/fixed/` 中的现成产物。
2. 只有当现成结果合法、完整，并满足合入条件时，才允许合入（promote）。
3. 合入比较必须与当前已生效 candidate 使用同一配置口径（工艺、约束、评测口径一致）。
4. 提升提交采用线性历史，不使用 merge commit。
5. 当前不默认分派 `Refactor Agent`；Scheduler 应默认把“做 general、可复用、可扩展机制”的任务直接交给 Worker。

## 2. 对 Worker 的任务风格分配

Scheduler 可以为 Worker 指定本轮任务风格：

- `conservative`
- `aggressive`

如果程序员没有明确指定，则 Scheduler 必须在两者之间随机选择一个。  
但当 Worker 已经提出明显更具泛化性、跨层次、跨模块或机制级的方案时，应优先允许其按 `aggressive` 风格执行，而不是强行压缩成局部修补。

Scheduler 在下发任务时，还应明确告诉 Worker：

- 本轮任务风格
- 如果是 `aggressive`，允许尝试的步数上限
- 本轮希望解决的瓶颈、缺口或机制方向

建议理解如下：

- `conservative`：优先选择一个瓶颈明确、收益路径清楚、改动局部的优化点，尽量一轮完成。
- `aggressive`：允许 Worker 推进更大幅度的新策略、新机制或跨层次协同设计；如果同时存在激进方案和保守方案，默认优先激进方案，但要求目标明确、功能定位明确、预期收益明确。

## 3. 合法性与完整性审查（只看现成结果）

Scheduler 必须在 `results/fixed/` 下确认以下文件存在且可读取：

- `logs/check.log`
- `logs/sim.log`
- `eval_sta/timing_summary.rpt`
- `eval_sta/critical_path.rpt`
- `eval_sta/design_area.rpt`
- `eval_sta/cell_usage.rpt`
- `area.json`
- `summary.json`

准入最小条件（均基于现成报告）：

- `check.log` 显示 candidate legality check 通过
- `summary.json` 中 `correctness == "pass"`
- `summary.json` 关键字段齐全，且与 timing/area 报告一致

在满足以上最小条件后，以下四类结果都允许进入合入判断：

1. 有明确性能收益的实现  
   例如改善 `wns`、`tns`、`critical_delay`、`area` 中至少一个核心指标，且没有不可接受退化。
2. 没有直接性能收益，但实现了新的分析功能  
   例如新增 profiling、瓶颈定位、IR 级 timing/area 分析、报告提取、候选结构观察器等。
3. 没有直接性能收益，但实现了未来可复用的 pass / pattern / helper  
   例如当前未在主 pipeline 启用，但其机制清晰、边界清楚、未来可用于优化或分析。
4. 提出了大胆的跨层次协同设计机制  
   即使 Worker 在本轮尚未想出足够好的策略去超过当前 SOTA，只要该机制在完备性上涵盖原有机制、实现质量过关、后续有继续叠代价值，Scheduler 也可以考虑先合入代码。

因此，Scheduler 不得把“本轮没拿到直接 QoR 改善”简单等同于“必须 reject”。  
若结果本质上属于分析能力建设、机制建设或可复用技术贮备，且质量合格、接口合理、对后续工作有明确帮助，可以 promote。

任一最小合法性条件不满足才应直接 reject。

Worker 在中间试错阶段可以只做部分评估，但 Scheduler 只认可最终验收阶段留下的完整结果。  
也就是说，只有当 `results/fixed/` 中已经具备完整验收产物时，Scheduler 才能进入审查与 promote / reject 判断。

## 4. 使用 Sub-Agent 时的模型要求

如果 Scheduler 需要启动 sub-agent 执行优化任务，必须满足以下要求：

- 优先分配当前可用的最新版本模型
- 思考强度必须设置为较高档位，不得使用低强度快速模式执行优化主任务
- 若存在多个可选模型，优先选择更新且更强的模型承担实际优化工作

Scheduler 不得为了节省资源而默认给优化任务分配明显过旧或低思考强度的模型。

## 5. 日志记录方法

`promote.json` 与 `reject.json` 都必须是合法 UTF-8 JSON 对象，且结构一致：

```json
{
  "history": [
    {
      "iteration": 0,
      "metadata": {
        "source": "baseline",
        "dut": "baseline.synth.v",
        "top_module": "mac16x16p32",
        "comment": "Baseline design synthesized with Cadence Genus."
      },
      "result_summary": {
        "correctness": "pass",
        "timing_status": "fail",
        "wns": -0.3817,
        "tns": -9.9825,
        "critical_delay": 0.3826,
        "area": 153.0,
        "cell_count": 1716
      }
    }
  ]
}
```

每条记录都必须包含：

- `iteration`：本次迭代的序号
- `metadata`: 包括 `source`, `dut`, `top_module`, `comment`
- `result_summary`：包括 `correctness`, `timing_status`, `wns`, `tns`, `critical_delay`, `area`, `cell_count`

- 顶层必须为对象，且包含 `history` 数组
- `history` 只能追加，不能覆盖旧记录
- 新记录的 `iteration` 必须不小于已有最大值

`metadata.comment` 必须只保留关键内容，但不能空泛。至少要写清三件事：

1. 本轮观察到的瓶颈、缺口或动机
2. 本轮改动了什么机制、分析能力或实现
3. 于是取得了什么优化效果，或留下了什么后续可复用价值

推荐写法：

- promote 示例：`Observed the D30 high-bit sum chain as the timing bottleneck; introduced a reusable high-bit carry-window optimization pass plus supporting analysis hooks; this improved critical_delay without area regression.`
- promote 示例：`Observed missing IR-level visibility into timing hot spots; added a reusable timing bottleneck profiler that is not yet enabled in the main pipeline; this round brought no immediate QoR gain but establishes a reusable analysis capability.`
- reject 示例：`Observed the D30 output tail as the bottleneck; expanded the high-bit fast window in the lowering flow; this caused no timing gain and increased area, so the round was rejected.`

缺失或格式不合法即拒绝（reject）。

## 6. promote / reject 的日志更新方法

1. promote 时：
   - 只更新 `promote.json`
   - 向 `history` 追加一条新记录
   - `comment` 写清瓶颈/动机、改动内容、优化效果或技术贮备价值
2. reject 时：
   - 只更新 `reject.json`
   - 向 `history` 追加一条新记录
   - `comment` 写清瓶颈/动机、改动内容、回退或 reject 原因
3. 两类更新都必须基于 worker 留下的现成结果
4. 只有日志写入成功后，才允许执行清理

缺失、格式不合法、或 reject 后未追加记录，均视为 Scheduler 流程不完整。

## 7. 合入/拒绝后的工作区处理

本仓库要求 Scheduler/Worker 共享同一工作区，因此默认不再执行“删除 worker worktree”这一类清理动作。归档写入成功后，只处理仓库内容本身：

1. 合入（promote）：
  - 完成提升提交，并 push 到远程仓库
  - 向 `promote.json` 追加本轮合入记录
2. 拒绝（reject）：
   - 向 `reject.json` 追加本次拒绝归档
