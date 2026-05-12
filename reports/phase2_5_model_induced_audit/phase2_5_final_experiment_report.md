# Clash2Feedback-GC 阶段 2.5 最终实验报告: Frozen DiffSBDD 模型诱导失败审计

## 1. 执行摘要

阶段 2.5 的定位是 `model-induced failure audit`, 不是 repair 实验, 不是模型训练, 不是 baseline ranking, 也不是阶段 3 定位准确率主评估. 本阶段使用 frozen DiffSBDD baseline 在经过 training-overlap audit 的 clean base pockets 上生成候选分子, 记录 all generated samples, 并对 generated ligands 做 ligand validity, protein-ligand clash, R-group attribution, failure taxonomy, repairability proxy 和 artificial-vs-model-induced gap analysis.

本轮实验完成了 DiffSBDD 外部仓库, checkpoint, 独立 `diffsbdd` 环境和 GPU 推理检查, 并实际生成 `10 pockets x 20 candidates = 200 unique candidates`. 每个 candidate 记录 `raw_generated` 和 `standardized_generated` 两个审计阶段, 因此 `generation_manifest.parquet`, `failure_taxonomy.csv`, `ligand_validity.csv` 和 `repairability_proxy.csv` 均为 `400 audit rows`. 这 400 行不是 400 个独立分子; 论文和实验解释应以 `200 unique candidates` 为主口径.

核心结论是: 在本轮 frozen DiffSBDD de novo complete-ligand audit 中, `single_rgroup_clash` 只出现 `1 / 200 = 0.5%` unique candidates, 不是主导失败类型. 主要分布是 `ligand_only_invalid` 80 个, `valid_no_severe_clash` 73 个, `near_miss_contact` 31 个, `global_pose_failure` 8 个, `scaffold_clash` 6 个, `rgroup_unattributable` 1 个, `single_rgroup_clash` 1 个.

这不要求立即放弃 Clash2Feedback-GC 的 R-group local repair 主线, 但要求收窄论文 claim: 阶段 2 artificial `supported_single_rgroup` benchmark 应被表述为可控局部修复测试床, 不应被表述为全部 DiffSBDD de novo model-induced failure distribution 的代表样本. 当前最合理顺序是先归档并提交阶段 2.5 最终报告, 再开展阶段 4 最小修复闭环实验.

## 2. 实验目标与边界

阶段 2.5 的目标是审计 frozen generation baseline 诱导出的真实候选分子失败分布, 用于回答一个外部有效性问题: 阶段 2 artificial single-Rgroup clash benchmark 与真实 model-induced failures 的关系是什么.

本阶段明确遵守以下边界:

- 不训练模型.
- 不做 repair.
- 不调参.
- 不做 baseline ranking.
- 不回改 `phase2_v0_1`.
- 不把 model-induced samples 混入阶段 3 Top-1 / Top-3 主评估.
- 不把 predicted dominant R-group 当作 oracle ground truth.
- training-overlap audit 先于 generation audit.
- all generated samples 均记录到 manifest.

因此, 阶段 2.5 只能支持 failure taxonomy 和 distribution-gap 层面的结论, 不能作为 repair success evidence.

## 3. 基线模型与可复现信息

本轮 baseline 和复现信息来自 `configs/phase2_5_model_induced_audit.yaml`, `docs/external_baselines.md`, `reports/phase2_5_model_induced_audit/external_setup.json` 和 `summary.json`.

| 项目 | 取值 |
|---|---|
| Baseline model | DiffSBDD |
| 运行模式 | frozen inference only |
| 外部仓库 | `https://github.com/arneschneuing/DiffSBDD.git` |
| 固定 commit | `5d0d38d16c8932a0339fd2ce3f67ade98bbdff27` |
| 本地源码路径 | `external/DiffSBDD/` |
| 主要入口 | `external/DiffSBDD/generate_ligands.py` |
| Checkpoint | `crossdocked_fullatom_cond.ckpt` |
| Checkpoint MD5 | `166b0c056b31ffdf31d489a63e91e05b` |
| Checkpoint SHA256 | `07f86764bf569aafbc40a9c15fc02de8e2550437dd0f17f657eab3abe66c372c` |
| Checkpoint 文件大小 | `17861341` bytes |
| 主控环境 | `c2f_cpu` |
| DiffSBDD 环境 | `diffsbdd` |
| DiffSBDD 环境 CUDA 可用 | `true` |
| GPU 信息 | 2 x NVIDIA GeForce RTX 2080 Ti |

