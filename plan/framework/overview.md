# Integer MAC Agent Evaluation Framework

## 1. 目标

为整数乘累加器 `D = A * B + C` 搭建一个可复现、可自动化、可在 5 分钟内完成单次评估的框架。

约束如下：

- `A`、`B` 固定为 16-bit。
- `C`、`D` 固定为 32-bit。
- Baseline 使用 Synopsys DesignWare 已有实现。
- Agent 生成版本与 baseline 放在同一 RTL 目录下统一管理。
- 正确性通过 RTL 仿真评估。
- Agent 最终产物不走 DC 从 RTL 再综合，而是要求直接输出“可用于时序/面积评估的综合后网表”。
- 时序评估使用 OpenROAD 提供的 OpenTimer，不依赖 DC 的时序分析。

本计划先定义项目结构、评估接口、运行流程与里程碑，不在本文件中展开具体脚本实现细节。

## 2. 总体思路

框架拆为四条链路：

1. `Baseline` 链路  
   使用 `rtl/baseline.v` 中的 DesignWare 风格实现，通过 DC 在当前 PDK / liberty 上综合，得到 baseline 网表与基础 PPA 参考。

2. `Candidate` 链路  
   Agent 直接生成门级网表或近门级结构化 Verilog，放入 `rtl/`，不再经过 DC 做综合，只做合法性检查、仿真和 OpenTimer 分析。

3. `Simulation` 链路  
   对 baseline 和 candidate 使用统一 testbench、统一向量集、统一 checker 做功能正确性验证。

4. `Evaluation` 链路  
   对 baseline 的 DC 输出网表，以及 agent 直接生成的网表，统一用 liberty + OpenTimer 进行时序分析，并辅以简单面积/单元统计，形成横向对比。

## 3. 建议目录结构

```text
rtl/
  baseline.v              # DesignWare baseline RTL
  candidate_*.v           # agent 生成的结构化 RTL / 门级网表

syn/
  run.tcl                 # 最简 DC 综合脚本，仅用于 baseline
  reports/
  outputs/

sim/
  tb_mac.sv               # 统一 testbench
  vectors.py              # 向量生成脚本（定向 + 随机）
  run_rtl_sim.sh          # RTL 仿真入口
  run_gate_sim.sh         # 网表仿真入口（可选）

eval/
  run_timer.sh            # OpenTimer 分析入口
  parse_reports.py        # 提取 correctness / timing / area 摘要
  area_report.py          # 基于 liberty 的面积统计

plan/
  framework/
    overview.md           # 本文件

env/
  environment.yml         # OpenTimer / 仿真依赖的 conda 环境

results/
  baseline/
  candidate/
```

说明：

- `rtl/` 只放待评估设计，不放 testbench。
- `syn/` 只服务 baseline，避免误用到 candidate。
- `sim/` 只承担功能正确性仿真。
- `eval/` 专门承担 PPA 评估，和 `sim/` 解耦。
- `results/` 用于存放单次运行结果，便于 agent 自动比较。

## 4. 各模块职责

### 4.1 Baseline

目标：

- 在 `rtl/baseline.v` 中放入基于 Synopsys DesignWare 的 MAC baseline。
- 用 DC 在当前 PDK 上综合为门级网表。
- 生成 baseline 的参考指标：
  - Worst Negative Slack / Critical Path Delay
  - Cell Area
  - Cell Count
  - 功能正确性通过情况

建议约束：

- baseline 只作为参考上界/下界，不参与 agent 迭代修改。
- baseline 输出统一命名为：
  - `syn/outputs/baseline_mapped.v`
  - `syn/reports/baseline_timing.rpt`
  - `syn/reports/baseline_area.rpt`

### 4.2 Agent Candidate

目标：

- Agent 不输出行为级 RTL，而是直接输出可评估的结构化 Verilog 网表。
- 该网表应仅实例化当前 PDK 标准单元，或者实例化一个明确定义的受限门级原语集合。

核心约束：

- 禁止将 candidate 再送入 DC 做综合优化。
- 允许做以下轻量步骤：
  - 语法检查
  - 连接性/端口合法性检查
  - 仿真编译
  - OpenTimer 时序分析

建议输入输出契约：

- 输入给 agent：
  - MAC 功能定义
  - 目标 liberty / 单元白名单
  - 时序目标（例如 target period）
  - 评估脚本接口
- agent 输出：
  - `rtl/candidate_<tag>.v`
  - 可选说明文件 `results/candidate/<tag>/notes.md`

### 4.3 仿真

目标：

- 快速判断 candidate 是否功能正确。
- 在 5 分钟预算内优先排除明显错误设计。

仿真策略：

