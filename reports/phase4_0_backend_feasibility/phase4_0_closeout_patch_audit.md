# Phase 4.0 Closeout Patch Audit

## 1. Repository Check

- pre-patch `git status --short`: `clean`.
- `git branch --show-current`: `20260514-043614-phase4-0`.
- `git rev-parse HEAD`: `60e2011ff0a6c405c9d3c20a772859ae1e72060a`.

## 2. Closeout Scope

- 阶段 4.0 主实验是否完成: 是.
- 是否需要重跑 40 case: 否.
- 是否需要补跑主后端: 否.
- DiffSBDD joint blocked 是否影响最终报告: 否, 它是 backend feasibility audit 的真实结论.
- 是否需要生成式后端继续修补: 是, 作为后续阶段.
- 是否可以进入 `phase4_0_final_experiment_report.md` 生成: yes.

## 3. Reliable Repair Candidate Definition

可靠修复候选必须同时满足以下 10 项标准:

- `candidate_readable`.
- `ligand_valid`.
- `fixed_structure_match_success`.
- `old_clash_resolved`.
- `no_new_severe_clash`.
- `scaffold_stable`.
- `keep_region_stable`.
- `anchor_integrity`.
- `edit_compliance`.
- `pocket_retention`.

这意味着:

- 不是“生成出来”就算成功.
- 不是“没有新碰撞”就算成功.
- 必须旧碰撞消除, 无新严重碰撞, 局部结构保持, 连接点合理, 候选合法, 且仍在口袋中.
- 对 DiffSBDD / DiffDec 等可能改变拓扑或原子顺序的后端, `fixed_structure_match_success=true` 是进入可靠成功的必要条件.

## 4. Existing Result Contract

- mode: `formal_40_case`.
- selected_case_count: 40.
- formal_40_case_results_generated: True.
- training_or_finetuning_performed: False.
- h_clash_used_in_diffsbdd_generation: False.
- phase4_mask_seed_unchanged: True.

## 5. Backend Wording For Final Report

- `rule_fixed_topology`: 构象型强基线和可逆性 sanity check. 38/40 case 成功证明当前受控人工局部碰撞样本存在大量构象可逆失败, 但不能写成生成式局部修复主方法.
- `diffsbdd_conditional_inpainting`: 生成式局部补全有非零可靠修复结果, 是当前最值得继续修补的生成式局部补全后端.
- `diffdec_single_rgroup`: 环境, checkpoint 和 GPU formal run 已跑通, 但 0 reliable success. 主要问题是输入适配, anchor/scaffold 匹配, candidate mapping 和 generated R-group size 控制; `CL` vocabulary 只解释 1 个 execution failure.
- `diffsbdd_full_resampling`: 只能作为全配体重采样对照, 不能作为局部修复后端.
- `diffsbdd_joint_inpainting`: 当前 blocked, 不需要先修 joint 再出阶段 4.0 最终报告.

## 6. Backend Rates

| backend_name | selected_case_denominator | failure_attempt_rate | reliable_candidate_rate | sample_reliable_repair_yield | proposal_per_case_mean | cost_per_reliable_case |
| --- | --- | --- | --- | --- | --- | --- |
| diffdec_single_rgroup | 40 | 0.025000 | 0.000000 | 0.000000 | 8.000000 | NA |
| diffsbdd_conditional_inpainting | 40 | 0.025000 | 0.027244 | 0.225000 | 16.000000 | 71.111111 |
| diffsbdd_full_resampling | 40 | 0.000000 | 0.000000 | 0.000000 | 8.000000 | NA |
| diffsbdd_joint_inpainting | 40 | 1.000000 | NA | 0.000000 | 0.000000 | NA |
| rule_fixed_topology | 40 | 0.000000 | 0.709375 | 0.950000 | 30.000000 | 31.578947 |

## 7. DiffSBDD Center Sensitivity

| center | attempt_rows | candidate_count | execution_failure_count | reliable_candidate_success_count | sample_reliable_success_count |
| --- | --- | --- | --- | --- | --- |
| ligand | 40 | 312 | 1 | 5 | 4 |
| pocket | 40 | 312 | 1 | 12 | 7 |

- center-level sample counts are not additive because the same case can succeed under both centers.

## 8. Blocked Backends

- `diffsbdd_joint_inpainting`: status `blocked`, blocked_reason `official_inpaint_entrypoint_incompatible_with_joint_checkpoint:center_argument`.

## 9. New Closeout Patch Outputs

- `reports/phase4_0_backend_feasibility/backend_comparison_rates.csv`.
- `reports/phase4_0_backend_feasibility/diffsbdd_center_sensitivity.csv`.
- `reports/phase4_0_backend_feasibility/diffsbdd_center_sensitivity.md`.
- `reports/phase4_0_backend_feasibility/diffdec_failure_funnel.csv`.
- `reports/phase4_0_backend_feasibility/diffdec_failure_analysis.md`.
- `reports/phase4_0_backend_feasibility/rule_backend_diagnostic.md`.
- `reports/phase4_0_backend_feasibility/full_resampling_control_analysis.md`.
- `reports/phase4_0_backend_feasibility/full_resampling_global_control_metrics.csv`.
- `reports/phase4_0_backend_feasibility/phase4_0_closeout_patch_audit.md`.

## 10. Follow-Up Recommendation

- 可以进入 `phase4_0_final_experiment_report.md` 生成.
- 不建议直接以 `rule_fixed_topology` 作为生成式主线进入正式阶段 4.1.
- 建议新增阶段 4.0.1 或 4.0.5, 聚焦 DiffSBDD conditional adapter / anchor-aware filtering 修补和 DiffDec adapter 修补.
- 若要做 `phase4.1-rule-mini`, 只能作为规则型 sanity check, 不作为生成式修复主结果.
- 阶段 4.1 的 Random / Predicted / Oracle 正式掩码对照需要另行制定方案.

## 11. Validation Status

- 本收尾脚本只读取既有结果文件并写出派生报告, 未调用任何 repair backend.
- `conda run -n c2f_cpu python -m compileall src scripts`: passed.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_backend_feasibility.py -q`: 8 passed.
- `conda run -n c2f_cpu python -m pytest -q`: 128 passed.

## 12. Guardrail Statement

- 本次补丁不修改阶段 2 / 2.5 / 3 历史结果.
- 本次补丁不覆盖 `reports/phase3_label_provenance_audit/phase4_mask_seed.csv`.
- 本次补丁不提交 `external/DiffSBDD`, `external/DiffDec`, checkpoint, 大量候选 SDF 或日志缓存.
- 本次补丁不生成 `phase4_0_final_experiment_report.md`.