DiffSBDD 核心模型以蛋白口袋为条件采样 ligand atom types 和 3D coordinates. 随后 DiffSBDD 会构建 RDKit molecule 并写出 SDF 文件. 阶段 2.5 消费的是 DiffSBDD 写出的最终 SDF 文件, 不是模型内部的 point-cloud tensor.

## 4. 训练重叠审计

训练重叠审计已在 generation 前完成. 本轮审计覆盖 51 个本地 processed pockets.

| 指标 | 取值 |
|---|---:|
| 已审计 pockets | 51 |
| `T_unknown` pockets | 51 |
| 当前规则下 external-validity eligible | 51 |
| Same-source debug subset | 0 |
| Official split available | `false` |

官方 DiffSBDD / Pocket2Mol split 文件缺失. 因此, 所有已审计 pocket 均被标记为 `T_unknown`. 这意味着当前结果只能解释为 unknown training-overlap status 下的 frozen DiffSBDD model-induced failure audit, 不能解释为 strict external-unseen evaluation.

`summary.json` 和 `phase2_5_completion_audit.md` 记录的 blocked reason 为:

```text
official_diffsbdd_or_pocket2mol_split_unavailable
```

## 5. 基础 Pocket 选择

生成子集从 `base_pocket_selection.csv` 中选择了 10 个 base pockets. 这些 selected pockets 全部为 `overlap_tier=T_unknown`, 来源于本项目本地 `val` 和 `test` split.

| selected base pockets | 取值 |
|---|---:|
| selected pockets 总数 | 10 |
| selected `val` pockets | 3 |
| selected `test` pockets | 7 |
| selected `T_unknown` pockets | 10 |

Selected pockets 清单:

| base_sample_id | base_split | target_id |
|---|---|---|
| `complex_crossdocked_000026` | val | `RIP1_MOMCH_24_270_0` |
| `complex_crossdocked_000027` | val | `RIP1_MOMCH_24_270_0` |
| `complex_crossdocked_000028` | val | `RIP1_MOMCH_24_270_0` |
| `complex_crossdocked_000001` | test | `CDGT2_BACCI_28_713_0` |
| `complex_crossdocked_000002` | test | `CDGT2_BACCI_28_713_0` |
| `complex_crossdocked_000003` | test | `CDGT2_BACCI_28_713_0` |
| `complex_crossdocked_000004` | test | `CDGT2_BACCI_28_713_0` |
| `complex_crossdocked_000005` | test | `CDGT2_BACCI_28_713_0` |
| `complex_crossdocked_000006` | test | `CDGT2_BACCI_28_713_0` |
| `complex_crossdocked_000007` | test | `CDGT2_BACCI_28_713_0` |

因为所有 selected pockets 都是 `T_unknown`, 这组样本可以用于 frozen model-induced audit, 但不足以支持 strict external-unseen claim.

## 6. 生成规模与审计阶段

生成规模:

```text
10 selected pockets x 20 candidates per pocket = 200 unique candidates
```

审计阶段:

```text
raw_generated
standardized_generated
```

`standardized_generated` 是同一批 generated molecules 的审计阶段视图, 不是第二批独立生成分子. 在当前项目实现中, 它会复制 RDKit molecule, 如果出现 multiple fragments 则保留 heavy atoms 数最多的最大 fragment. 这不是 repair, 不是 relaxation, 不是 redocking, 也不是 complex minimization.

已观察到的审计表规模:

| 表 | rows | unique candidate_id | 说明 |
|---|---:|---:|---|
| `generation_manifest.parquet` | 400 | 200 | 200 raw + 200 standardized |
| `failure_taxonomy.csv` | 400 | 200 | 每个 candidate 每个 stage 一行 taxonomy |
| `ligand_validity.csv` | 400 | 200 | 每个 candidate 每个 stage 一行 validity |
| `repairability_proxy.csv` | 400 | 200 | 每个 candidate 每个 stage 一行 proxy |
| `model_induced_clash_report.csv` | 240 | 120 | 仅 ligand-valid rows, raw + standardized |

