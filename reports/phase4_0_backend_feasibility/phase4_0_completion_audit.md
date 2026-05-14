# Phase 4.0 Backend Feasibility Completion Audit

## 1. Scope

- selected cases: 40.
- mode: formal_40_case.
- no training or finetuning was performed.
- DiffSBDD/DiffDec original source and denoising loops were not modified.
- `H_clash` was not passed into DiffSBDD or DiffDec generation.

## 2. Selection

- expected case count: 40.
- selected case count: 40.
- phase4_mask_seed unchanged: True.

## 3. Backend Summary

| backend_name | attempts | candidates | failure_attempts | reliable_candidates | reliable_cases |
|---|---:|---:|---:|---:|---:|
| diffdec_single_rgroup | 40 | 313 | 1 | 0 | 0 |
| diffsbdd_conditional_inpainting | 80 | 626 | 2 | 17 | 9 |
| diffsbdd_full_resampling | 40 | 320 | 0 | 0 | 0 |
| diffsbdd_joint_inpainting | 40 | 40 | 40 | 0 | 0 |
| rule_fixed_topology | 40 | 320 | 0 | 227 | 38 |

## 4. Inventory

| backend_name | status | blocked_reason |
|---|---|---|
| rule_fixed_topology | ready |  |
| diffsbdd_conditional_inpainting | ready |  |
| diffsbdd_full_resampling | ready |  |
| diffsbdd_joint_inpainting | blocked | official_inpaint_entrypoint_incompatible_with_joint_checkpoint:center_argument |
| diffdec_single_rgroup | ready |  |

## 5. Verification

- verifier outcome rows: 1619.
- reliable candidate successes: 244.
- `backend_comparison.csv` contains backend-level counters.
- `failure_cases.csv` contains non-reliable candidate and attempt rows.
