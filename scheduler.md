# Scheduler 合入与归档规则

本文只描述以下内容：

- 合入/准入规则
- 合法性审查（基于 worker 现成结果）
- 使用 sub-agent 时的模型分配要求
- 日志记录方法
- promote / reject 的日志更新方法
- 合入（promote）或拒绝（reject）后的 worktree 清理

本文不包含 Scheduler 如何产生优化思路。

## 1. 合入与准入规则

1. Scheduler 不重新运行检查或评测流程。  
   Worker 已经执行过完整流程，Scheduler 仅审查 worker worktree 固定结果目录 `results/fixed/` 中的现成产物。
2. 只有当现成结果合法、完整，并满足合入条件时，才允许合入（promote）。
3. 合入比较必须与当前已生效 candidate 使用同一配置口径（工艺、约束、评测口径一致）。
4. 提升提交采用线性历史，不使用 merge commit。

## 2. 合法性与完整性审查（只看现成结果）

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
- 与当前已生效 candidate 对比后，满足预设合入条件（例如至少一个核心指标改善且无不可接受退化）

任一条件不满足即拒绝（reject）。

## 3. 使用 Sub-Agent 时的模型要求

如果 Scheduler 需要启动 sub-agent 执行优化任务，必须满足以下要求：

- 优先分配当前可用的最新版本模型
- 思考强度必须设置为较高档位，不得使用低强度快速模式执行优化主任务
- 若存在多个可选模型，优先选择更新且更强的模型承担实际优化工作

Scheduler 不得为了节省资源而默认给优化任务分配明显过旧或低思考强度的模型。

## 4. 日志记录方法

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

1. 本轮观察到的瓶颈
2. 本轮改动了什么
3. 于是取得了什么优化效果，或于是产生了什么回退

推荐写法：

- promote 示例：`Observed the D30 high-bit sum chain as the timing bottleneck; strengthened the final carry/output window in rtl/generate.py; this improved critical_delay without area regression.`
- reject 示例：`Observed the D30 output tail as the bottleneck; expanded the high-bit fast window in rtl/generate.py; this caused no timing gain and increased area, so the round was rejected.`

缺失或格式不合法即拒绝（reject）。

## 5. promote / reject 的日志更新方法

1. promote 时：
   - 只更新 `promote.json`
   - 向 `history` 追加一条新记录
   - `comment` 写清瓶颈、改动、优化效果
2. reject 时：
   - 只更新 `reject.json`
   - 向 `history` 追加一条新记录
   - `comment` 写清瓶颈、改动、回退或 reject 原因
3. 两类更新都必须基于 worker 留下的现成结果
4. 只有日志写入成功后，才允许执行清理

缺失、格式不合法、或 reject 后未追加记录，均视为 Scheduler 流程不完整。

## 6. 合入/拒绝后的 Worktree 清理

在归档写入成功后，必须执行 worker worktree 清理：

1. 合入（promote）：
  - 完成提升提交，并push到远程仓库
  - 向 `promote.json` 追加本轮合入记录
  - 删除对应 worker worktree
  - 按仓库策略删除 worker 分支（如允许）
2. 拒绝（reject）：
   - 向 `reject.json` 追加本次拒绝归档
   - 删除对应 worker worktree
   - 按仓库策略删除 worker 分支（如允许）
