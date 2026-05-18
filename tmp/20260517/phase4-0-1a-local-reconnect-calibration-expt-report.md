# Phase 4.0.1a Local Reconnect Calibration 临时实验汇报

> 本文件是临时实验汇报, 不是 final report.

## 1. 摘要

- 本次只做 report-only / audit-only 校准, 状态: `completed`.
- DiffSBDD 候选重标注数量: 2187.
- reconnect 三分类: single-anchor pass 0, multi-attachment out-of-scope 332, invalid 1855.
- shadow reliable count: 0.
- 建议用途: `soft_filter`.

## 2. 口径

- `multi_attachment_out_of_scope` 不等于 ligand invalid.
- `ligand_valid` 表示 RDKit sanitize 层面的化学可解析性, 不等价于候选是单个完整 ligand.
- `candidate_single_fragment=false` 或 `candidate_total_fragment_count > 1` 在 reconnect 三分类中优先归入 `invalid_reconnect`.
- `reliable_repair_success` 保持阶段 4.0 / 4.0.1 的 10 项标准, 本阶段不回写历史结果.
- `strict_single_anchor_shadow_reliable` 只用于观察后续若加严 single-anchor reconnect 的影响.

## 3. Shadow Analysis

| candidate_budget_k | candidate_count | reliable_repair_success_count | strict_single_anchor_shadow_reliable_count | strict_single_anchor_shadow_reliable_rate | single_anchor_reconnect_pass_count | multi_attachment_out_of_scope_count | invalid_reconnect_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| -1 | 2187 | 48 | 0 | 0 | 0 | 332 | 1855 |
| 8 | 313 | 10 | 0 | 0 | 0 | 44 | 269 |
| 16 | 625 | 14 | 0 | 0 | 0 | 94 | 531 |
| 32 | 1249 | 24 | 0 | 0 | 0 | 194 | 1055 |

## 4. Category Counts

| source_group | candidate_budget_k | reconnect_category | count |
| --- | --- | --- | --- |
| clean_positive | 0 | single_anchor_reconnect_pass | 40 |
| diffsbdd_candidates | 8 | invalid_reconnect | 269 |
| diffsbdd_candidates | 8 | multi_attachment_out_of_scope | 44 |
| diffsbdd_candidates | 16 | invalid_reconnect | 531 |
| diffsbdd_candidates | 16 | multi_attachment_out_of_scope | 94 |
| diffsbdd_candidates | 32 | invalid_reconnect | 1055 |
| diffsbdd_candidates | 32 | multi_attachment_out_of_scope | 194 |
| rule_positive | 8 | single_anchor_reconnect_pass | 227 |
| synthetic_negative | 0 | invalid_reconnect | 3 |
| synthetic_negative | 0 | multi_attachment_out_of_scope | 1 |