- 使用统一 testbench `sim/tb_mac.sv`。
- baseline 与 candidate 共用同一套向量。
- 采用“两阶段向量”：
  - 定向向量：覆盖边界条件、符号位/进位敏感点、全 0、全 1、最大乘积、溢出附近组合。
  - 小规模随机向量：例如 5k 到 20k 组，数量按工具速度可调。

推荐检查点：

- `A=0`、`B=0`
- `A=16'hffff`、`B=16'hffff`
- `A=16'h8000`、`B=16'h8000`
- `C=0`、`C=32'hffff_ffff`
- 高位进位传播场景
- 若定义涉及 signed/unsigned，需显式固定语义并单独覆盖

时间控制建议：

- 默认仅运行定向 + 5k 随机。
- 发现通过后，再允许离线扩展到更大随机集。
- 单次仿真目标控制在 1 分钟以内。

关键前提：

- 需要先明确这是 `unsigned MAC` 还是 `signed MAC`。  
  当前建议默认按 `unsigned` 处理，避免 baseline 与 candidate 在乘法语义上不一致。

### 4.4 OpenTimer 评估

目标：

- 对 baseline 网表和 candidate 网表做统一时序评估。
- 尽量避免依赖商业工具，降低环境安装门槛。

方案：

- 使用 conda 环境安装 OpenROAD / OpenTimer 相关工具。
- 准备一个最小 STA 驱动脚本，输入包括：
  - 网表
  - liberty
  - SDC

目录约束：

- OpenTimer、面积统计、结果汇总脚本统一放在 `eval/`。
- `sim/` 中不再混放任何 PPA 评估逻辑。

产出指标：

- 最大频率或最小时钟周期
- WNS / TNS
- 关键路径摘要

补充指标：

- 面积可通过以下两种方式择一：
  1. 对 candidate 网表按 liberty 中单元面积求和
  2. 用 Yosys / 自定义 parser 统计实例并映射面积

由于 candidate 不经过 DC，面积评估建议采用“liberty 面积求和”，这样 baseline 和 candidate 可统一口径比较。

## 5. 最小可交付脚本定义

### 5.1 `syn/run.tcl`

职责：

- 读取 `rtl/baseline.v`
- 设定顶层模块
- 读取目标库和 link 库
- 设置简单时钟约束
- `compile` 或 `compile_ultra` 的最简版本
- 输出映射网表和基础 report

定位：

- 该脚本只用于 baseline，不用于 candidate。
- 脚本必须尽量短，减少环境依赖和调参复杂度。

### 5.2 `sim/run_rtl_sim.sh`

职责：

- 编译 baseline/candidate 与统一 testbench
- 运行定向 + 小规模随机测试
- 输出 pass/fail 与失败样例

建议：

- 支持命令行参数指定 DUT 文件与 top name。
- 若仓库已有仿真器，优先用现成工具；否则默认兼容 `iverilog` 或 `verilator`。

### 5.3 `eval/run_timer.sh`

职责：

- 接收网表、liberty、SDC
- 调 OpenTimer / OpenROAD 的 STA 能力
- 输出 timing summary

### 5.4 `eval/parse_reports.py`

职责：

- 汇总以下结果为统一表格：
  - correctness
  - critical delay / WNS
  - area
  - cell count
  - runtime

### 5.5 `eval/area_report.py`

职责：

- 读取 candidate 或 baseline 网表
- 结合 liberty 中的单元面积信息统计总面积
- 输出统一格式面积报告，供 `parse_reports.py` 汇总

## 6. 建议的评估流程

单次评估建议按以下顺序执行：

1. 准备 baseline
   - 用 DC 综合 `rtl/baseline.v`
   - 存档 baseline 网表与报告

2. 生成 candidate
   - Agent 直接生成 `rtl/candidate_<tag>.v`
   - 检查是否只使用允许单元/原语

3. 功能仿真
   - baseline 先跑一遍，确认 testbench 无误
   - candidate 跑同一套向量
   - 失败则立即淘汰，不进入后续评估

4. 时序/面积评估
   - baseline mapped netlist 走 OpenTimer
   - candidate netlist 走 OpenTimer
   - `eval/` 中的统一脚本汇总 timing / area 结果

5. 排名
   - 首先以功能正确为硬门槛
   - 然后比较 delay
   - 再比较 area
   - 最后可引入复合分数，例如 `score = alpha * delay + beta * area`

## 7. 5 分钟预算拆分

为了满足单次评估不超过 5 分钟，建议预算如下：

- 语法检查与准备：10 秒以内
- RTL 仿真：30 到 60 秒
- OpenTimer：30 到 90 秒
- 报告汇总：10 秒以内
- 预留波动：2 到 3 分钟

