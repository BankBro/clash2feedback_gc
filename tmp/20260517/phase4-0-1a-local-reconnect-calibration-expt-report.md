# Phase 4.0.1a Local Reconnect Calibration 临时实验汇报

> 本文件是临时实验汇报, 不是 final report.

## 1. 摘要

- 任务短名: `phase4-0-1a-local-reconnect-calibration`.
- 本次只做 report-only / audit-only 校准, 状态: `completed`.
- 本次未重跑 DiffSBDD, 未重新生成候选, 未训练或微调模型, 未修改 DiffSBDD denoising loop.
- 本次未修改 reliable repair 10 项标准, 也未把 local reconnect 加入 reliable repair 标准.
- DiffSBDD 候选重标注数量: 2187.
- reconnect 三分类: single-anchor pass 0, multi-attachment out-of-scope 563, invalid 1624.
- 阶段 4.0.1 原 `reliable_repair_success=True`: 48.
- strict single-anchor shadow reliable count: 0.
- clean positive: 40/40 进入 `single_anchor_reconnect_pass`.
- rule positive: 227/227 进入 `single_anchor_reconnect_pass`.
- synthetic negative: disconnected / floating / missing-anchor 进入 `invalid_reconnect`, extra-attachment 进入 `multi_attachment_out_of_scope`.
- 规则校准建议用途: `soft_filter`. 对当前 DiffSBDD 结果的解释是: 现有候选在 strict single-anchor reconnect 下没有成功样本.

## 2. 口径

- `multi_attachment_out_of_scope` 不等于 ligand invalid.
- `reliable_repair_success` 保持阶段 4.0 / 4.0.1 的 10 项标准, 本阶段不回写历史结果.
- `strict_single_anchor_shadow_reliable` 只用于观察后续若加严 single-anchor reconnect 的影响.
- `local_reconnect_check` 当前可以解释为经过 clean / rule / synthetic negative 初步校准的诊断和软筛选候选项, 但不能直接反向推翻阶段 4.0.1 既有 reliable repair 结果.
- 阶段 4.0.1a 不做 Random / Predicted / Oracle 正式对照, 不做 DiffDec adapter 修补, 不声称 `H_clash` 进入生成过程.

## 3. 输入和实现

主要输入:

- `docs/20260517-Clash2Feedback-GC_阶段4.0.1a局部接回诊断规则校准方案总纲.md`
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_verifier_outcome.csv`
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_anchor_reconnect_audit.csv`
- `reports/phase4_0_1_diffsbdd_conditional_repair/diffsbdd_candidate_manifest.csv`
- `reports/phase4_0_backend_feasibility/verifier_outcome.csv`
- `reports/phase4_0_backend_feasibility/candidate_manifest.csv`
- `reports/phase4_0_1_diffsbdd_conditional_repair/selected_cases.csv`
- `data/benchmarks/clashrepairbench_rg_artificial/v0_1/manifest.parquet`

本次新增入口:

- `configs/phase4_0_1a_local_reconnect_calibration.yaml`
- `scripts/phase4_0_1a_local_reconnect_calibration.py`
- `src/clash2feedback/repair/reconnect_calibration.py`
- `tests/test_phase4_0_1a_local_reconnect_calibration.py`

三分类优先级:

1. 候选不可读, ligand invalid, fixed structure mapping 失败, anchor 不可映射, generated fragment 为空, floating fragment, 未接回 anchor -> `invalid_reconnect`.
2. 候选可读且 mapping / anchor / anchor connection 成功, 但存在额外 attachment 或多 attachment -> `multi_attachment_out_of_scope`.
3. 单一 anchor neighbor, 无 extra attachment, 无 floating fragment -> `single_anchor_reconnect_pass`.

## 4. Shadow Analysis

| candidate_budget_k | candidate_count | reliable_repair_success_count | strict_single_anchor_shadow_reliable_count | strict_single_anchor_shadow_reliable_rate | single_anchor_reconnect_pass_count | multi_attachment_out_of_scope_count | invalid_reconnect_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| -1 | 2187 | 48 | 0 | 0 | 0 | 563 | 1624 |
| 8 | 313 | 10 | 0 | 0 | 0 | 79 | 234 |
| 16 | 625 | 14 | 0 | 0 | 0 | 160 | 465 |
| 32 | 1249 | 24 | 0 | 0 | 0 | 324 | 925 |

## 5. Category Counts

| source_group | candidate_budget_k | reconnect_category | count |
| --- | --- | --- | --- |
| clean_positive | 0 | single_anchor_reconnect_pass | 40 |
| diffsbdd_candidates | 8 | invalid_reconnect | 234 |
| diffsbdd_candidates | 8 | multi_attachment_out_of_scope | 79 |
| diffsbdd_candidates | 16 | invalid_reconnect | 465 |
| diffsbdd_candidates | 16 | multi_attachment_out_of_scope | 160 |
| diffsbdd_candidates | 32 | invalid_reconnect | 925 |
| diffsbdd_candidates | 32 | multi_attachment_out_of_scope | 324 |
| rule_positive | 8 | single_anchor_reconnect_pass | 227 |
| synthetic_negative | 0 | invalid_reconnect | 3 |
| synthetic_negative | 0 | multi_attachment_out_of_scope | 1 |

## 6. 结果解读

- clean positive 和 rule positive 全部通过, 说明当前检查器对当前 single-anchor R-group 任务的正样本没有明显误伤.
- synthetic negative 的最小负样本符合预期: 断开, floating, missing-anchor 进入 invalid; extra-attachment 进入 out-of-scope.
- DiffSBDD 候选中没有 strict single-anchor pass, 因而如果把 strict single-anchor reconnect 作为后续硬门槛, 阶段 4.0.1 的 48 个 reliable candidates 会全部被 shadow 过滤.
- 563 条 DiffSBDD 候选被拆分为 `multi_attachment_out_of_scope`, 它们不应被写成 ligand invalid. 这些候选更适合后续作为 multi-anchor / linker repair 方向的现象证据.
- 当前结果支持把 local reconnect 暂时作为诊断项或软筛选候选项, 不支持在没有进一步人工结构抽查前直接加入 reliable repair 10 项标准.

## 7. 输出文件

建议提交到远端, 供网页版 ChatGPT 读取:

- `reports/phase4_0_1a_local_reconnect_calibration/local_reconnect_calibration_summary.json`
- `reports/phase4_0_1a_local_reconnect_calibration/local_reconnect_category_counts.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/reconnect_shadow_reliable_analysis.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/diffsbdd_reconnect_reclassified.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/clean_positive_reconnect_check.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/rule_positive_reconnect_check.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/synthetic_negative_reconnect_check.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/local_reconnect_calibration_cases.csv`
- `reports/phase4_0_1a_local_reconnect_calibration/phase4_0_1a_completion_audit.md`
- `tmp/20260517/phase4-0-1a-local-reconnect-calibration-expt-report.md`

不需要提交 `runs/`, `external/`, checkpoint, 生成日志或重资产 SDF.

## 8. 测试和不变性

- `conda run -n c2f_cpu python -m compileall src scripts`: passed.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1a_local_reconnect_calibration.py -q`: 4 passed.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1_diffsbdd_conditional.py -q`: 6 passed.
- `conda run -n c2f_cpu python -m pytest -q`: 138 passed.
- `reports/phase3_label_provenance_audit/phase4_mask_seed.csv` SHA256: `18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc`.
- 用户列出的阶段 2, 2.5, 3, 4.0, 4.0.1 历史结果文件未修改.
