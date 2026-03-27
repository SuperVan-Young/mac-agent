# RTL 仿真指南

## 目标

验证一个 design 的功能正确性。

当前 testbench 针对：

- 顶层：`mac16x16p32`
- 功能：`D = A * B + C`
- 语义：`unsigned`

## 依赖

需要：

- `iverilog`
- `vvp`
- `python3`

## 基本用法

仿真 baseline：

```bash
bash sim/run_rtl_sim.sh -d rtl/baseline.v
```

仿真 candidate：

```bash
bash sim/run_rtl_sim.sh -d rtl/candidate_xxx.v
```

如果 candidate 是 ASAP7 门级网表，脚本会自动加入 `tech/asap7/verilog/stdcell/*.v`。

## 常用参数

- `-d`：DUT 路径
- `-n`：随机向量数量，默认 `5000`
- `-s`：随机种子
- `-o`：输出目录，默认 `sim/out`
- `-a`：A 输入位宽，默认 `16`
- `-b`：B 输入位宽，默认 `16`
- `-w`：C/D 累加位宽，默认 `32`
- `-p`：pipeline cycle，默认 `1`（当 `baseline` 且 `p>1` 时启用时序流水检查）

示例：

```bash
bash sim/run_rtl_sim.sh -d rtl/candidate_seed.v -n 2000 -s 7
```

baseline 可配置位宽/流水示例：

```bash
bash sim/run_rtl_sim.sh -d rtl/baseline.v -n 2000 -s 7 -a 16 -b 16 -w 32 -p 1
```

## 成功判定

命令返回码为 `0`，并且输出中包含：

- `RESULT: PASS`
- `SIMULATION_STATUS=PASS`

## 失败判定

命令返回非零，输出中会包含失败样例上下文，例如：

- `A`
- `B`
- `C`
- expected `D`
- observed `D`

## 输出位置

默认输出在：

```text
sim/out/
```

包括：

- `vectors.txt`
- `simv.out`
