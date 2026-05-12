# Clash2Feedback-GC 阶段 2.5 最终实验报告: Frozen DiffSBDD 模型诱导失败审计

## 1. Executive Summary

阶段 2.5 的定位是 `model-induced failure audit`, 不是 repair 实验, 不是模型训练, 不是 baseline ranking, 也不是阶段 3 定位准确率主评估. 本阶段使用 frozen DiffSBDD baseline 在经过 training-overlap audit 的 clean base pockets 上生成候选分子, 记录 all generated samples, 并对 generated ligands 做 ligand validity, protein-ligand clash, R-group attribution, failure taxonomy, repairability proxy 和 artificial-vs-model-induced gap analysis.

本轮实验完成了 DiffSBDD 外部仓库, checkpoint, 独立 `diffsbdd` 环境和 GPU 推理检查, 并实际生成 `10 pockets x 20 candidates = 200 unique candidates`. 每个 candidate 记录 `raw_generated` 和 `standardized_generated` 两个审计阶段, 因此 `generation_manifest.parquet`, `failure_taxonomy.csv`, `ligand_validity.csv` 和 `repairability_proxy.csv` 均为 `400 audit rows`. 这 400 行不是 400 个独立分子; 论文和实验解释应以 `200 unique candidates` 为主口径.

核心结论是: 在本轮 frozen DiffSBDD de novo complete-ligand audit 中, `single_rgroup_clash` 只出现 `1 / 200 = 0.5%` unique candidates, 不是主导失败类型. 主要分布是 `ligand_only_invalid` 80 个, `valid_no_severe_clash` 73 个, `near_miss_contact` 31 个, `global_pose_failure` 8 个, `scaffold_clash` 6 个, `rgroup_unattributable` 1 个, `single_rgroup_clash` 1 个.

这不要求立即放弃 Clash2Feedback-GC 的 R-group local repair 主线, 但要求收窄论文 claim: 阶段 2 artificial `supported_single_rgroup` benchmark 应被表述为可控局部修复测试床, 不应被表述为全部 DiffSBDD de novo model-induced failure distribution 的代表样本. 当前最合理顺序是先归档并提交阶段 2.5 最终报告, 再开展阶段 4 最小修复闭环实验.

## 2. Experiment Goal and Boundary

阶段 2.5 目标是审计 frozen generation baseline 诱导出的真实候选分子失败分布, 用于回答一个外部有效性问题: 阶段 2 artificial single-Rgroup clash benchmark 与真实 model-induced failures 的关系是什么.

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

## 3. Baseline and Reproducibility

本轮 baseline 和复现信息来自 `configs/phase2_5_model_induced_audit.yaml`, `docs/external_baselines.md`, `reports/phase2_5_model_induced_audit/external_setup.json` 和 `summary.json`.

| item | value |
|---|---|
| Baseline model | DiffSBDD |
| Mode | frozen inference only |
| External repo | `https://github.com/arneschneuing/DiffSBDD.git` |
| Pinned commit | `5d0d38d16c8932a0339fd2ce3f67ade98bbdff27` |
| Local source path | `external/DiffSBDD/` |
| Primary entrypoint | `external/DiffSBDD/generate_ligands.py` |
| Checkpoint | `crossdocked_fullatom_cond.ckpt` |
| Checkpoint MD5 | `166b0c056b31ffdf31d489a63e91e05b` |
| Checkpoint SHA256 | `07f86764bf569aafbc40a9c15fc02de8e2550437dd0f17f657eab3abe66c372c` |
| Checkpoint size | `17861341` bytes |
| Main control env | `c2f_cpu` |
| DiffSBDD env | `diffsbdd` |
| CUDA available in DiffSBDD env | `true` |
| GPU info | 2 x NVIDIA GeForce RTX 2080 Ti |

DiffSBDD core model samples ligand atom types and 3D coordinates conditioned on a protein pocket. DiffSBDD then builds RDKit molecules and writes SDF files. Phase 2.5 consumes the final SDF files written by DiffSBDD, not the internal point-cloud tensors.

## 4. Training-Overlap Audit

Training-overlap audit was completed before generation. The audit covered 51 local processed pockets.

