# Integer MAC 评估框架

评估 `D = A * B + C` 的正确性、时序和面积。默认设计为 unsigned 16×16→32，顶层 `mac16x16p32`。

```bash
bash env/setup_conda.sh
make all
```

`make all` 直接评估 `rtl/baseline/baseline.synth.v`，结果位于 `eval/results/baseline/`。`make syn` 使用 Genus 重新综合 baseline 源码；运行其他网表可指定 `DUT=/absolute/path/to/netlist.v`。

- `rtl/baseline/`：baseline 源码与综合网表
- `eval/`：仿真、综合、合法性检查、timing、area、汇总及配置
- `.agents/skills/mac-eval/`：评估技能与操作参考
- `env/`：环境安装；`tech/`：工艺资源

详细用法见[评估流程](.agents/skills/mac-eval/references/baseline_flow_zh.md)，Agent 入口见 [AGENTS.md](AGENTS.md)。
