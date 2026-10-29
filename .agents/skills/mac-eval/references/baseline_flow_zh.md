# MAC 评估流程

所有命令从仓库根目录执行。默认配置在 `eval/config.mk`；命令行变量优先于 `CONFIG=/path/to/config.mk`，后者优先于默认值。

## 环境

```bash
bash env/setup_conda.sh
```

需要 `python3`、`iverilog`、`vvp`、`conda` 在 PATH 中。OpenROAD 默认环境是 `/tmp/mac-agent-openroad-env`，可用 `OPENROAD_CONDA_PREFIX` 覆盖。Python 评估脚本仅使用标准库。只有显式综合需要 Genus。

## 评估固定 baseline

```bash
make all
make print-config
```

默认 DUT 是 `rtl/baseline/baseline.synth.v`。流程依次进行 check、sim，随后 timing/area，最后汇总；baseline 默认跳过 candidate 专属的网表合法性检查。`make all` 不重新综合，不覆盖保存的 baseline 网表。

默认输出 `results/baseline/`：

- `summary.json`、`summary.csv`：汇总
- `logs/`：各阶段日志
- `sim/`：仿真向量和产物
- `eval_sta/`：SDC、timing、area 报告
- `area.json`：面积汇总
- `syn/outputs/`、`syn/reports/`：显式综合的产物

`make clean` 删除当前 `RESULTS_DIR`，不会删除 `rtl/baseline/`。同一结果目录再次评估会更新报告；比较多个设计时设置不同的 `DESIGN_NAME` 或 `RESULTS_DIR`。

## 独立阶段与其他网表

```bash
make sim
make timing
make area
make area-debug
make all DESIGN_NAME=my_candidate DESIGN_TYPE=candidate DUT=/absolute/path/to/netlist.v
```

`DESIGN_TYPE=candidate` 默认启用固定 unsigned 16×16→32 接口的结构合法性检查。也可显式设置 `CHECK_ENABLE`。`DUT` 同时用于仿真、timing 和 area，后两者要求已映射到工艺库的网表。评估器不会自动综合行为级 RTL。

`timing` 和 `area` 会先运行仿真。仿真默认使用 5000 个随机向量及边界用例，可用 `SIM_RANDOM_COUNT`、`SIM_SEED_LIST`、`SIM_PARALLEL_JOBS` 配置。

## 显式重新综合

```bash
make syn
make all DUT="$PWD/results/baseline/syn/outputs/baseline_mapped.v"
```

`make syn`（兼容别名 `make synth`）用 Genus 综合 `SYN_RTL`，默认是 `rtl/baseline/baseline.v`。它仅写运行产物，不替换已提交网表。

改变 baseline 位宽或流水级时，综合和评估使用相同配置，例如：

```bash
make syn DESIGN_NAME=baseline_pipe MAC_PIPELINE_CYCLES=2
make all DESIGN_NAME=baseline_pipe MAC_PIPELINE_CYCLES=2 \
  DUT="$PWD/results/baseline_pipe/syn/outputs/baseline_mapped.v"
```

位宽通过 `MAC_A_WIDTH`、`MAC_B_WIDTH`、`MAC_ACC_WIDTH` 配置。固定 baseline 网表不受这些变量改变；需要先重新综合。仅测试行为级源码可运行 `make sim DUT="$PWD/rtl/baseline/baseline.v"` 并传入相应参数。

## 评估器回归检查

修改仿真驱动或 testbench 后运行：

```bash
python3 -m unittest discover -s eval/sim/tests
```

覆盖组合与多种流水级，并确认错误结果能被检出。

## 结果解释

仿真 pass 仅说明向量检查通过；时序是否满足约束看 `timing_status`、WNS/TNS 及关键路径。面积使用 LEF 和 Liberty 的 OpenROAD 统计。详细诊断见同目录 timing/area 指南。

`eval/report.py` 将单次评估解析为统一指标，写入运行目录中的 `summary.json` 和 `summary.csv`。跨轮比较、排名及 promote/reject 决策归档由外部框架负责；旧记录可从 Git 历史读取。外部框架可用 `RESULTS_DIR=/absolute/path/to/run` 指定产物目录。
