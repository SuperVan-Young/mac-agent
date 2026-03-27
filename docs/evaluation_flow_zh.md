# 设计评测流程

## 评测一个 baseline

### 1. RTL 仿真

```bash
mkdir -p results/baseline
bash sim/run_rtl_sim.sh -d rtl/baseline.v > results/baseline/sim.log
```

### 2. Genus 综合

```bash
genus -no_gui -files syn/run.tcl
```

### 3. OpenROAD STA

```bash
bash eval/run_timer.sh \
  --netlist syn/outputs/baseline_mapped.v \
  --sdc eval/templates/minimal.sdc
```

### 4. 面积统计

```bash
python3 eval/area_report.py \
  --netlist syn/outputs/baseline_mapped.v \
  --liberty tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib:tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib \
  --out results/baseline/area.json
```

### 5. 汇总

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

## 评测一个 candidate

candidate 不允许再跑综合工具。

推荐流程：

### 1. 先做 candidate 合法性检查

```bash
python3 tools/check_candidate_netlist.py rtl/candidate_xxx.v
```

如果仓库内存在 repo-local ASAP7 liberty bundle，checker 会自动用它构建 allowlist。

### 2. 再做仿真

```bash
mkdir -p results/candidate_xxx
bash sim/run_rtl_sim.sh -d rtl/candidate_xxx.v > results/candidate_xxx/sim.log
```

### 3. 对 candidate 网表做 OpenROAD STA

```bash
bash eval/run_timer.sh \
  --netlist rtl/candidate_xxx.v \
  --sdc eval/templates/minimal.sdc \
  --out-dir results/candidate_xxx/eval_sta
```

### 4. 做面积统计

```bash
python3 eval/area_report.py \
  --netlist rtl/candidate_xxx.v \
  --liberty tech/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib:tech/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib:tech/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib \
  --out results/candidate_xxx/area.json
```

### 5. 汇总

```bash
python3 eval/parse_reports.py \
  --design-name candidate_xxx \
  --design-type candidate \
  --sim-log results/candidate_xxx/sim.log \
  --timing-summary results/candidate_xxx/eval_sta/timing_summary.rpt \
  --critical-path results/candidate_xxx/eval_sta/critical_path.rpt \
  --area-json results/candidate_xxx/area.json \
  --results-dir results/candidate_xxx \
  --write-csv
```