Raw 与 standardized 一致性:

| 检查项 | 取值 |
|---|---:|
| paired unique candidates | 200 |
| standardization 后 taxonomy 变化 | 0 |
| standardization 后 ligand validity 变化 | 0 |
| raw `num_fragments=1` candidates | 200 |
| standardized `num_fragments=1` candidates | 200 |

因此, 下游生物学解释和论文叙事应使用 200-candidate unique view. 400-row view 主要用于检查审计完整性和 stage 一致性.

## 7. Unique-Candidate 口径失败分类

下表的 unique-candidate taxonomy 由 `failure_taxonomy.csv` 中每个 `candidate_id` 的 `raw_generated` row 计算得到. 本轮 raw 和 standardized taxonomy labels 对全部 200 个 candidate 完全一致, 所以使用 raw row 作为 unique representative 是合理的.

| failure_taxonomy | unique count | ratio |
|---|---:|---:|
| `ligand_only_invalid` | 80 | 40.0% |
| `valid_no_severe_clash` | 73 | 36.5% |
| `near_miss_contact` | 31 | 15.5% |
| `global_pose_failure` | 8 | 4.0% |
| `scaffold_clash` | 6 | 3.0% |
| `rgroup_unattributable` | 1 | 0.5% |
| `single_rgroup_clash` | 1 | 0.5% |

`summary.json` 中的 audit-row taxonomy counts 因为每个 candidate 同时有 `raw_generated` 和 `standardized_generated` 两行, 所以对 stage-invariant labels 来说正好是 unique count 的两倍.

| audit-row metric | value |
|---|---:|
| `num_single_rgroup_clash` | 2 |
| `num_scaffold_clash` | 12 |
| `num_global_pose_failure` | 16 |
| `num_near_miss_contact` | 62 |
| `num_with_severe_clash` | 30 |

最重要的结果是: local single-Rgroup severe clash 在本轮 DiffSBDD de novo audit 中非常少, 只有 `1 / 200` unique candidates. 唯一 case 是 `complex_crossdocked_000007__cand_0015`, 其 dominant predicted R-group 为 `R2`, `num_severe_clash_pairs=1`, `max_clash_depth=0.40536`. 但它的 `repairability_proxy` 仍然是 `reject`, 因此本轮 audit 没有形成可靠的 model-induced local repair subset.

## 8. 配体有效性与 Clash 结果

Unique-candidate 口径的 ligand validity 由 `ligand_validity.csv` 中每个 candidate 的 `raw_generated` row 计算得到.

| ligand validity | unique count | ratio |
|---|---:|---:|
| valid | 120 | 60.0% |
| invalid | 80 | 40.0% |

Raw unique view 中的 invalidity reasons:

| ligand_validity_reason | unique count |
|---|---:|
| `ligand_internal_severe_clash` | 73 |
| `rdkit_sanitize_failed` | 3 |
| `heavy_atom_count_out_of_range` | 3 |
| `rdkit_sanitize_failed;ligand_internal_severe_clash` | 1 |

Clash 报告只对 ligand-valid candidates 生成, 因此覆盖 120 个 unique candidates, 对应 raw 和 standardized 两阶段共 240 audit rows. 在 200 unique-candidate taxonomy 中, severe protein-ligand clash categories 共 15 个 candidates: 1 个 `single_rgroup_clash`, 6 个 `scaffold_clash`, 8 个 `global_pose_failure`.

Raw unique view 中的 repairability proxy:

| repairability_proxy | unique count |
|---|---:|
| `reject` | 111 |
| `invalid_unrepairable` | 80 |
| `global_repose_needed` | 8 |
| `unsupported` | 1 |
| `local_rgroup_repair_possible` | 0 |

`summary.json` 中的 `phase2_coverage_proxy` 为 `0.0`, 与 `local_rgroup_repair_possible` rows 缺失一致.

## 9. Artificial 与 Model-Induced 分布差距

分布差距分析比较了受控的阶段 2 artificial supported-single-Rgroup benchmark 和阶段 2.5 model-induced audit.