| metric | value |
|---|---:|
| Pockets audited | 51 |
| `T_unknown` pockets | 51 |
| External-validity eligible under current rules | 51 |
| Same-source debug subset | 0 |
| Official split available | `false` |

The official DiffSBDD / Pocket2Mol split files were unavailable. As a result, every audited pocket was assigned to `T_unknown`. This means the current audit must be interpreted as a frozen DiffSBDD model-induced failure audit under unknown training-overlap status. It must not be described as strict external-unseen evaluation.

The blocked reason recorded in `summary.json` and `phase2_5_completion_audit.md` is:

```text
official_diffsbdd_or_pocket2mol_split_unavailable
```

## 5. Base Pocket Selection

The generation subset selected 10 base pockets from `base_pocket_selection.csv`. The selected pockets all had `overlap_tier=T_unknown` and were selected from local `val` and `test` splits.

| selected base pockets | value |
|---|---:|
| Total selected pockets | 10 |
| Selected `val` pockets | 3 |
| Selected `test` pockets | 7 |
| Selected `T_unknown` pockets | 10 |

Selected pockets:

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

Because all selected pockets are `T_unknown`, the selected set is useful for frozen model-induced audit, but not sufficient for strict external-unseen claims.

## 6. Generation and Audit Stages

Generation scale:

```text
10 selected pockets x 20 candidates per pocket = 200 unique candidates
```

Audit stages:

```text
raw_generated
standardized_generated
```

The `standardized_generated` stage is an audit-stage view of the same generated molecule, not a second independent generated molecule. In this project implementation, it copies the RDKit molecule and, if multiple fragments exist, keeps the largest heavy-atom fragment. This is not repair, not relaxation, not redocking, and not complex minimization.

Observed audit table sizes:

| table | rows | unique candidate_id | notes |
|---|---:|---:|---|
| `generation_manifest.parquet` | 400 | 200 | 200 raw + 200 standardized |
| `failure_taxonomy.csv` | 400 | 200 | one taxonomy row per candidate per stage |
| `ligand_validity.csv` | 400 | 200 | one validity row per candidate per stage |
| `repairability_proxy.csv` | 400 | 200 | one proxy row per candidate per stage |
| `model_induced_clash_report.csv` | 240 | 120 | valid ligand rows only, raw + standardized |

Raw vs standardized consistency:

| check | value |
|---|---:|
| Paired unique candidates | 200 |
| Taxonomy changed after standardization | 0 |
| Ligand validity changed after standardization | 0 |
| Raw `num_fragments=1` candidates | 200 |
| Standardized `num_fragments=1` candidates | 200 |

Therefore, downstream biological and experimental interpretation should use the 200-candidate unique view. The 400-row view is useful for checking audit completeness and stage consistency.

## 7. Unique-Candidate Failure Taxonomy

The unique-candidate taxonomy below is computed by taking the `raw_generated` row for each `candidate_id` from `failure_taxonomy.csv`. This is valid here because raw and standardized taxonomy labels are identical for all 200 candidates.

| failure_taxonomy | unique count | ratio |
|---|---:|---:|
| `ligand_only_invalid` | 80 | 40.0% |
| `valid_no_severe_clash` | 73 | 36.5% |
| `near_miss_contact` | 31 | 15.5% |
| `global_pose_failure` | 8 | 4.0% |
| `scaffold_clash` | 6 | 3.0% |
| `rgroup_unattributable` | 1 | 0.5% |
| `single_rgroup_clash` | 1 | 0.5% |

Audit-row taxonomy counts from `summary.json` are exactly doubled for stage-invariant labels because each candidate appears once in `raw_generated` and once in `standardized_generated`.

| audit-row metric | value |
|---|---:|
| `num_single_rgroup_clash` | 2 |
| `num_scaffold_clash` | 12 |
| `num_global_pose_failure` | 16 |
| `num_near_miss_contact` | 62 |
| `num_with_severe_clash` | 30 |

The most important result is that local single-Rgroup severe clash is very rare in this DiffSBDD de novo audit: only 1 out of 200 unique candidates. The single case is `complex_crossdocked_000007__cand_0015`, with dominant predicted R-group `R2`, `num_severe_clash_pairs=1`, and `max_clash_depth=0.40536`. Its `repairability_proxy` is still `reject`, so this audit does not establish a reliable model-induced local repair subset.

