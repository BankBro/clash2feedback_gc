# Phase 4.0.1a Local Reconnect Calibration Completion Audit

## 1. Scope

- 本阶段为 report-only / audit-only.
- 未重跑 DiffSBDD, 未重新生成候选, 未训练或微调模型.
- 未修改 reliable repair 10 项标准, 未把 local reconnect 加入 reliable repair 标准.
- `multi_attachment_out_of_scope` 只表示超出当前 single-anchor R-group repair 范围, 不等于 ligand invalid.

## 2. Repository Facts

- branch: `20260517-161211-phase4-0-1a`.
- HEAD: `347a303529a547b4f9ccfdbf39c1605299cc518e`.
- plan doc exists: True.
- phase4_mask_seed_sha256: `18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc`.

## 3. Calibration Summary

- DiffSBDD candidates reclassified: 2187.
- clean positive cases: 40.
- rule positive cases: 227.
- synthetic negative cases: 4.
- single-anchor pass: 0.
- multi-attachment out-of-scope: 332.
- invalid reconnect: 1855.
- strict single-anchor shadow reliable count: 0.
- recommended use: `soft_filter`.

## 4. Shadow Analysis

| candidate_budget_k | candidate_count | reliable_repair_success_count | strict_single_anchor_shadow_reliable_count | strict_single_anchor_shadow_reliable_rate | single_anchor_reconnect_pass_count | multi_attachment_out_of_scope_count | invalid_reconnect_count |
| --- | --- | --- | --- | --- | --- | --- | --- |
| -1 | 2187 | 48 | 0 | 0 | 0 | 332 | 1855 |
| 8 | 313 | 10 | 0 | 0 | 0 | 44 | 269 |
| 16 | 625 | 14 | 0 | 0 | 0 | 94 | 531 |
| 32 | 1249 | 24 | 0 | 0 | 0 | 194 | 1055 |

## 5. Category Counts

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
