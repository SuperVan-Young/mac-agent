# 设计评测流程

当前推荐统一使用 `make` 管理评测顺序。

## 评测一个 baseline

### 1. baseline 综合

```bash
genus -no_gui -files syn/run.tcl
```

### 2. baseline 评测

```bash
make all \
  DESIGN_NAME=baseline_mapped \
  DESIGN_TYPE=baseline \
  DUT=$(pwd)/syn/outputs/baseline_mapped.v \
  CHECK_ENABLE=0
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
