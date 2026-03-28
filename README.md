# Integer MAC 评估框架

目标函数为 `D = A * B + C`。candidate 契约接口固定为 `A/B=16-bit`、`C/D=32-bit`、顶层 `mac16x16p32`；baseline 在 Make/config 中支持可配置位宽与 pipeline（默认仍为 `16x16->32`, cycle=1）。

当前 agent 工作入口：

- [AGENTS.md](/home/xuechenhao/mac-agent/AGENTS.md)
- [agents/roles/scheduler.md](/home/xuechenhao/mac-agent/agents/roles/scheduler.md)
- [agents/roles/worker.md](/home/xuechenhao/mac-agent/agents/roles/worker.md)
- [agents/roles/refactor.md](/home/xuechenhao/mac-agent/agents/roles/refactor.md)
- [agents/guides/timing_debug_guide_zh.md](/home/xuechenhao/mac-agent/agents/guides/timing_debug_guide_zh.md)
- [agents/guides/area_debug_guide_zh.md](/home/xuechenhao/mac-agent/agents/guides/area_debug_guide_zh.md)
- [docs/baseline_flow_zh.md](/home/xuechenhao/mac-agent/docs/baseline_flow_zh.md)
- [docs/compiler_testing_zh.md](/home/xuechenhao/mac-agent/docs/compiler_testing_zh.md)
- [tech/asap7/README.md](/home/xuechenhao/mac-agent/tech/asap7/README.md)

评估脚本统一收敛在 `eval/` 下，按流程拆分为：

- `eval/check/`
- `eval/sim/`
- `eval/syn/`
- `eval/timing/`
- `eval/area/`
- `eval/summary/`

Candidate 默认流程现在包含 RTL 生成步骤：

- `make generate`
- `make clean && make all`

默认生成产物位于 `results/fixed/generated/mac16x16p32.v`，可用 `DUT=...` 或 `GENERATE_ENABLE=0` 覆盖。

环境准备统一入口：

- `bash env/setup_conda.sh`
- Python 依赖统一由仓库根目录的 `requirements.txt` 管理
