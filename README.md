# Integer MAC 评估框架

本仓库用于评估整数乘累加器：

```text
D = A * B + C
```

默认接口固定为：

- `A`: 16-bit
- `B`: 16-bit
- `C`: 32-bit
- `D`: 32-bit
- 语义：`unsigned`
- 顶层模块名：`mac16x16p32`

当前仓库支持三件事：

1. RTL 仿真验证功能正确性
2. 用 Cadence Genus 做 baseline 综合
3. 用 OpenROAD/OpenSTA 做网表时序评估，并用脚本汇总结果

## 目录说明

```text
rtl/         设计文件
sim/         RTL 仿真
syn/         Genus 综合脚本
eval/        OpenROAD/OpenTimer 评估与结果汇总
env/         OpenROAD conda 环境辅助脚本
tech/        repo-local ASAP7 工艺库
results/     评估结果输出
```

## 依赖

### 仿真

需要：

- `iverilog`
- `vvp`
- `python3`

### 综合

需要：

- `genus`

当前仓库已经按 Cadence Genus 写好 [syn/run.tcl](/home/xuechenhao/mac-agent/syn/run.tcl)。

### 时序评估

需要：

- `conda`
- `openroad`

可用下面命令准备本地环境：

```bash
bash env/setup_openroad_conda.sh
```

如果环境已经装好，只想检查：

```bash
bash env/setup_openroad_conda.sh --prefix /tmp/mac-agent-openroad-env --skip-install
```

## 默认工艺库

仓库默认使用 repo-local ASAP7 TT/RVT liberty bundle：

- [tech/asap7/README.md](/home/xuechenhao/mac-agent/tech/asap7/README.md)
- [tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib](/home/xuechenhao/mac-agent/tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib)
- [tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib](/home/xuechenhao/mac-agent/tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib)
- [tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib](/home/xuechenhao/mac-agent/tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib)
- [tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib](/home/xuechenhao/mac-agent/tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib)
- [tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib](/home/xuechenhao/mac-agent/tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib)

综合和 STA 默认都会使用这些文件，不传额外参数也能工作。

## 1. 如何做 RTL 仿真

默认仿真 baseline：

```bash
bash sim/run_rtl_sim.sh -d rtl/baseline.v
```

仿真其它设计：

```bash
bash sim/run_rtl_sim.sh -d rtl/candidate_xxx.v
```

常用参数：

- `-d`：指定 DUT 文件
- `-n`：随机向量个数，默认 `5000`
- `-s`：随机种子
- `-o`：输出目录，默认 `sim/out`

示例：

```bash
bash sim/run_rtl_sim.sh -d rtl/baseline.v -n 2000 -s 7
```

判定标准：

- 终端出现 `RESULT: PASS`
- 终端出现 `SIMULATION_STATUS=PASS`

仿真失败时会打印：

- 输入向量
- 期望值
- 实际值

## 2. 如何用 Genus 综合 baseline

直接运行：

```bash
genus -no_gui -files syn/run.tcl
```

默认行为：

- 读取 [rtl/baseline.v](/home/xuechenhao/mac-agent/rtl/baseline.v)
- 使用 repo-local ASAP7 liberty bundle
- 输出到：
  - [syn/outputs/baseline_mapped.v](/home/xuechenhao/mac-agent/syn/outputs/baseline_mapped.v)
  - [syn/reports/baseline_timing.rpt](/home/xuechenhao/mac-agent/syn/reports/baseline_timing.rpt)
  - [syn/reports/baseline_area.rpt](/home/xuechenhao/mac-agent/syn/reports/baseline_area.rpt)

只做脚本检查，不真正综合：

```bash
GENUS_DRY_RUN=1 tclsh syn/run.tcl
```

可覆盖的环境变量：

- `GENUS_TOP`
- `GENUS_RTL`
- `GENUS_LIB`
- `GENUS_CLK_PERIOD`
- `GENUS_OUT_DIR`
- `GENUS_RPT_DIR`

例如改时序目标：

```bash
GENUS_CLK_PERIOD=0.8 genus -no_gui -files syn/run.tcl
```

## 3. 如何用 OpenROAD 做 STA 评估

对一个综合网表做 STA：

```bash
bash eval/run_timer.sh \
  --netlist syn/outputs/baseline_mapped.v \
  --sdc eval/templates/minimal.sdc
```

默认行为：

- 默认使用 repo-local ASAP7 liberty bundle
- 优先调用当前 `PATH` 里的 `openroad`
- 如果没激活环境，则回退到：
  - `conda run -p /tmp/mac-agent-openroad-env openroad`

输出目录默认是：

```text
results/<netlist_basename>/eval_sta/
```

主要输出：

- `timing_summary.rpt`
- `critical_path.rpt`
- `sta.log`

只检查命令解析，不实际跑：

```bash
bash eval/run_timer.sh \
  --netlist syn/outputs/baseline_mapped.v \
  --sdc eval/templates/minimal.sdc \
  --dry-run
```

如果你想显式指定 liberty bundle，也可以手工传：

```bash
bash eval/run_timer.sh \
  --netlist syn/outputs/baseline_mapped.v \
  --sdc eval/templates/minimal.sdc \
  --liberty tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib:tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
```

## 4. 如何汇总一个 design 的评估结果

### 4.1 面积统计

对一个网表按 liberty 面积求和：

```bash
python3 eval/area_report.py \
  --netlist syn/outputs/baseline_mapped.v \
  --liberty tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib:tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib \
  --out results/baseline/area.json
```

### 4.2 统一汇总

如果你已经有：

- 仿真日志
- timing report
- area json

可以生成统一 summary：

```bash
python3 eval/parse_reports.py \
  --design-name baseline \
  --design-type baseline \
  --sim-log results/baseline/sim.log \
  --timing-summary syn/reports/baseline_timing.rpt \
  --area-json results/baseline/area.json \
  --results-dir results/baseline \
  --write-csv
```

输出：

- [results/baseline/summary.json](/home/xuechenhao/mac-agent/results/baseline/summary.json)
- [results/baseline/summary.csv](/home/xuechenhao/mac-agent/results/baseline/summary.csv)

## 5. 推荐评测流程

评测一个 design，推荐按这个顺序：

1. RTL 仿真

```bash
bash sim/run_rtl_sim.sh -d rtl/<design>.v
```

2. 如果是 baseline，需要先做 Genus 综合

```bash
genus -no_gui -files syn/run.tcl
```

3. 对综合网表做 OpenROAD STA

```bash
bash eval/run_timer.sh \
  --netlist syn/outputs/baseline_mapped.v \
  --sdc eval/templates/minimal.sdc
```

4. 做面积统计和汇总

```bash
python3 eval/area_report.py \
  --netlist syn/outputs/baseline_mapped.v \
  --liberty tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib:tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib \
  --out results/baseline/area.json

python3 eval/parse_reports.py \
  --design-name baseline \
  --design-type baseline \
  --sim-log results/baseline/sim.log \
  --timing-summary syn/reports/baseline_timing.rpt \
  --area-json results/baseline/area.json \
  --results-dir results/baseline \
  --write-csv
```

## 6. 当前仓库状态

当前 baseline 已经验证过：

- RTL 仿真可通过
- Genus 可以在本机启动并完成综合
- OpenROAD 可以正确读取 repo-local ASAP7 liberty bundle

如果后续要评测 candidate，建议先做：

```bash
python3 tools/check_candidate_netlist.py rtl/candidate_xxx.v
```

再进入仿真和评估流程。
