# Integer MAC 评估框架

项目目标是让 agent 开发直接生成 MAC 门级网表的 EDA 工具，并在相同工艺与约束下超越商用综合工具的时序、面积表现。`eval/` 提供统一评测 harness，baseline 提供商用工具的比较基准。

评估 `D = A * B + C` 的正确性、时序和面积。默认设计为 unsigned 16×16→32，顶层 `mac16x16p32`。

```bash
bash env/setup_conda.sh
make all
```

`make all` 直接评估 `rtl/baseline/baseline.synth.v`，结果位于 `results/baseline/`。`make syn` 使用 Genus 重新综合 baseline 源码；运行其他网表可指定 `DUT=/absolute/path/to/netlist.v`。

- `rtl/baseline/`：baseline 源码与综合网表
- `eval/`：仿真、综合、合法性检查、timing、area、汇总及配置
- `.agents/skills/mac-eval/`：评估技能与操作参考
- `env/`：环境安装；`tech/`：工艺资源

详细用法见[评估流程](.agents/skills/mac-eval/references/baseline_flow_zh.md)，Agent 入口见 [AGENTS.md](AGENTS.md)。
