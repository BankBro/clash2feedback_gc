# 阶段 3 最终实验报告

## 1. 报告定位

本报告汇总 Clash2Feedback-GC 阶段 3 的真实仓库结果. 阶段 3 的当前口径是:

```text
label provenance audit
+ circularity risk audit
+ construction consistency check
+ phase4 mask seed generation
```

阶段 3 不是 independent locator benchmark. 它不训练模型, 不调用生成器, 不修复分子, 不生成 repaired ligand, 不计算 repair yield. 阶段 3 的核心交付物是 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`, 用于为阶段 4 准备可追溯的 oracle / predicted / random 三类掩码和旧碰撞证据.

本报告基于以下本地核查状态生成:

- 分支: `20260513-160230-phase3-implementation`
- 报告生成前 commit: `6c6ec3e0773e0eb1bac684e5baa558acb704b667`
- 阶段 3 配置: `configs/phase3_label_provenance_audit.yaml`
- 阶段 3 入口: `scripts/phase3_label_provenance_audit.py`
- 阶段 3 输出目录: `reports/phase3_label_provenance_audit/`

## 2. 输入与输出

阶段 3 读取阶段 2 人工扰动 benchmark, 阶段 2 报告, processed base samples 和阶段 2.5 审计报告. 阶段 3 不回写阶段 2 / 阶段 2.5 历史结果, 不修改 benchmark 数据.

主要输出文件包括:

- `summary.json`
- `phase2_label_provenance_audit.md`
- `circularity_risk_audit.md`
- `field_dependency_table.csv`
- `set_definition_report.csv`
- `construction_consistency_report.csv`
- `locator_stress_report_s0.csv`
- `locator_stress_report_s1.csv`
- `phase4_mask_seed.csv`
- `random_mask_balance_summary.csv`
- `phase3_completion_audit.md`

其中 `random_mask_balance_summary.csv` 是收尾核查派生统计, 仅用于说明 random mask 与 oracle/predicted mask 的大小差异, 不回写阶段 3 核心结果.

## 3. 阶段目标与边界

阶段 3 要解决的问题是:

- 审计 phase2 标签从哪里来.
- 审计 `target_rgroup`, `target_score_ratio_valid`, `predicted_dominant_valid_rgroup`, `supported_single_rgroup` 之间的依赖关系.
- 明确 `supported_single_rgroup` 的循环验证风险.
- 在 S2 主集上报告 construction consistency.
- 为阶段 4 生成 oracle / predicted / random 三类 mask seed.

阶段 3 不承担以下职责:

- 不证明定位器无偏准确率.
- 不把 Top-1 / Top-3 写成 independent localization accuracy.
- 不把 `target_rgroup` 写成无偏定位真值.
- 不把 predicted mask 写成 ground truth.
- 不把 `supported_single_rgroup` 写成无偏 benchmark.
- 不证明修复后端可用.
- 不证明 Clash2Feedback-GC 能修复分子.

## 4. S0 / S1 / S2 集合

阶段 3 定义了三套集合:

| 集合 | 数量 | 定义 | 阶段 4 角色 | construction consistency 分母 |
|---|---:|---|---|---|
| S0_all_valid_injection_attempts | 1185 | ligand valid, ligand internal severe clash 为 0, oracle split 不属于 unsupported / invalid_conformer / duplicate_removed | auxiliary audit only | 否 |
| S1_oracle_target_local_clash_set | 467 | valid ligand, target severe clash >= 1, scaffold 和 non-target severe clash 为 0, max clash depth <= 1.5, 不使用 `target_score_ratio_valid` gate | auxiliary stress analysis only | 否 |
| S2_phase2_supported_single_rgroup | 357 | `oracle_split == supported_single_rgroup` | 阶段 4 主输入 | 是 |

S2 是 detector / attribution / target-dominance gates 过滤后的 clean local repair substrate. 因为 S2 已使用 attribution-derived gate, 其 circularity risk level 记为 high. S0 / S1 只用于辅助审计和压力分析, 不作为阶段 4 主输入.

## 5. 字段溯源

关键字段的解释如下:

| 字段或产物 | 来源 | 阶段 3 解释 |
|---|---|---|
| `target_rgroup` | phase2 人工扰动流程 | 人工扰动标签和 oracle mask 来源, 不是无偏定位真值 |
| `target_atom_indices` | phase2 manifest 与 processed base sample 交叉核查 | oracle/reference edit mask atoms |
| `anchor_scaffold_atom_idx` | phase2 manifest 与 processed base sample | anchor 单独记录, 不默认加入自由编辑掩码 |
| `anchor_rgroup_atom_idx` | phase2 manifest 与 processed base sample | anchor 单独记录 |
| `anchor_bond_idx` | phase2 manifest 与 processed base sample | anchor bond 单独记录 |
| `predicted_dominant_valid_rgroup` | `attribute_clashes_to_rgroups().dominant_valid_rgroup` | attribution-derived operational mask policy, 不是 ground truth, 也不是 phase2 acceptance gate |
| `target_score_ratio_valid` | attribution-derived valid R-group scores | 参与 `supported_single_rgroup` gate |
| `supported_single_rgroup` | `assign_oracle_split()` | clean local repair substrate, 不是无偏定位 benchmark |
| phase2.5 model-induced rows | `reports/phase2_5_model_induced_audit/failure_taxonomy.csv` | 没有人工 `target_rgroup`, 不进入 construction consistency denominator |
| `phase4_mask_seed.csv` | 阶段 3 mask seed 生成逻辑 | 阶段 4.0 / 4.1 输入 |

因此, `target_rgroup` 可以作为阶段 4 oracle mask 来源, 但不能被写成 unbiased locator ground truth. `predicted_dominant_valid_rgroup` 可以作为自动掩码策略输出, 但不能被写成 ground truth.

## 6. 循环验证风险

阶段 3 的主要循环风险来自 S2:

```text
人工扰动 target_rgroup
-> detector 识别 protein-ligand clash
-> attribution 将 clash evidence 归因到 R-group
-> target_score_ratio_valid 参与 supported_single_rgroup gate
-> 阶段 3 再用同一 attribution-derived policy 检查 predicted 与 target 是否一致
```

因此, S2 上的 Top-1 / Top-3 只能解释为 construction consistency check. 它说明人工扰动标签, attribution 记录和阶段 4 掩码构造在 clean local repair substrate 内部一致, 不说明定位器在无偏样本上的独立准确率.

S1 不使用 `target_score_ratio_valid >= 0.7` gate, 可以弱化 target-dominance gate 带来的循环风险, 但仍依赖 detector 的 region-level pair 统计, 因而也不是完全无循环验证的定位 benchmark.

## 7. Construction Consistency 结果

`construction_consistency_report.csv` 使用 S2 作为唯一分母:

| 指标 | 分子 | 分母 | 数值 | 解释 |
|---|---:|---:|---:|---|
| Top-1 predicted equals oracle | 357 | 357 | 1.0 | 只检查 clean local repair substrate 上 predicted mask policy 与人工扰动目标的一致性 |
| Top-3 target in top valid R-groups | 357 | 357 | 1.0 | 只检查 attribution construction 是否把人工 target 排进 top valid R-groups |

两项指标均标记为 `not_independent_locator_benchmark=True`.

该结果可以写成:

```text
S2 clean local repair substrate 上, attribution-derived predicted mask policy 与人工扰动参考区域完全一致.
```

不能写成:

```text
规则定位器在 357 个样本上取得 100% 独立定位准确率.
```

## 8. Phase 4 Mask Seed

`phase4_mask_seed.csv` 共有 357 行, 全部来自 S2. 每行包含:

- 基础 case 信息和 split 信息.
- `target_rgroup`, `target_atom_indices`, `predicted_dominant_valid_rgroup`, `top_valid_rgroups_json`.
- oracle / predicted / random 三类 edit mask.
- oracle / predicted / random 三类 keep mask.
- 三类 mask 的 anchor scaffold atom, anchor R-group atom 和 anchor bond.
- old clash pairs.
- protein clash hot atoms 和 hot residues.
- target / non-target / scaffold severe clash 计数.
- `phase4_0_backend_feasibility_candidate`.
- `phase4_1_formal_loop_candidate`.

可用性统计:

| 项目 | 数量 |
|---|---:|
| `phase4_mask_seed.csv` rows | 357 |
| oracle / predicted / random masks 均可用 | 357 |
| `phase4_0_backend_feasibility_candidate=True` | 357 |
| `phase4_1_formal_loop_candidate=True` | 357 |
| `predicted_equals_oracle=True` | 357 |
| `random_equals_oracle=True` | 0 |
| `random_equals_predicted=True` | 0 |
| `circularity_risk_level=high` | 357 |

Mask 口径:

- oracle mask = `target_rgroup` 对应的整个 R 基原子集合.
- predicted mask = `predicted_dominant_valid_rgroup` 对应的整个 R 基原子集合, 是 attribution-derived operational policy.
- random mask = 同一配体中排除 oracle/predicted 后的 size-matched 或 nearest-size 合法 single-anchor R 基.
- edit mask = 整个 R 基.
- keep mask = 配体中除 edit mask 外的所有原子.
- anchor 单独记录, 不默认加入自由编辑掩码.

`phase4_mask_seed.csv` 足以支持阶段 4.0 Oracle mask backend feasibility audit 和阶段 4.1 Random / Predicted / Oracle formal repair loop.

## 9. Random Mask Size Matching

`random_mask_balance_summary.csv` 记录了 357 个 S2 case 的 random mask size balance:

| 统计项 | 结果 |
|---|---:|
| rows | 357 |
| `random_mask_fallback_reason=primary_exclude_oracle_and_predicted` | 357 |
| mean abs size diff random vs oracle | 1.456583 |
| mean abs size diff random vs predicted | 1.456583 |
| max abs size diff random vs oracle | 3 |
| max abs size diff random vs predicted | 3 |

大小差异分布:

| abs size diff | random vs oracle | random vs predicted |
|---:|---:|---:|
| 0 | 127 | 127 |
| 1 | 26 | 26 |
| 2 | 118 | 118 |
| 3 | 86 | 86 |

结论: random mask 没有复用 oracle 或 predicted, 但不是所有 case 都能精确等大小. 当前 random mask 应解释为同配体内排除 oracle/predicted 后的 size-matched 或 nearest-size 合法 R 基 baseline. 这不阻断阶段 4.0, 但阶段 4.1 结果解释时应记录 size diff, 必要时按 `abs_size_diff_random_vs_oracle` 做敏感性分析.

## 10. 能支持的结论

阶段 3 结果支持以下结论:

- 阶段 3 已完成 phase2 标签溯源审计, 循环验证风险审计, construction consistency check 和 phase4 mask seed generation.
- S2 主集共有 357 个 clean local repair substrate case, 全部可以进入阶段 4.0 和阶段 4.1 候选.
- S2 上 predicted mask 与 oracle mask 完全一致, 说明该 clean substrate 中 attribution-derived mask policy 与人工扰动参考区域一致.
- random mask 没有退化成 oracle 或 predicted 复用.
- phase2.5 model-induced rows 没有人工 `target_rgroup`, 当前没有进入 construction consistency denominator.
- `phase4_mask_seed.csv` 已经提供阶段 4 所需的 edit mask, keep mask, anchor, old clash evidence 和 protein hot region.

## 11. 不能支持的结论

阶段 3 结果不能支持以下结论:

- 不能证明定位器的 independent localization accuracy.
- 不能把 Top-1 / Top-3 = 1.0 写成无偏定位准确率 100%.
- 不能把 `target_rgroup` 写成无偏 locator ground truth.
- 不能把 predicted mask 写成真实失败区域或 ground truth.
- 不能把 `supported_single_rgroup` 写成无偏 benchmark.
- 不能说明修复后端已经可用.
- 不能说明模型已经能修复分子.
- 不能从 S2 的 predicted=oracle 推出阶段 4.1 必然存在 Predicted 优于 Oracle 的差异.

## 12. 阶段 4.0 建议

建议进入阶段 4.0. 阶段 4.0 应优先做 Oracle mask backend feasibility audit, 目标是回答:

```text
当给定正确修复区域时, repair backend 是否能稳定修复.
```

最小执行顺序:

1. 读取 `phase4_mask_seed.csv`, 做字段 sanity check.
2. 先抽取 20-50 个 S2 case, 不建议首轮直接跑全量 357.
3. 使用 oracle mask 运行 backend feasibility audit.
4. 至少记录 candidate generation success, ligand validity, anchor consistency, old clash resolved, no new severe clash, scaffold RMSD, non-mask RMSD.
5. 如果 Oracle mask 下后端可行, 再进入阶段 4.1 Random / Predicted / Oracle formal repair loop.
6. 如果 Oracle mask 都修不好, 优先修 repair backend, 不应把失败归因到 mask policy.

阶段 4.1 中, 当前 S2 上 `predicted_equals_oracle=357/357`, 因此核心比较应写成:

```text
Random vs Predicted/Oracle
```

不要强行写成:

```text
Random < Predicted < Oracle
```

当前数据不支持 Predicted 与 Oracle 在 S2 上产生 mask 差距.

## 13. 最终结论

阶段 3 通过, 建议进入阶段 4.0.

更准确的总结是:

```text
阶段 3 成功完成了 phase2 标签溯源、循环验证风险审计、construction consistency check 和阶段 4 掩码种子生成。S2 主集上 predicted mask 与 oracle mask 完全一致, 说明该 clean local repair substrate 与 attribution-derived mask policy 高度一致; 但该结果只能作为 construction consistency check, 不能解释为 independent locator accuracy。phase4_mask_seed.csv 已为 357 个 S2 case 提供 oracle / predicted / random 三类掩码、keep mask、anchor 和旧碰撞证据, 足以支持阶段 4.0 Oracle mask backend feasibility audit 和阶段 4.1 Random / Predicted / Oracle formal repair loop。阶段 4.1 应把核心比较写成 Random vs Predicted/Oracle, 并记录 random mask size diff 对结果解释的影响。
```
