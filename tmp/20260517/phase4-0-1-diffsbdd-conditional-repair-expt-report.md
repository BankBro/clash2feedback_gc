# 阶段 4.0.1 DiffSBDD conditional repair 临时实验汇报

## 1. 实验边界

- 本文件是临时实验汇报, 不是正式 final report.
- 本阶段只做 DiffSBDD conditional inpainting 修补.
- 样本数: 40, 复用阶段 4.0 selected cases.
- 主设置: center=`pocket`.
- K 预算: [8, 16, 32].
- 未训练或微调 DiffSBDD, 未修改 DiffSBDD 原始去噪过程, 未声称 `H_clash` 进入生成过程.
- GPU 运行使用 `external/DiffSBDD` 本地实验分支 `20260517-080227-phase4-0-1-gpu-inpaint-fix`, patch commit `a3d49bba85d6426120759cd7b1b856d9b84471f2`; 补丁只修复 `inpaint.py` 在 molecule-building/SDF 写出前 `lig_mask` 与 CPU tensor 的设备不一致问题, 不改 denoising loop, 不合入原始 main.
- reliable repair candidate 继续沿用阶段 4.0 的 10 项标准.

## 2. 预算曲线

| candidate_budget_k | selected_case_denominator | attempt_rows | proposal_count_sum | candidate_count_sum | execution_failure_count | candidate_readable_count | fixed_structure_match_success_count | anchor_integrity_success_count | local_reconnect_pass_count | old_clash_resolved_count | no_new_severe_clash_count | reliable_candidate_success_count | sample_reliable_success_count | sample_reliable_repair_yield | reliable_candidate_rate | anchor_integrity_rate | local_reconnect_pass_rate | old_clash_resolved_rate | no_new_severe_clash_rate | runtime_sec_sum | cost_per_reliable_case |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 8 | 40 | 40 | 320 | 312 | 1 | 312 | 312 | 114 | 0 | 30 | 30 | 10 | 7 | 0.175000 | 0.032051 | 0.365385 | 0.000000 | 0.096154 | 0.096154 | 349.898481 | 45.714286 |
| 16 | 40 | 40 | 640 | 624 | 1 | 624 | 624 | 217 | 0 | 61 | 66 | 14 | 7 | 0.175000 | 0.022436 | 0.347756 | 0.000000 | 0.097756 | 0.105769 | 462.216100 | 91.428571 |
| 32 | 40 | 40 | 1280 | 1248 | 1 | 1248 | 1248 | 461 | 0 | 104 | 110 | 24 | 10 | 0.250000 | 0.019231 | 0.369391 | 0.000000 | 0.083333 | 0.088141 | 763.258701 | 128.000000 |

## 3. Failure Funnel

