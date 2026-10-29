# MAC 评估流程

## 环境与入口

从仓库根目录运行，Python 3.10+。环境安装保留 Shell：

```bash
bash env/setup_conda.sh
```

评测依赖 Yosys、Icarus (`iverilog`/`vvp`)、OpenSTA 和 OpenROAD；仅综合需要 Genus。Python 脚本使用标准库。工具默认目录及评测条件见 `eval/config.json`。环境安装会补齐 OpenROAD 使用的 fmt 8 ABI。

正式运行：

```bash
python eval/run.py candidate.v --harness-ref <committed-revision> --output results/run-001
python eval/run.py rtl/baseline/baseline.synth.v --harness-ref <committed-revision>
```

`--harness-ref` 默认 HEAD，启动时解析为完整 commit。必须选择包含 Python harness 的提交。工作区尚未提交的 evaluator 变化不进入正式运行；候选本身可以未提交。正式运行只接受完整流程，不能覆盖配置或跳过 checker。

流程：候选快照 → Yosys 检查/结构展开 → 仿真 → 全设计时序 → 面积 → 单次结果。没有综合、技术映射或性能优化 pass。各测量阶段使用同一份 `check/mapped.v`，原提交保留为 `candidate.v`；两者分别记录 hash。

每次运行使用新目录；显式 `--output` 目录已存在时拒绝运行，保留其内容。默认生成 `results/<unique-run>/`。运行产物不入 Git，框架可以指定其他路径。

## 开发调试

```bash
python eval/run.py rtl/baseline/baseline.synth.v --dev
python eval/run.py candidate.v --dev --stage check
python eval/run.py candidate.v --dev --stage sim
python eval/run.py candidate.v --dev --stage timing
python eval/run.py candidate.v --dev --stage area --area-detail
python eval/run.py candidate.v --dev --config /path/to/config.json
```

`--config` 是完整 JSON 配置文件，不是局部覆盖。部分阶段仍先运行所需前置检查；结果不会声明完整验收通过。baseline 无特殊免检分支。开发结果的 `mode` 为 `development`。

正式隔离通过 Git archive 导出固定版本的 `eval/` 和 `tech/` 实现，工作区仅提供启动器与候选。它是可复现执行边界，不是权限沙箱；有相同系统权限的进程仍能修改文件。正式评分方应控制认可的 harness commit，并使用可信启动器。

## 网表契约

- 顶层 `mac16x16p32`，A/B 为 unsigned 16 位输入，C 为 unsigned 32 位输入，D 为 32 位输出。
- 数学语义：`D = (A * B + C) mod 2^32`，无时钟、状态或额外延迟。
- 单文件、自包含，允许内部层次；可达叶子仅限配置中的 ASAP7 组合单元。
- 允许纯连线、0/1 常量、位选择与拼接；不接受未映射运算/primitive、过程块、存储器、未知单元、PDK 同名定义、X/Z 常量、外部 include 或条件预处理。
- Yosys 解析并验证层次、连接、驱动和组合环；不执行 `synth`、`abc` 或补充映射。
- 结构合法不等于功能正确；当前使用定向与随机向量仿真，形式验证尚未加入。

## 结果协议

每次实际评测都写 `summary.json`；正常 worker 运行还写 `summary.csv`。启动失败尽可能在新目录写 setup error，已存在目录始终不覆盖。

- `execution_status`：`completed` / `error` / `timeout`。
- `validity`：`valid` / `invalid` / `not_established`。
- `pass`：只有完整、有效并满足已配置指标约束才为 true。
- `correctness`：仿真状态、方法、种子与向量数量。
- `constraints.timing`：按配置的 WNS 下限判定；默认 0 ns。
- `constraints.area`：默认 `not_set`；只报告面积，不自行设定面积预算。
- `metrics`：`arrival_time_ns`、`wns_ns`、`tns_ns`、`area_um2`、`cell_count`。阶段失败时为 null。
- `failed_stage` / `stages`：定位错误、各阶段耗时与状态。
- `candidate_sha256` / `evaluated_netlist_sha256`：原候选和检查后网表的身份。
- `tool_versions`：工具路径、二进制 hash 和版本输出。`manifest.json` 保存 harness/PDK 文件 hash 与配置指纹；`config.json` 保存完整生效配置。
- 正式运行额外记录 `harness_commit`，并保存 `harness/` 源码供检查。

退出码：0 为完整通过或请求的单阶段完成；1 为非法/错误候选或指标约束失败；2 为工具/启动错误；3 为阶段超时。必须结合 JSON 判读单阶段结果，不能仅凭退出码宣称完整通过。

阶段工具子进程有超时并清理其进程组。超时限制来自配置，各工具调用独立计时。没有综合 score，也不自动 promote、commit 或 push。

## 测量口径

保留此前的 ASAP7 TT/RVT Liberty、LEF 及 1 ns 周期、0.1 ns 输入/输出 delay。未新增输入驱动、输出负载或布局布线寄生设置。`arrival_time_ns` 是报告中的 data arrival time，包含 `input_external_delay_ns`。本轮不推导纯电路传播延迟。

baseline 与 candidate 必须用同一提交和测量配置比较。`timing pass` 仅指满足当前约束，不表示胜过 baseline。

## 显式综合与参数化开发

```bash
python eval/syn/run.py --output results/syn-001
python eval/run.py results/syn-001/baseline_mapped.v --dev
```

Genus 默认输入 `rtl/baseline/baseline.v`。它只写新运行目录，不覆盖已提交 baseline。参数化综合与独立仿真用于开发：

```bash
python eval/syn/run.py --widths 8 8 16 --cycles 2 --output results/syn-pipe
python eval/sim/run.py rtl/baseline/baseline.v --widths 8 8 16 --cycles 2 --output results/sim-pipe
```

这些可变接口不属于本轮固定 MAC 正式验收任务。