根据 `artificial_vs_model_induced_gap.csv`, 阶段 2 在 numeric comparisons 中包含 357 个 `phase2_supported_single_rgroup` cases. 这些 artificial cases 是 clean, controlled, 有 oracle target R-group, 适合用于 local repair 和 localization evaluation.

Model-induced 侧只有 1 个 unique `single_rgroup_clash` candidate, 在 audit-row 口径中表现为 2 行. 因此, 阶段 2 artificial supported-single-Rgroup cases 应被解释为 controlled local-repair testbed, 而不是全部 DiffSBDD de novo failures 的代表样本.

正确解释是:

- 阶段 2 artificial benchmark 仍然有价值, 因为它提供 clean, controllable, oracle-labeled local repair problem.
- 阶段 2.5 表明, 该问题在当前 DiffSBDD de novo complete-ligand audit 中是稀有子分布.
- 项目不应声称真实 DiffSBDD de novo failures 主要是 R-group clashes.
- 项目可以声称自己研究 scaffold-preserving local editing 中一个经典, 可验证的 local steric clash subtype.

## 10. 解释限制

### 10.1 训练重叠状态未知

由于官方 DiffSBDD / Pocket2Mol split 文件缺失, 所有 audited pockets 均为 `T_unknown`. 本轮审计可以作为 frozen model-induced failure audit, 但不能作为 strict external-unseen evaluation.

### 10.2 200 Unique Candidates 与 400 Audit Rows

400 audit rows 来自每个 candidate 的两个 postprocess-stage records:

```text
200 raw_generated rows + 200 standardized_generated rows = 400 audit rows
```

这些 rows 不应解释为 400 个独立生成分子. 本报告的 unique-candidate statistics 使用每个 `candidate_id` 一行, 并使用 `raw_generated` 作为 representative row, 因为本轮 raw 与 standardized labels 完全一致.

### 10.3 `global_pose_failure` 是粗粒度标签

当前 `global_pose_failure` 是一个 coarse global-like / non-local severe failure bin. 当 severe clashes 过深, 过多, 或 severe clash pattern 不能安全满足 clean local R-group 或 scaffold attribution criteria 时, 样本会被归到这个类别. 本轮 8 个 unique `global_pose_failure` candidates 的 taxonomy reason 全部是 `global_pose_threshold_exceeded`.

这个标签不能直接解释为 ligand 整体 pose 一定放错. 它可能包含 deep local clashes, dense severe contact patterns, distributed multi-region failures, scaffold-near failures, attribution uncertainty, 或真正的 global placement errors. 若要进一步区分, 需要额外几何特征和 visual QC.

后续可以考虑新增更细的 subtypes:

- `deep_local_clash`
- `dense_clash_failure`
- `distributed_pose_failure`
- `attribution_failed_with_severe_clash`
- `out_of_pocket_failure`
- `possible_coordinate_or_scope_issue`

### 10.4 Predicted Dominant R-Group 不是 Oracle 标签

Generated ligands 没有 oracle `target_rgroup`. `dominant_valid_rgroup` 只是 attribution output, 只能用于 taxonomy 和 proxy analysis. 它不能被当作 ground-truth target R-group, 也不能用于阶段 3 Top-1 / Top-3 oracle label.

### 10.5 人工可视化 QC 仍为 Pending

`visual_qc_notes.md` 记录的是 `pending_manual_review`. 当前 automatic taxonomy 尚未通过人工 visual inspection 确认. 最终报告不能写成 visual QC 已经通过.

## 11. 对研究方向的影响

研究课题不需要立刻放弃. 但论文 claim 必须收窄.

应避免的宽泛 claim 是:

```text
真实 de novo SBDD generation failures 主要是 R-group clashes, 且阶段 2 artificial R-group clashes 能代表完整 model-induced failure distribution.
```

当前更稳妥的 claim 是:

```text
Clash2Feedback-GC 研究 scaffold-preserving local editing 中一个经典, 可控, 可验证的 local steric clash subtype: 定位到 R-group regions 的 protein-ligand clashes.
```

阶段 2.5 的价值在于澄清边界: 阶段 2 artificial benchmark 不是全部 generated failures 的 proxy, 但它仍然是评估 structured clash feedback 能否在 reliable geometric criteria 下指导 local repair 的合适测试床.