| candidate_budget_k | funnel_step | count | denominator | rate |
| --- | --- | --- | --- | --- |
| 8 | attempted_cases | 40 | 40 | 1.000000 |
| 8 | execution_success | 39 | 40 | 0.975000 |
| 8 | generated_candidates | 312 | 312 | 1.000000 |
| 8 | candidate_readable | 312 | 312 | 1.000000 |
| 8 | ligand_valid | 270 | 312 | 0.865385 |
| 8 | fixed_structure_match_success | 312 | 312 | 1.000000 |
| 8 | anchor_match_success | 312 | 312 | 1.000000 |
| 8 | local_reconnect_pass | 0 | 312 | 0.000000 |
| 8 | anchor_integrity | 114 | 312 | 0.365385 |
| 8 | old_clash_resolved | 30 | 312 | 0.096154 |
| 8 | no_new_severe_clash | 30 | 312 | 0.096154 |
| 8 | scaffold_stable | 32 | 312 | 0.102564 |
| 8 | keep_region_stable | 312 | 312 | 1.000000 |
| 8 | edit_compliance | 32 | 312 | 0.102564 |
| 8 | pocket_retention | 32 | 312 | 0.102564 |
| 8 | reliable_repair_success | 10 | 312 | 0.032051 |
| 16 | attempted_cases | 40 | 40 | 1.000000 |
| 16 | execution_success | 39 | 40 | 0.975000 |
| 16 | generated_candidates | 624 | 624 | 1.000000 |
| 16 | candidate_readable | 624 | 624 | 1.000000 |
| 16 | ligand_valid | 565 | 624 | 0.905449 |
| 16 | fixed_structure_match_success | 624 | 624 | 1.000000 |
| 16 | anchor_match_success | 624 | 624 | 1.000000 |
| 16 | local_reconnect_pass | 0 | 624 | 0.000000 |
| 16 | anchor_integrity | 217 | 624 | 0.347756 |
| 16 | old_clash_resolved | 61 | 624 | 0.097756 |
| 16 | no_new_severe_clash | 66 | 624 | 0.105769 |
| 16 | scaffold_stable | 67 | 624 | 0.107372 |
| 16 | keep_region_stable | 624 | 624 | 1.000000 |
| 16 | edit_compliance | 67 | 624 | 0.107372 |
| 16 | pocket_retention | 67 | 624 | 0.107372 |
| 16 | reliable_repair_success | 14 | 624 | 0.022436 |
| 32 | attempted_cases | 40 | 40 | 1.000000 |
| 32 | execution_success | 39 | 40 | 0.975000 |
| 32 | generated_candidates | 1248 | 1248 | 1.000000 |
| 32 | candidate_readable | 1248 | 1248 | 1.000000 |
| 32 | ligand_valid | 1092 | 1248 | 0.875000 |
| 32 | fixed_structure_match_success | 1248 | 1248 | 1.000000 |
| 32 | anchor_match_success | 1248 | 1248 | 1.000000 |
| 32 | local_reconnect_pass | 0 | 1248 | 0.000000 |
| 32 | anchor_integrity | 461 | 1248 | 0.369391 |
| 32 | old_clash_resolved | 104 | 1248 | 0.083333 |
| 32 | no_new_severe_clash | 110 | 1248 | 0.088141 |
| 32 | scaffold_stable | 113 | 1248 | 0.090545 |
| 32 | keep_region_stable | 1248 | 1248 | 1.000000 |
| 32 | edit_compliance | 113 | 1248 | 0.090545 |
| 32 | pocket_retention | 113 | 1248 | 0.090545 |
| 32 | reliable_repair_success | 24 | 1248 | 0.019231 |

## 4. 阶段 4.0 对比

| metric | phase4_0_diffsbdd_conditional_overall | phase4_0_diffsbdd_conditional_center_pocket | phase4_0_1_k8 | delta_k8_vs_phase4_0_overall | delta_k8_vs_phase4_0_pocket | phase4_0_1_k16 | delta_k16_vs_phase4_0_overall | delta_k16_vs_phase4_0_pocket | phase4_0_1_k32 | delta_k32_vs_phase4_0_overall | delta_k32_vs_phase4_0_pocket |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sample_reliable_success_count | 9.000000 | 7.000000 | 7.000000 | -2.000000 | 0.000000 | 7.000000 | -2.000000 | 0.000000 | 10.000000 | 1.000000 | 3.000000 |
| sample_reliable_repair_yield | 0.225000 | 0.175000 | 0.175000 | -0.050000 | 0.000000 | 0.175000 | -0.050000 | 0.000000 | 0.250000 | 0.025000 | 0.075000 |
| reliable_candidate_success_count | 17.000000 | 12.000000 | 10.000000 | -7.000000 | -2.000000 | 14.000000 | -3.000000 | 2.000000 | 24.000000 | 7.000000 | 12.000000 |
| reliable_candidate_rate | 0.027244 | 0.038462 | 0.032051 | 0.004807 | -0.006410 | 0.022436 | -0.004808 | -0.016026 | 0.019231 | -0.008013 | -0.019231 |
| anchor_integrity_rate | 0.403846 | 0.451923 | 0.365385 | -0.038461 | -0.086538 | 0.347756 | -0.056090 | -0.104167 | 0.369391 | -0.034455 | -0.082532 |
| local_reconnect_pass_rate | NA | NA | 0.000000 | NA | NA | 0.000000 | NA | NA | 0.000000 | NA | NA |
| old_clash_resolved_rate | 0.083333 | 0.073718 | 0.096154 | 0.012821 | 0.022436 | 0.097756 | 0.014423 | 0.024038 | 0.083333 | 0.000000 | 0.009615 |
| no_new_severe_clash_rate | 0.088141 | 0.080128 | 0.096154 | 0.008013 | 0.016026 | 0.105769 | 0.017628 | 0.025641 | 0.088141 | 0.000000 | 0.008013 |
| cost_per_reliable_case | 71.111111 | NA | 45.714286 | -25.396825 | NA | 91.428571 | 20.317460 | NA | 128.000000 | 56.888889 | NA |
| runtime_sec_sum | NA | NA | 349.898481 | NA | NA | 462.216100 | NA | NA | 763.258701 | NA | NA |

