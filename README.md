# Integer MAC 网表评测

Agent 的提交物是自包含的 MAC Verilog 门级网表；可以直接编写，也可以由 EDA 工具生成。目标是在相同工艺和约束下超越商用综合 baseline。

当前任务是 unsigned `D = (A * B + C) mod 2^32`，16×16+32→32，纯组合逻辑，顶层 `mac16x16p32`。

```bash
bash env/setup_conda.sh
# 正式评测：所选提交必须已包含 Python harness
python eval/run.py rtl/baseline/baseline.synth.v --harness-ref HEAD
# 调试尚未提交的 harness
python eval/run.py rtl/baseline/baseline.synth.v --dev
```

默认运行目录为 `results/` 下的独立目录。可用 `--output` 指定新目录，既有结果不会被覆盖。流程包括 Yosys 网表检查、Icarus 仿真、OpenSTA 时序及 OpenROAD 面积；输出结构化 `summary.json`。正式入口从固定 Git 版本导出 harness 和工艺资源，baseline 与 candidate 接受相同检查。

`python eval/syn/run.py` 单独调用 Genus 重新综合 baseline；评测流程不调用综合。时序口径为 pre-layout，`arrival_time_ns` 包含输入外部延迟。

- `rtl/baseline/`：参考源码和固定综合网表
- `eval/`：评测实现与 JSON 配置
- `tests/`：统一回归测试
- `.agents/skills/mac-eval/`：技能与操作参考
- `env/`：安装；`tech/`：工艺资源

详细用法见[评估流程](.agents/skills/mac-eval/references/baseline_flow_zh.md)，Agent 入口见 [AGENTS.md](AGENTS.md)。
