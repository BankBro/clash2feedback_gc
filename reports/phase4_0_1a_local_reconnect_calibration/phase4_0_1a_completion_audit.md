# Phase 4.0.1a Local Reconnect Calibration Completion Audit

## 1. Scope

- 本阶段为 report-only / audit-only.
- 未重跑 DiffSBDD, 未重新生成候选, 未训练或微调模型.
- 未修改 reliable repair 10 项标准, 未把 local reconnect 加入 reliable repair 标准.
- `multi_attachment_out_of_scope` 只表示超出当前 single-anchor R-group repair 范围, 不等于 ligand invalid.

## 2. Repository Facts

- branch: `20260517-161211-phase4-0-1a`.
- HEAD: `93f1e221cc7e959248a418382e0800250bf6d5f4`.
- plan doc exists: True.
- phase4_mask_seed_sha256: `18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc`.

## 3. Calibration Summary

- DiffSBDD candidates reclassified: 2187.
- clean positive cases: 40.
- rule positive cases: 227.
- synthetic negative cases: 4.
- single-anchor pass: 0.
- multi-attachment out-of-scope: 563.
- invalid reconnect: 1624.
- strict single-anchor shadow reliable count: 0.
- recommended use: `soft_filter`.

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
