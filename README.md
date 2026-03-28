# Integer MAC 评估框架

目标函数为 `D = A * B + C`。candidate 契约接口固定为 `A/B=16-bit`、`C/D=32-bit`、顶层 `mac16x16p32`；baseline 在 Make/config 中支持可配置位宽与 pipeline（默认仍为 `16x16->32`, cycle=1）。

当前 agent 工作入口：

- [AGENTS.md](/home/xuechenhao/mac-agent/AGENTS.md)
- [scheduler.md](/home/xuechenhao/mac-agent/scheduler.md)
- [worker.md](/home/xuechenhao/mac-agent/worker.md)
- [docs/baseline_flow_zh.md](/home/xuechenhao/mac-agent/docs/baseline_flow_zh.md)
- [docs/timing_debug_guide_zh.md](/home/xuechenhao/mac-agent/docs/timing_debug_guide_zh.md)
- [tech/asap7/README.md](/home/xuechenhao/mac-agent/tech/asap7/README.md)

环境准备统一入口：

- `bash env/setup_conda.sh`
- Python 依赖统一由仓库根目录的 `requirements.txt` 管理