## 12. 建议下一步: 阶段 4 最小修复闭环

当前顺序应为:

1. 完成并提交阶段 2.5 最终报告.
2. 将报告推送到远端分支.
3. 再启动阶段 4 minimal repair-loop experiments.

阶段 4 不应作为本报告任务的一部分启动.

建议阶段 4 方向:

- 使用阶段 2 `supported_single_rgroup` cases 作为 controlled repair benchmark.
- 比较 random-mask repair, predicted-mask repair 和 oracle/reference-mask repair.
- 评估 reliable repair yield, old-clash resolution, no-new-clash rate, scaffold RMSD, non-mask RMSD 和 ligand validity.
- 除非另行正式定义 model-induced benchmark, 否则阶段 2.5 model-induced samples 不应进入阶段 3 localization denominators.

## 13. 可写入论文的结论

当前仓库结果支持以下结论:

- Frozen DiffSBDD baseline 已在 no-training, no-repair, no-ranking 设置下完成审计.
- Training-overlap audit 已在 generation 前执行, all generated samples 已记录.
- 本轮从 10 个 selected pockets 生成 200 个 unique candidates, 每个 candidate 有两个 audit stages.
- 本轮 raw 和 standardized stages 没有改变 validity 或 taxonomy labels.
- 在当前 unknown-overlap status 下, `single_rgroup_clash` 在 DiffSBDD de novo audit 中很少: 1 / 200 unique candidates.
- 阶段 2 artificial supported-single-Rgroup cases 更适合解释为 controlled local-repair testbed.
- 论文 claim 应聚焦 classic R-group-localized steric clash subtype 的 reliable local repair, 不应声称覆盖所有 de novo generation failures.

## 14. 必须保守或禁止的结论

以下结论不应写入论文或汇报:

- 本轮是 strict external-unseen evaluation.
- DiffSBDD real de novo generation failures 主要是 R-group clashes.
- 阶段 2.5 证明任何 repair 方法有效.
- 400 audit rows 等于 400 independent generated molecules.
- Predicted dominant R-group 是 oracle ground truth.
- `global_pose_failure` 一定表示 ligand 整体 pose 放错.
- Model-induced samples 可以直接混入阶段 3 Top-1 / Top-3 主评估.
- 阶段 2 artificial benchmark 代表完整 model-induced failure distribution.
- 本轮结果可用于与其他 generator 做 baseline ranking.

## 15. 验证与文件

本报告主要使用以下文件:

- `reports/phase2_5_model_induced_audit/summary.json`
- `reports/phase2_5_model_induced_audit/training_overlap_summary.json`
- `reports/phase2_5_model_induced_audit/base_pocket_selection.csv`
- `reports/phase2_5_model_induced_audit/generation_manifest.parquet`
- `reports/phase2_5_model_induced_audit/failure_taxonomy.csv`
- `reports/phase2_5_model_induced_audit/ligand_validity.csv`
- `reports/phase2_5_model_induced_audit/model_induced_clash_report.csv`
- `reports/phase2_5_model_induced_audit/repairability_proxy.csv`
- `reports/phase2_5_model_induced_audit/artificial_vs_model_induced_gap.csv`
- `reports/phase2_5_model_induced_audit/visual_qc_notes.md`
- `reports/phase2_5_model_induced_audit/phase2_5_completion_audit.md`

Completion audit 记录:

```text
compileall: passed: conda run -n c2f_cpu python -m compileall src scripts
pytest: passed: 112 tests in 6.24s
```

本最终报告使用的 sanity checks:

- `failure_taxonomy.csv` 覆盖 400 audit rows 和 200 unique candidates.
- `generation_manifest.parquet` 包含 200 `raw_generated` rows 和 200 `standardized_generated` rows.
- Raw vs standardized taxonomy changes: 0 / 200.
- Raw vs standardized ligand-validity changes: 0 / 200.
- `training_overlap_summary.json` 记录 `official_split_available=false`.
- `visual_qc_notes.md` 仍为 `pending_manual_review`.
- No-oracle-leakage 由 `tests/test_phase2_5_no_oracle_leakage.py` 覆盖.