## 5. 验证状态

- `conda run -n c2f_cpu python -m compileall src scripts`: 通过.
- `conda run -n c2f_cpu python -m pytest tests/test_phase4_0_1_diffsbdd_conditional.py tests/test_phase4_backend_feasibility.py -q`: 14 passed.
- `conda run -n c2f_cpu python -m pytest -q`: 134 passed.
- selected cases denominator: 40 rows, 40 unique case_id.
- preflight cases: 5 rows, 均来自阶段 4.0 selected cases.
- `phase4_mask_seed.csv` SHA256 保持 `18cea12cc4f92a8f21f6f9de83c2ba551556e35a19e9d781d3a98f79b99097cc`.
- 禁止修改范围核查: `reports/phase2_injection/`, `reports/phase2_5_model_induced_audit/`, `reports/phase3_label_provenance_audit/`, `reports/phase4_0_backend_feasibility/`, `data/benchmarks/clashrepairbench_rg_artificial/v0_1/` 无 git status 输出.
- `external/DiffSBDD` 当前分支: `20260517-080227-phase4-0-1-gpu-inpaint-fix`; 当前 commit: `a3d49bba85d6426120759cd7b1b856d9b84471f2`; tracked working tree clean. `checkpoints/` 和 `__pycache__/` 仍为外部仓库未跟踪/忽略类本地文件, 不建议提交.

## 6. 远端审阅建议

建议提交到远端供网页版 ChatGPT 阅读的内容:

- 阶段 4.0.1 主项目代码, 配置和测试: `configs/phase4_0_1_diffsbdd_conditional_repair.yaml`, `scripts/phase4_0_1_diffsbdd_conditional_repair.py`, `src/clash2feedback/repair/phase4_0_1.py`, `src/clash2feedback/repair/fragment_diagnostics.py`, `src/clash2feedback/repair/diffsbdd_anchor_filter.py`, `src/clash2feedback/repair/reconnect_check.py`, `src/clash2feedback/repair/diffsbdd_adapter.py`, `tests/test_phase4_0_1_diffsbdd_conditional.py`.
- 轻量实验数据和汇总表: `reports/phase4_0_1_diffsbdd_conditional_repair/` 下的 `csv`, `json`, `md` 文件.
- 阶段方案和外部 baseline 记录: `docs/20260517-Clash2Feedback-GC_阶段4.0.1-DiffSBDD条件局部补全修补方案总纲.md`, `docs/external_baselines.md`.
- 临时分析入口: `tmp/20260517/phase4-0-1-diffsbdd-conditional-repair-expt-report.md`.
- 外部 DiffSBDD GPU patch 分支: `BankBro/DiffSBDD`, branch `20260517-080227-phase4-0-1-gpu-inpaint-fix`, commit `a3d49bba85d6426120759cd7b1b856d9b84471f2`.

不建议提交到远端的内容:

- `runs/phase4_0_1_diffsbdd_conditional_repair/` 下的 raw candidates, standardized candidates 和 logs.
- `external/DiffSBDD/checkpoints/` 及其他 checkpoint/cache.
- `external/DiffSBDD/__pycache__/` 和运行缓存.
