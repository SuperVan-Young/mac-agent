# Agent Entry

项目目标是让 agent 产生直接映射到特定 PDK 的 MAC Verilog 网表，在相同工艺与约束下探索超越商用综合结果的实现。可以直接编写网表，也可以开发生成器；验收对象是单个 Verilog 文件。

当前任务：`D = (A * B + C) mod 2^32`，unsigned 16×16+32→32，纯组合逻辑，顶层 `mac16x16p32`。

## 工作入口

运行或修改评估流程、综合设计、排查 timing/area 时，使用 [.agents/skills/mac-eval/SKILL.md](.agents/skills/mac-eval/SKILL.md)。

## 目录约定

- `rtl/baseline/`：baseline 行为级源码与固定综合网表。
- `eval/`：Python 评测 harness、任务配置、工具 Tcl。
- `tests/`：统一存放 harness 与仿真回归测试。
- `results/`：不提交 Git 的单次运行产物；外部框架负责迭代与排名。
- `.agents/skills/`：随仓库维护的技能与参考资料。
- `env/`：工具环境安装；`tech/`：工艺库。

正式入口是 `python eval/run.py candidate.v --harness-ref <commit>`；`--dev` 使用工作区 evaluator，结果不作为正式验收。单独综合使用 `python eval/syn/run.py`。baseline 与 candidate 走相同检查，正式配置来自所选提交。

修改 harness 或仿真后运行 `python -m unittest discover -s tests -v`。更新接口时同步维护技能参考资料。
