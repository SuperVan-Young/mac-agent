# Baseline 评测流程

本文档给 human user 使用，说明如何运行 baseline 设计的完整评测。

## 环境准备

需要以下工具可用：

- `genus`
- `python3`
- `iverilog`
- `vvp`
- `conda`

OpenROAD conda 环境可按需检查：

```bash
bash env/setup_openroad_conda.sh --prefix /tmp/mac-agent-openroad-env --skip-install
```

## 一键运行 baseline

在仓库根目录执行：

```bash
make clean && make all \
  DESIGN_NAME=baseline \
  DESIGN_TYPE=baseline \
  DUT=$(pwd)/rtl/baseline.v \
  CHECK_ENABLE=0
```

流程顺序为：

1. `synth`
2. `sim`
3. `timing`
4. `area`
5. `summary`

## 结果位置

默认结果放在固定目录：

```text
results/fixed/
```

关键文件：

- `results/fixed/summary.json`
- `results/fixed/logs/sim.log`
- `results/fixed/logs/sta.log`
- `results/fixed/eval_sta/timing_summary.rpt`
- `results/fixed/eval_sta/critical_path.rpt`
- `results/fixed/eval_sta/design_area.rpt`
- `results/fixed/area.json`

## 说明

- baseline 会先通过 Genus 生成综合网表，再走后续统一评测流程
- `CHECK_ENABLE=0` 是因为 baseline 不走 candidate legality check
