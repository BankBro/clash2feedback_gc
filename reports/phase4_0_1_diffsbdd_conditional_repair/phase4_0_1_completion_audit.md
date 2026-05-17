# Phase 4.0.1 DiffSBDD Conditional Repair Completion Audit

## 1. Scope

- 本阶段只运行 `diffsbdd_conditional_inpainting`.
- center: `pocket`.
- selected cases: 40.
- candidate budgets: [8, 16, 32].
- no training or finetuning was performed.
- DiffSBDD original denoising loop was not modified.
- GPU inpainting used external DiffSBDD branch `20260517-080227-phase4-0-1-gpu-inpaint-fix` at commit `a3d49bba85d6426120759cd7b1b856d9b84471f2`; the patch only moves `lig_mask` to CPU before molecule-building post-processing.
- `H_clash` was not passed into DiffSBDD generation.
- phase4_mask_seed unchanged: True.

## 2. Budget Curve

| candidate_budget_k | selected_case_denominator | attempt_rows | proposal_count_sum | candidate_count_sum | execution_failure_count | candidate_readable_count | fixed_structure_match_success_count | anchor_integrity_success_count | local_reconnect_pass_count | old_clash_resolved_count | no_new_severe_clash_count | reliable_candidate_success_count | sample_reliable_success_count | sample_reliable_repair_yield | reliable_candidate_rate | anchor_integrity_rate | local_reconnect_pass_rate | old_clash_resolved_rate | no_new_severe_clash_rate | runtime_sec_sum | cost_per_reliable_case |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 40 | 40 | 320 | 312 | 1 | 312 | 312 | 114 | 0 | 30 | 30 | 10 | 7 | 0.175000 | 0.032051 | 0.365385 | 0.000000 | 0.096154 | 0.096154 | 349.898481 | 45.714286 |
| 16 | 40 | 40 | 640 | 624 | 1 | 624 | 624 | 217 | 0 | 61 | 66 | 14 | 7 | 0.175000 | 0.022436 | 0.347756 | 0.000000 | 0.097756 | 0.105769 | 462.216100 | 91.428571 |
| 32 | 40 | 40 | 1280 | 1248 | 1 | 1248 | 1248 | 461 | 0 | 104 | 110 | 24 | 10 | 0.250000 | 0.019231 | 0.369391 | 0.000000 | 0.083333 | 0.088141 | 763.258701 | 128.000000 |

## 3. Guardrails

- reliable repair candidate 继续沿用阶段 4.0 的 10 项标准.
- anchor-aware filtering 和 local reconnect check 是新增诊断/筛选, 不替代 reliable repair 标准.
- 阶段 4.0 历史结果未作为写入目标.
- `python -m compileall src scripts`: passed.
- targeted pytest: 14 passed.
- full pytest: 134 passed.
