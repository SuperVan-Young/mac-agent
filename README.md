# Integer MAC 评估框架

目标函数为 `D = A * B + C`。candidate 契约接口固定为 `A/B=16-bit`、`C/D=32-bit`、顶层 `mac16x16p32`；baseline 在 Make/config 中支持可配置位宽与 pipeline（默认仍为 `16x16->32`, cycle=1）。

执行说明放在 `docs/`：

- [docs/simulation_guide_zh.md](/home/xuechenhao/mac-agent/docs/simulation_guide_zh.md)
- [docs/genus_guide_zh.md](/home/xuechenhao/mac-agent/docs/genus_guide_zh.md)
- [docs/openroad_eval_guide_zh.md](/home/xuechenhao/mac-agent/docs/openroad_eval_guide_zh.md)
- [docs/evaluation_flow_zh.md](/home/xuechenhao/mac-agent/docs/evaluation_flow_zh.md)
- [docs/contract.md](/home/xuechenhao/mac-agent/docs/contract.md)
- [docs/candidate_submission.md](/home/xuechenhao/mac-agent/docs/candidate_submission.md)
- [tech/asap7/README.md](/home/xuechenhao/mac-agent/tech/asap7/README.md)
