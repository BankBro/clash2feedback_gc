# Clash2Feedback-GC 阶段 2 收尾关闭摘要

## 1. 验收结论

阶段 2 已完成 `ClashRepairBench-RG-artificial` controlled synthetic failed pose benchmark 构建。当前结果满足阶段 2 自动验收条件, 可正式作为阶段 3 rule locator / verifier preflight 的输入。

核心结果:

- base clean samples: 51 / 51.
- total injection attempts: 2610.
- supported_single_rgroup 主负样本: 357.
- manifest: 2610 rows x 70 columns.
- phase2_acceptance_status: complete.

## 2. 主集用途

阶段 3 的 Top-1 / Top-3 主指标只应使用:

```text
oracle_split == supported_single_rgroup
```

当前 supported 主集通过以下 gates:

- `ligand_valid = true`.
- `ligand_internal_severe_clash_count = 0`.
- `target_num_severe_pairs >= 1`.
- `non_target_num_severe_pairs = 0`.
- `scaffold_num_severe_pairs = 0`.
- `target_score_ratio_valid >= 0.7`.
- `max_clash_depth <= 1.5 Å`.
- `base_split == derived_split`.

## 3. 边界和限制

阶段 2 只证明 controlled artificial single-Rgroup clash 子任务的数据构造已经完成。它不能证明真实生成模型 failures 已被覆盖, 也不能证明 repair 方法有效。

`directed_clash` 是 protein-guided 合法旋转角度选择, 用于富集受控局部 steric conflict。它是 diagnostic stress test, 不应解释为生成模型真实采样分布。

## 4. Visual QC 状态

自动结构 gates 已完成, `visual_qc_cases.csv` 和 `visual_qc_notes.md` 已更新为 `sampled_visual_qc_passed_with_minor_caveats`。当前清单为 32 个 case, 其中 supported visual QC 已覆盖 `easy_rotation`, `torsion_perturb`, `directed_clash` 三种注入方式。ChimeraX contact sheets 已生成到 `runs/phase2_visual_qc/case_*/images/`, 并按 oracle split 和 injection mode 建立软链接索引。用户人工粗看和 4 个只读子 agent 独立复核均未发现阻断问题, 因此 `visual_qc_manual_review` 标记为 done_with_minor_caveats。

保留 minor caveats: invalid_conformer 当前没有 ligand internal self-clash 专用高亮视图; invalid 抽样有两组视觉重复; ambiguous_region 部分 surface 视图信息量有限; near_miss_contact 没有 severe VDW pair, `clash_pair_vdw` 为背景-only。这些 caveat 不影响 supported 主集质量判断。

## 5. Energy Delta 口径

`energy_delta` 在 phase2_v0_1 中是 record-only ligand-only diagnostic, 不是 hard acceptance filter。supported cases 通过 sanitize, bond, anchor, chirality, internal-clash 和 protein-ligand gates, 但没有使用 strict energy-delta gate 筛除。

新增报告:

- `reports/phase2_injection/energy_delta_stats.csv`.
- `reports/phase2_injection/energy_delta_outliers.csv`.

## 6. 阶段 3 最小启动建议

阶段 3 可以从以下输入开始:

- `reports/phase2_injection/supported_single_rgroup_cases.csv`.
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet`.

最小指标:

- Coverage.
- Top-1.
- Top-1 covered.
- Top-3 rank.
- Top-3 operational.
- mode-wise performance: `easy_rotation`, `torsion_perturb`, `directed_clash`.
- difficulty-wise performance.
- split-wise performance.

reject / unsupported / near_miss / duplicate 不混入 Top-1 / Top-3 主分母, 只做分流分析。

## 7. 阶段 2.5 边界

阶段 2.5 external validity audit 后续单独处理。本次收尾未实现阶段 2.5, 未调用生成器, 未做 repair, 未训练模型, 未修改 phase2 benchmark 核心定义。

## 8. 最终验证

本次收尾后已重新运行阶段 2 脚本并完成验证:

- phase2 rerun: 2610 attempts, 357 supported.
- `compileall`: pass.
- `pytest`: 78 passed.
- `delta_sensitivity.csv`: 无空表头.
- `energy_delta_stats.csv` 和 `energy_delta_outliers.csv`: 已生成.
- `visual_qc_manual_review`: done_with_minor_caveats, 32 个抽样 case 的 contact sheets 已完成用户人工粗看和 4 个只读子 agent 复核.
