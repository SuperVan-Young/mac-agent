# 设计评测流程

当前推荐统一使用 `make` 管理评测顺序。

## 评测一个 baseline

`baseline` 现在可由 `make all` 串联完整流程（综合+仿真+STA+面积+汇总）：

```bash
make all \
  DESIGN_NAME=baseline \
  DESIGN_TYPE=baseline \
  DUT=$(pwd)/rtl/baseline.v \
  CHECK_ENABLE=0
```

可配置参数（默认 `A/B=16`、`ACC=32`、`pipeline=1`）：

```bash
make all \
  DESIGN_NAME=baseline \
  DESIGN_TYPE=baseline \
  DUT=$(pwd)/rtl/baseline.v \
  CHECK_ENABLE=0 \
  MAC_A_WIDTH=16 \
  MAC_B_WIDTH=16 \
  MAC_ACC_WIDTH=32 \
  MAC_PIPELINE_CYCLES=1
```

## 评测一个 candidate

candidate 不允许再跑综合工具，推荐直接用 `make all`。

推荐流程：

```bash
make all DESIGN_NAME=candidate_xxx DUT=$(pwd)/rtl/candidate_xxx.v
```

默认顺序是：

1. `check`
2. `sim`
3. `timing`
4. `area`
5. `summary`

如果仓库内存在 repo-local ASAP7 liberty bundle，`check` 会自动用它构建 allowlist。