## 8. Ligand Validity and Clash Results

Unique ligand validity is computed from `ligand_validity.csv` using the `raw_generated` row per candidate.

| ligand validity | unique count | ratio |
|---|---:|---:|
| valid | 120 | 60.0% |
| invalid | 80 | 40.0% |

Invalidity reasons in the raw unique view:

| ligand_validity_reason | unique count |
|---|---:|
| `ligand_internal_severe_clash` | 73 |
| `rdkit_sanitize_failed` | 3 |
| `heavy_atom_count_out_of_range` | 3 |
| `rdkit_sanitize_failed;ligand_internal_severe_clash` | 1 |

Clash reports were generated only for ligand-valid candidates, producing 120 unique candidates and 240 audit rows across raw and standardized stages. In the 200 unique-candidate taxonomy, severe protein-ligand clash categories comprise 15 candidates: 1 `single_rgroup_clash`, 6 `scaffold_clash`, and 8 `global_pose_failure`.

Repairability proxy in the raw unique view:

| repairability_proxy | unique count |
|---|---:|
| `reject` | 111 |
| `invalid_unrepairable` | 80 |
| `global_repose_needed` | 8 |
| `unsupported` | 1 |
| `local_rgroup_repair_possible` | 0 |

The `phase2_coverage_proxy` in `summary.json` is `0.0`, consistent with the absence of `local_rgroup_repair_possible` rows.

## 9. Artificial vs Model-Induced Gap

The gap analysis compares the controlled Phase 2 artificial supported-single-Rgroup benchmark with the Phase 2.5 model-induced audit.

From `artificial_vs_model_induced_gap.csv`, Phase 2 has 357 `phase2_supported_single_rgroup` cases in the reported numeric comparisons. These artificial cases are clean, controlled, have an oracle target R-group, and are suitable for local repair and localization evaluation.

The model-induced side contains only 1 unique `single_rgroup_clash` candidate, represented as 2 audit rows. Therefore, Phase 2 artificial supported-single-Rgroup cases should be interpreted as a controlled local-repair testbed, not as a representative sample of all DiffSBDD de novo failures.

The correct interpretation is:

- Phase 2 artificial benchmark is still valuable because it gives a clean, controllable, oracle-labeled local repair problem.
- Phase 2.5 shows that this problem is a rare subdistribution in the current DiffSBDD de novo complete-ligand audit.
- The project should not claim that true DiffSBDD de novo failures are mainly R-group clashes.
- The project can claim that it targets a classic, verification-friendly local steric clash subtype in scaffold-preserving local editing.

## 10. Interpretation Caveats

### 10.1 Unknown Training-Overlap Status

Because official DiffSBDD / Pocket2Mol split files were unavailable, all audited pockets are `T_unknown`. The audit is valid as a frozen model-induced failure audit, but not as strict external-unseen evaluation.

### 10.2 200 Unique Candidates vs 400 Audit Rows

The 400 audit rows are generated by two postprocess-stage records per candidate:

```text
200 raw_generated rows + 200 standardized_generated rows = 400 audit rows
```

They should not be interpreted as 400 independent generated molecules. Unique-candidate statistics in this report use one row per `candidate_id`, using `raw_generated` as the representative row because raw and standardized labels are identical in this run.

### 10.3 `global_pose_failure` Is Coarse

The current `global_pose_failure` label is a coarse global-like / non-local severe failure bin. It is assigned when severe clashes are too deep or too numerous, or when a severe clash pattern does not safely satisfy clean local R-group or scaffold attribution criteria. In this run, all 8 unique `global_pose_failure` candidates have taxonomy reason `global_pose_threshold_exceeded`.

This label must not be directly interpreted as definitive evidence that the entire ligand pose is globally misplaced. It may include deep local clashes, dense severe contact patterns, distributed multi-region failures, scaffold-near failures, attribution uncertainty, or true global placement errors. A finer subtype analysis would need additional geometry features and visual QC.

Recommended future subtypes:

- `deep_local_clash`
- `dense_clash_failure`
- `distributed_pose_failure`
- `attribution_failed_with_severe_clash`
- `out_of_pocket_failure`
- `possible_coordinate_or_scope_issue`

