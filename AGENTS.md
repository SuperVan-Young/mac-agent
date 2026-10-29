# Agent Entry

项目目标是让 agent 开发直接生成 MAC 门级网表的 EDA 工具，并在相同工艺与约束下超越商用综合工具的时序、面积表现。`eval/` 提供统一评测 harness，baseline 提供商用工具的比较基准。

本仓库评估整数 MAC：`D = A * B + C`，默认 unsigned 16×16→32，顶层 `mac16x16p32`。

## 工作入口

运行或修改评估流程、综合设计、排查 timing/area 时，使用仓库技能 [.agents/skills/mac-eval/SKILL.md](.agents/skills/mac-eval/SKILL.md)。

## 目录约定

- `rtl/baseline/`：baseline 行为级源码与固定综合网表。
- `eval/`：评估 harness，包括执行、配置、单次报告解析。
- `results/`：不提交 Git 的运行产物；外部框架可通过 `RESULTS_DIR` 指定其他输出目录。
- `.agents/skills/`：随仓库维护的技能与参考资料。
- `env/`：工具环境安装；`tech/`：工艺库。

根 Makefile 是薄入口。`make all` 默认评估保存的 baseline 网表；`make syn` 显式重新综合。修改评估流程后运行受影响阶段，检查日志与报告的一致性。修改路径时同步更新脚本默认值及技能参考资料。
