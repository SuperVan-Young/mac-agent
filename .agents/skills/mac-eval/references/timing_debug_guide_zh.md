# Timing 排查

完整评测输出 `timing/timing_summary.rpt`、`timing/critical_path.rpt`、`timing/sta.log` 和 `timing/constraints.sdc`。

开发模式可以查询多条路径和指定端点：

```bash
python eval/run.py candidate.v --dev --stage timing --max-paths 5
python eval/run.py candidate.v --dev --stage timing --from 'A[15],B[15]' --to 'D[31]' --max-paths 3
```

指定查询额外写 `timing/query_paths.rpt`、`timing/query_summary.rpt` 和 `timing/query.log`。全设计测量仍先执行，筛选出的路径不会覆盖主指标。无需手动准备 SDC 或导出环境变量。

查看路径时区分输入外部延迟、cell 延迟和 data arrival time。`arrival_time_ns` 包含输入 delay；默认无提取寄生，报告不能解释为 post-route 性能。比较不同候选时固定配置与工具版本。
