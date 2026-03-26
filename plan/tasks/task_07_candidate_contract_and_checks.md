# Task 07: Candidate Contract And Checks

## 目标

定义 agent 提交 candidate 的网表格式、合法性约束和准入检查，确保 candidate 能直接进入仿真和 PPA 评估，而不经过 DC 再综合。

## 范围

本任务只关注 candidate 提交流程和静态检查，不负责生成 candidate 的搜索算法。

## 输入

- `task_01_interface_contract.md` 定义的公共接口
- 当前 PDK 的 liberty 或单元白名单

## 输出

- candidate 提交规范文档
- 候选检查脚本计划
- 后续实现时对应的合法性检查脚本

建议落盘位置：

- 计划阶段：`plan/tasks/task_07_candidate_contract_and_checks.md`
- 实现阶段：可在 `eval/` 或 `tools/` 下增加检查脚本

## 设计要求

- candidate 必须直接提供可评估 Verilog 网表或结构化门级描述。
- candidate 不得依赖 DC 重新综合。
- candidate 顶层接口必须与公共接口规范一致。
- candidate 只能实例化：
  - liberty 中存在的标准单元
  - 或项目显式允许的原语集合

## 建议检查项

- 模块名和端口名检查
- 非法单元名检查
- 黑盒检查
- 多驱动/悬空连接基础检查
- 是否包含行为级 `*` 运算或高层算术语句检查

## 独立性设计

- 本任务只定义 candidate 的准入门槛。
- 通过检查的 candidate 才交给 `sim/` 和 `eval/`。
- 该任务不依赖 baseline 具体写法。

## 风险

- 若约束过松，agent 可能输出不可制造或不可 STA 的结构。
- 若约束过严，会限制搜索空间，影响 agent 优化效果。

## 验收标准

- 文档明确说明什么样的 candidate 可以被接受。
- 至少列出一组可自动执行的检查项。
- 检查项覆盖接口一致性、单元合法性和“不可再走 DC”这三个核心目标。
- 通过检查的 candidate 可以直接进入 `sim/` 和 `eval/` 流程。

## 本任务实现落地（Task07 Worktree）

- 提交规范文档：`docs/candidate_submission.md`
- 检查脚本：`tools/check_candidate_netlist.py`
- 默认白名单：`tools/allowed_cells.txt`
- 本地样例：`tools/samples/`

当前脚本覆盖检查项：

- 顶层模块与接口一致性（`mac16x16p32`, `A/B/C/D`, 位宽/方向）
- 禁止行为级算术构造（`*`, `+`, `always*`）
- 实例化单元白名单检查（允许外部传入 allowlist）
- 基础 top 模块合法性检查（唯一 top、禁止 `inout`、黑盒标记检测）

运行方式：

```bash
python3 tools/check_candidate_netlist.py tools/samples/candidate_ok.v
python3 tools/check_candidate_netlist.py tools/samples/candidate_bad_arith.v
```
