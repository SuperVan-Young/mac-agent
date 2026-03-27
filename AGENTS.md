# Agent Working Agreement

本仓库用于优化 `candidate design`。默认对象为 `rtl/candidate_mac16x16p32.v`，功能为 `D = A * B + C`，top 为 `mac16x16p32`。

角色固定为两类：

- `Scheduler`
- `Worker`

## 统一评估流程

所有比较都以 `Makefile` 为准，不允许手工拼接替代流程。

- 入口：`make all [CONFIG=...]`
- `candidate`：`check -> sim -> timing -> area -> summary`
- `baseline`：`synth(Genus) -> check -> sim -> timing -> area -> summary`

关键脚本与产物：

- `check`：`check/check_candidate_netlist.py`，输出 `results/<design>/check.log`
- `sim`：`sim/run_rtl_sim.sh`，输出 `results/<design>/sim.log`
- `timing`：`eval/run_timer.sh openroad`，输出 `results/<design>/eval_sta/timing_summary.rpt` 与 `critical_path.rpt`
- `area`：`eval/run_area.sh`，输出 `results/<design>/eval_sta/design_area.rpt`、`cell_usage.rpt`、`results/<design>/area.json`
- `summary`：`eval/parse_reports.py`，输出 `results/<design>/summary.json`，可选 `summary.csv`

配置统一来自 `env/config.mk`，可用 `CONFIG=<path>` 覆盖。未经批准，不得切换工艺库、约束口径或 summary 字段定义。

## Scheduler

职责：

- 分配任务并检查 `Worker` 是否遵守改动边界。
- 用同一配置口径比较当前已合入 candidate 与新候选。
- 只在结果完整、可复现、可比较时决定是否合入。
- 自动合入后维护 `archive/` 与当前生效 candidate 的对应关系。

可修改范围：

- `rtl/candidate*.v`
- `archive/`
- 调度与归档说明文件

除非用户单独下达框架维护任务，不修改评估框架代码。

合入条件：

1. `correctness == pass`
2. `make all` 跑通且产物完整
3. 与当前基线使用同一配置口径
4. 至少一个核心指标改善，且无不可接受退化

核心指标默认包括：`wns`、`tns`、`critical_delay`、`area`。

归档要求：

- 每次被合入版本保存在 `archive/<timestamp>_<tag>/`
- 至少保留 `candidate.v`、`summary.json`、`check.log`、`sim.log`、`eval_sta/timing_summary.rpt`、`eval_sta/critical_path.rpt`、`eval_sta/design_area.rpt`、`eval_sta/cell_usage.rpt`、`area.json`、`metadata.json`
- `metadata.json` 至少记录 `source_worker`、`source_commit`、`promoted_commit`、`comparison_baseline`、`merge_rationale`、`config_snapshot`

## Worker

职责：

- 在当前 candidate 上做最小、可解释、可回退的修改。
- 运行完整评估流程并提交可复现结果。
- 给出相对当前基线的明确结论：可合入或不建议合入。

允许修改：

- `rtl/candidate*.v`
- 仅用于生成 candidate 的 Python 脚本

禁止修改：

- `sim/`
- `eval/`
- `syn/`
- `check/`
- `env/`
- `tech/`
- `docs/`
- `plan/`
- `AGENTS.md`

不得通过修改评估脚本制造提升。

提交前最低验收：

1. `make all` 成功
2. `summary.json` 中 `correctness == pass`
3. 提供对比对象、关键指标变化和原始报告路径

若功能正确但无提升，必须标记为“不建议合入”。

## 共同规则

- 历史保持线性：不使用 merge commit
- `Worker` 以独立 commit 或清晰 patch 交付，`Scheduler` 决定是否提升
- 口头结论与报告冲突时，以报告为准
- 结果不完整不得自动合入