### 10.4 Predicted Dominant R-Group Is Not Oracle

Generated ligands do not have an oracle `target_rgroup`. The `dominant_valid_rgroup` field is an attribution output for taxonomy and proxy analysis only. It must not be treated as ground-truth target R-group, and it must not be used as a Stage 3 Top-1 / Top-3 oracle label.

### 10.5 Visual QC Is Pending

`visual_qc_notes.md` records `pending_manual_review`. The automatic taxonomy has not been manually confirmed by visual inspection. The final report should not state that visual QC has passed.

## 11. Implications for Research Direction

The research topic does not need to be abandoned immediately. However, the claim must be narrowed.

The broad claim to avoid is:

```text
True de novo SBDD generation failures are mainly R-group clashes, and Phase 2 artificial R-group clashes represent the full model-induced failure distribution.
```

The defensible claim is:

```text
Clash2Feedback-GC studies a classic, controllable, and verification-friendly local steric clash subtype in scaffold-preserving local editing: protein-ligand clashes localized to R-group regions.
```

Phase 2.5 strengthens the project by clarifying the boundary: the Phase 2 artificial benchmark is not a proxy for all generated failures, but it remains a suitable testbed for evaluating whether structured clash feedback can guide local repair under reliable geometric criteria.

## 12. Recommended Next Step: Phase 4 Minimal Repair Loop

The current order should be:

1. Complete and submit this Phase 2.5 final report.
2. Push the report to the remote branch.
3. Then start Phase 4 minimal repair-loop experiments.

Phase 4 should not be started as part of this report task.

Recommended Phase 4 direction:

- Use Phase 2 `supported_single_rgroup` cases as the controlled repair benchmark.
- Compare random-mask repair, predicted-mask repair, and oracle/reference-mask repair.
- Evaluate reliable repair yield, old-clash resolution, no-new-clash rate, scaffold RMSD, non-mask RMSD, and ligand validity.
- Keep model-induced Phase 2.5 samples outside Stage 3 localization denominators unless a separate model-induced benchmark is formally defined.

## 13. Paper-Writable Claims

The following claims are supported by the current repository results:

- A frozen DiffSBDD baseline was successfully audited under a no-training, no-repair, no-ranking setting.
- Training-overlap audit was performed before generation, and all generated samples were recorded.
- The run generated 200 unique candidates from 10 selected pockets, with two audit stages per candidate.
- Raw and standardized stages did not change validity or taxonomy labels in this run.
- Under current unknown-overlap status, `single_rgroup_clash` was rare in the DiffSBDD de novo audit: 1 out of 200 unique candidates.
- Phase 2 artificial supported-single-Rgroup cases are best interpreted as a controlled local-repair testbed.
- The paper claim should focus on reliable local repair of a classic R-group-localized steric clash subtype, not on covering all de novo generation failures.

## 14. Conservative or Forbidden Claims

The following claims should not be made:

- This is a strict external-unseen evaluation.
- DiffSBDD real de novo generation failures are mainly R-group clashes.
- Phase 2.5 proves any repair method works.
- 400 audit rows are 400 independent generated molecules.
- Predicted dominant R-group is oracle ground truth.
- `global_pose_failure` definitively means the entire ligand pose is globally misplaced.
- Model-induced samples can be directly mixed into Stage 3 Top-1 / Top-3 main evaluation.
- Phase 2 artificial benchmark represents the full model-induced failure distribution.
- This run can be used for baseline ranking against other generators.

## 15. Verification and Files

Primary report files used:

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

Completion audit records:

```text
compileall: passed: conda run -n c2f_cpu python -m compileall src scripts
pytest: passed: 112 tests in 6.24s
```

Sanity checks used for this final report:

- `failure_taxonomy.csv` covers 400 audit rows and 200 unique candidates.
- `generation_manifest.parquet` contains 200 `raw_generated` rows and 200 `standardized_generated` rows.
- Raw vs standardized taxonomy changes: 0 / 200.
- Raw vs standardized ligand-validity changes: 0 / 200.
- `training_overlap_summary.json` records `official_split_available=false`.
- `visual_qc_notes.md` remains `pending_manual_review`.
- No-oracle-leakage is covered by `tests/test_phase2_5_no_oracle_leakage.py`.

