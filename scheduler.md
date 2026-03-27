# Scheduler 合入与归档规则

本文只描述以下内容：

- 合入/准入规则
- 合法性审查（基于 worker 现成结果）
- 归档保留文件范围
- `optimization_log.json` 要求
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

## 3. 归档保留文件（严格限制）

每次决策都写入 `archive/<timestamp>_<tag>/`。  
归档中只允许保留以下两种组合之一：

1. `mac16x16p32.v` + `optimization_log.json`
2. `rtl/generate.py` + `optimization_log.json`

除上述组合外，不保留其他源码或附加文件。

## 4. optimization_log.json 要求

`optimization_log.json` 为必需文件，必须是合法 UTF-8 JSON 对象。  
至少包含以下字段：

- `iteration`
- `metadata`
- `result_summary`

约束：

- `result_summary` 中的指标字段值必须为数值或 `null`
- 必填字段不得缺失
- 不允许使用 `"TBD"` 等占位值

缺失或格式不合法即拒绝（reject）。

## 5. 合入/拒绝后的 Worktree 清理

在归档写入成功后，必须执行 worker worktree 清理：

1. 合入（promote）：
   - 完成提升提交
   - 删除对应 worker worktree
   - 按仓库策略删除 worker 分支（如允许）
2. 拒绝（reject）：
   - 保留本次拒绝归档
   - 删除对应 worker worktree
   - 按仓库策略删除 worker 分支（如允许）
