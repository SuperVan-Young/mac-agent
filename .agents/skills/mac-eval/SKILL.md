---
name: mac-eval
description: 在 mac-agent 仓库检查 PDK 门级网表，运行 MAC 仿真与 OpenSTA/OpenROAD 评测、Genus baseline 综合，或排查时序和面积报告。
---

# MAC 评估

运行或修改 harness 前读 [评估流程](references/baseline_flow_zh.md)。时序端点查询读 [Timing 排查](references/timing_debug_guide_zh.md)；面积贡献分析读 [Area 排查](references/area_debug_guide_zh.md)。

交付对象是自包含的 Verilog 网表。Agent 可以直接编写，也可以用生成器产生；harness 验收文件本身。正式 MAC 契约为 unsigned 16×16+32→32、纯组合逻辑，输出取低 32 位。全部可达叶子必须是指定 ASAP7 组合单元，baseline 与 candidate 接受相同检查。

`python eval/run.py candidate.v --harness-ref <commit>` 从指定提交导出 evaluator 和工艺资源，导入候选快照后评测。`--dev` 使用工作区代码，结果明确标为 development。正式流程需要提交中已存在 Python harness；没有时报告 setup error，不回退到工作区。

唯一配置源为 `eval/config.json`。正式运行使用所选提交中的配置；开发运行允许 `--config`。评分、优化迭代和历史排名由外部框架负责；本仓库仅判定合法性、仿真正确性及已配置指标约束。

读 `summary.json` 时同时检查 `execution_status`、`validity`、`pass`、`constraints` 和 `mode`。部分阶段成功不代表完整验收；超时或工具错误不代表候选功能错误，也不算通过。`arrival_time_ns` 包含输入外部延迟，口径为 pre-layout、无提取寄生；不能称为纯电路延迟或 post-route PPA。

修改 harness 或仿真后运行 `python -m unittest discover -s tests -v`。报告使用的提交、候选 hash、结果目录和未完成项目。当前正确性依据仍为仿真，不是形式证明。
