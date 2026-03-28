# Compiler 测试说明

本文档说明当前 `rtl/compiler/` 的测试组织方式，以及如何运行和新增测试。

## 1. 测试目标

当前编译器测试主要用于验证：

1. xDSL pass / pattern 能按预期完成变换
2. pass 不会在简单输入上莫名失败
3. 中间 IR 和最终产物可以被稳定检查

测试风格参考 MLIR 常见的 `lit` / `FileCheck` 用法，但实现上使用仓库内的一个轻量 runner。

## 2. 测试目录

测试位于：

```text
test/compiler/
```

子路径尽量对应 `rtl/compiler/` 的代码路径。例如：

```text
rtl/compiler/passes/lower_arith_ct_to_comp.py
test/compiler/passes/lower_arith_ct_to_comp/basic.mlir
```

当前入口文件：

- [test_lit.py](/home/xuechenhao/mac-agent/test/compiler/test_lit.py)
- [lit_runner.py](/home/xuechenhao/mac-agent/test/compiler/lit_runner.py)

## 3. 测试文件格式

每个测试文件都是一个 `.mlir` 文件，包含三部分：

1. `// RUN:` 注释
2. `// CHECK:` / `// CHECK-NOT:` 注释
3. 输入 IR

示例：

```mlir
// RUN: compiler-opt --pass lower-arith-ct-to-comp
// CHECK: "comp.ha"() {instance_name = "ct_c0_ha"
// CHECK: "comp.fa"() {instance_name = "ct_c1_fa"
// CHECK-NOT: "arith.compressor_tree"()
"builtin.module"() ({
  "arith.compressor_tree"() {reduction_type = "dadda", columns = ["c0=A[0],B[0]", "c1=pp_0_1,pp_1_0,C[0]"], owner = "arith.compressor_tree"} : () -> ()
}) : () -> ()
```

## 4. 支持的 RUN 语法

当前支持最小子集：

```text
// RUN: compiler-opt --pass <pass-name> [--pass <pass-name> ...] [--emit ir|verilog]
```

支持的 pass：

- `lower-arith-ct-to-comp`
- `lower-comp-to-asap7`

支持的输出：

- `--emit ir`
  - 默认值
  - 检查 pass 之后的 IR 文本
- `--emit verilog`
  - 把最终 ASAP7-only IR lower 为结构 Verilog 后检查文本

示例：

```mlir
// RUN: compiler-opt --pass lower-arith-ct-to-comp --pass lower-comp-to-asap7
```

```mlir
// RUN: compiler-opt --pass lower-arith-ct-to-comp --pass lower-comp-to-asap7 --emit verilog
```

## 5. 支持的 CHECK 语法

当前支持两种：

1. `// CHECK:`
   - 输出中必须出现
   - 按出现顺序匹配
2. `// CHECK-NOT:`
   - 输出中绝不能出现

注意：

1. `CHECK` 是顺序匹配，不是无序匹配。
2. 如果你要检查的内容出现在输出更前面，`CHECK` 行顺序也要相应提前。
3. 当前不支持 `CHECK-LABEL`、`CHECK-SAME`、正则 capture 等更复杂语法。

## 6. 如何运行测试

### 6.1 运行全部 compiler 测试

```bash
conda run -p /tmp/mac-agent-openroad-env pytest -q test/compiler
```

### 6.2 运行单个测试文件

```bash
conda run -p /tmp/mac-agent-openroad-env pytest -q test/compiler/passes/lower_arith_ct_to_comp/basic.mlir
```

### 6.3 按测试名筛选

使用 `pytest -k`：

```bash
conda run -p /tmp/mac-agent-openroad-env pytest -q test/compiler -k lower_arith_ct_to_comp
```

例如：

```bash
conda run -p /tmp/mac-agent-openroad-env pytest -q test/compiler -k comp_to_asap7
```

```bash
conda run -p /tmp/mac-agent-openroad-env pytest -q test/compiler -k demo_verilog
```

`-k` 匹配的是 pytest case 名。当前 case 名基本就是相对路径，例如：

- `passes/lower_arith_ct_to_comp/basic.mlir`
- `passes/lower_comp_to_asap7/basic.mlir`
- `pipeline/demo_verilog.mlir`

## 7. 如何新增测试

建议流程：

1. 找到你想测试的 compiler 模块路径
2. 在 `test/compiler/` 下建立对应子目录
3. 新增一个 `.mlir` 文件
4. 写 `RUN`
5. 写 `CHECK`
6. 填入输入 IR

例如要给 `rtl/compiler/passes/lower_comp_to_asap7.py` 新增测试，可以放在：

```text
test/compiler/passes/lower_comp_to_asap7/
```

## 8. 当前实现原理

这套方案不是直接使用 LLVM 的 `lit`，而是：

1. 用 `pytest` 发现所有 `.mlir` 文件
2. 用仓库内 `lit_runner.py` 解析注释中的 `RUN/CHECK`
3. 用 xDSL parser 读取输入 IR
4. 调用仓库内真实 pass
5. 将 IR 或 Verilog 文本输出出来
6. 做最小版顺序匹配检查

这样做的好处是：

1. 测试输入和期望都在一个文件里
2. 便于阅读 pass 产物
3. 不需要为每个 case 单独写 Python `assert`

## 9. 限制

当前是最小可用版本，有限制：

1. 不支持真正的 `lit` 工具链
2. 不支持 `CHECK-LABEL`
3. 不支持 `CHECK-SAME`
4. 不支持 capture / 回引用
5. 不支持一份文件里写多条 `RUN`

如果后续需要，再按实际需求逐步扩展，不建议一开始做成完整 FileCheck 复刻。
