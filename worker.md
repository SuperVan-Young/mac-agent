# Worker 执行规范

本文档定义 `Worker` 的固定执行方式。目标是在不改评估框架的前提下，通过修改单一生成脚本做一轮小优化，并把结果留在固定位置供 `Scheduler` 检查。

## 1. 严格角色边界

`Worker` 只允许修改一个文件：

- `rtl/generate.py`

除 `rtl/generate.py` 外，仓库内任何其他路径都禁止修改。

## 2. 每轮固定流程

1. 自己创建独立 worktree。
2. 阅读当前主线或上轮候选的日志与报告。
3. 自己提出一个小优化点。
4. 只修改 `rtl/generate.py`。
5. 生成本轮 `mac16x16p32.v`。
6. 完成验证流程。
7. 汇报合法性、正确性、指标变化和是否建议合入。

必要时允许外部调研，包括上网查资料，但不得改评估框架或扩大改动边界。

## 3. 时间限制

- 每轮从开始修改到验证结束，必须在 10 分钟内完成。
- 超过 10 分钟必须自动退出本轮。
- 建议使用 `timeout 10m` 保证流程会自动终止。

## 4. 验证流程

在独立 worktree 内按以下顺序执行：

1. 运行 `rtl/generate.py`，生成 `mac16x16p32.v`
2. 运行完整评估：

```bash
timeout 10m make clean && timeout 10m make all DESIGN_TYPE=candidate DUT=$(pwd)/mac16x16p32.v
```

验证完成后，结果必须出现在固定位置：

- `results/fixed/summary.json`
- `results/fixed/logs/check.log`
- `results/fixed/logs/sim.log`
- `results/fixed/eval_sta/timing_summary.rpt`
- `results/fixed/eval_sta/critical_path.rpt`
- `results/fixed/eval_sta/design_area.rpt`
- `results/fixed/area.json`

## 5. 每轮要求

- 一轮只做一个小优化点
- 改动必须局部、可解释、可回退
- 不允许同时引入多个优化想法
- 不允许为了通过验证去改框架
- 不允许读入已有网表结构做增量修改，必须从零开始构建网表

## 6. Worker 侧验收标准

提交给 `Scheduler` 前，必须同时满足：

1. 只修改了 `rtl/generate.py`
2. 验证流程成功完成
3. `results/fixed/summary.json` 存在
4. `summary.json` 中 `correctness == "pass"`
5. 给出相对当前基线的明确对比结论

默认核心指标：

- `wns`
- `tns`
- `critical_delay`
- `area`

## 7. 汇报模板

```text
[第 <N> 轮]
优化点：
- <本轮唯一小优化点>

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

## 8. 立即停止条件

出现以下情况时，本轮必须立即结束并汇报：

- 超过 10 分钟
- `check` 失败
- `sim` 失败
- 需要修改 `rtl/generate.py` 之外的文件
- 已经偏离本轮最初的小优化点
