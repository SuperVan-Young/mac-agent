# Timing 调试接口

本文档给 AI/worker 使用，说明如何查看比默认 `make timing` 更细的时序报告。

## 默认行为

默认 `make timing` 只生成一份汇总报告和一份最差路径报告：

- `results/fixed/eval_sta/timing_summary.rpt`
- `results/fixed/eval_sta/critical_path.rpt`

如果需要查看更多路径、或聚焦某些输入到输出的路径组合，请直接调用底层脚本。

## 基本调用

```bash
NETLIST_PATH="$(pwd)/results/fixed/generated/mac16x16p32.v" \
LIBERTY_PATHS="$(make -s print-config | awk -F= '/^LIBERTY_PATHS=/{print $2}')" \
SDC_PATH="$(pwd)/results/fixed/eval_sta/constraints.sdc" \
TOP_MODULE=mac16x16p32 \
TIMING_SUMMARY_REPORT="$(pwd)/results/fixed/eval_sta/timing_query_summary.rpt" \
CRITICAL_PATH_REPORT="$(pwd)/results/fixed/eval_sta/critical_path.rpt" \
bash eval/timing/run_timer.sh openroad \
  --max-paths 5 \
  --output-report "$(pwd)/results/fixed/eval_sta/top5_paths.rpt"
```

## 指定端点范围

如果要只看某些输入 pin 到某些输出 pin：

```bash
NETLIST_PATH="$(pwd)/results/fixed/generated/mac16x16p32.v" \
LIBERTY_PATHS="$(make -s print-config | awk -F= '/^LIBERTY_PATHS=/{print $2}')" \
SDC_PATH="$(pwd)/results/fixed/eval_sta/constraints.sdc" \
TOP_MODULE=mac16x16p32 \
TIMING_SUMMARY_REPORT="$(pwd)/results/fixed/eval_sta/timing_query_summary.rpt" \
CRITICAL_PATH_REPORT="$(pwd)/results/fixed/eval_sta/critical_path.rpt" \
bash eval/timing/run_timer.sh openroad \
  --from 'A[15],B[15]' \
  --to 'D[31]' \
  --max-paths 3 \
  --output-report "$(pwd)/results/fixed/eval_sta/a15_b15_to_d31.rpt"
```

## 常用参数

- `--max-paths N`：输出前 `N` 条路径
- `--endpoint-count N`：限制 endpoint 数量
- `--from`：指定起点 pin/port，逗号分隔
- `--to`：指定终点 pin/port，逗号分隔
- `--output-report`：指定详细报告输出文件

## 适用场景

- 默认最差路径不够，想多看几条 path
- 想比较不同输入 pin 到输出 pin 的组合
- 想确认优化是不是只改善了一条局部路径