说明：

- baseline 的 DC 综合不应放在每次 candidate 评估都重复执行。  
  正确做法是：baseline 只在切换 PDK / liberty / 约束后重新生成一次。
- candidate 评估应只包含：
  - 仿真
  - `eval/run_timer.sh`
  - `eval/area_report.py`

这样单次 candidate 迭代更容易稳定控制在 5 分钟内。

## 8. 关键技术决策

### 8.1 为什么 baseline 用 DC，candidate 不用 DC

- baseline 目标是获得业界成熟 IP 在当前工艺下的参考实现。
- candidate 若再走 DC，会把 agent 的结构优势与综合器优化能力混在一起，难以判断 agent 本身是否真的优于 DesignWare。
- 因此应把 candidate 约束为“直接生成可评估网表”，只做分析，不做再综合。

### 8.2 为什么时序分析选 OpenTimer

- 开源，可复现，易部署。
- 只要有 liberty、网表和约束即可运行。
- 适合作为 agent 大规模迭代中的轻量评估器。

### 8.3 为什么先做功能硬过滤

- 不正确的设计即使时序更好也没有意义。
- 先用轻量仿真过滤，可以显著减少后续无效 STA 开销。

## 9. 风险与应对

### 风险 1：signed / unsigned 语义不清

影响：

- baseline、candidate、testbench 可能比较出错。

应对：

- 在项目开始时固定接口语义。  
  当前建议：第一版按 `unsigned` 实现，后续若需要再扩展 `signed` 版本。

### 风险 2：agent 输出网表不符合库约束

影响：

- OpenTimer 可跑，但实际不可综合或不可物理实现。

应对：

- 给 agent 明确单元白名单。
- 在仿真前增加实例合法性检查脚本。

### 风险 3：面积统计口径不一致

影响：

- baseline 与 candidate 对比不公平。

应对：

- 统一从 liberty 获取单元面积，按实例求和。
- baseline 即使有 DC area report，也同时跑一次统一面积统计脚本。

### 风险 4：单次评估超时

影响：

- agent 搜索效率过低。

应对：

- baseline 综合离线缓存。
- 减少随机向量数。
- STA 只跑单角、单模式、单时钟。

## 10. 分阶段实施计划

### Phase 1：框架打底

交付：

- 建立目录结构
- 放置 `rtl/baseline.v`
- 提供 `syn/run.tcl`
- 提供最小 testbench 与 `sim/run_rtl_sim.sh`
- 提供 `eval/run_timer.sh`
- 提供 `eval/area_report.py`

验收标准：

- baseline 能完成一次 DC 综合
- baseline 能完成一次 RTL 仿真
- baseline 网表能完成一次 OpenTimer 分析

### Phase 2：统一报告与自动化

交付：

- `eval/parse_reports.py`
- `results/` 结果归档
- 一键运行入口，例如 `make eval-baseline` / `make eval-candidate`

验收标准：

- baseline 与 candidate 可输出统一格式结果表

### Phase 3：接入 agent 搜索

交付：

- candidate 文件命名规范
- agent 输出校验器
- 自动淘汰功能错误设计
- 基于 timing/area 的排序规则

验收标准：

- agent 可以稳定提交候选网表并得到自动评分

## 11. 当前建议的明确事项

在真正开始写脚本前，建议先固定以下 5 项：

1. MAC 按 `unsigned` 还是 `signed`
2. baseline 顶层模块名
3. 当前 PDK 对应的 `liberty` 路径
4. RTL 仿真器选择：`iverilog`、`verilator` 或其他
5. OpenTimer/OpenROAD 安装方式：纯 conda 还是系统已有环境

若以上信息尚未固定，第一版框架建议按以下默认值推进：

- MAC 语义：`unsigned`
- 顶层模块名：`mac16x16p32`
- baseline 顶层与 candidate 顶层接口一致
- 仿真器：`iverilog`
- STA：conda 安装 OpenROAD/OpenTimer

## 12. 结论

该框架的核心原则是：

- 用 DC 只建立 baseline 参考；
- 用统一仿真保证功能正确；
- 用 OpenTimer 做 candidate 与 baseline 的统一时序分析；
- 用轻量、缓存化、单角评估把单次迭代控制在 5 分钟内；
- 把 agent 的输出限制为“直接可评估网表”，避免被 DC 二次优化掩盖真实性能。

按此计划推进后，下一步应优先实现：

1. `rtl/baseline.v`
2. `syn/run.tcl`
3. `sim/tb_mac.sv`
4. `sim/run_rtl_sim.sh`
5. `eval/run_timer.sh`
6. `eval/area_report.py`
