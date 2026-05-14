# Phase 4.0 Backend Feasibility Preflight Report

## 1. Scope

- preflight cases: 5.
- mode: preflight_only.
- 40 case 正式小规模实验未生成.
- 本轮只实现规则型固定拓扑局部构象修复和 DiffSBDD CrossDocked full-atom conditional local completion 最小闭环.
- DiffSBDD/DiffDec 原始源码和去噪过程未修改.
- `H_clash` 未进入 DiffSBDD 生成命令.

## 2. Selected Cases

| case_id | split | injection_mode | difficulty | oracle_mask_size | selection_reason |
|---|---|---|---|---:|---|
| case_001001 | test | directed_clash | easy | 5 | directed test easy, mask/depth moderate |
| case_001243 | test | easy_rotation | easy | 5 | easy_rotation test easy |
| case_000982 | test | torsion_perturb | easy | 5 | torsion test easy |
| case_001238 | test | directed_clash | medium | 5 | test medium coverage |
| case_000703 | train | easy_rotation | medium | 4 | medium non-directed supplement |

## 3. Model Inventory

| backend_name | status | blocked_reason |
|---|---|---|
| rule_fixed_topology | ready |  |
| diffsbdd_conditional_inpainting | ready |  |
| diffsbdd_joint_inpainting | blocked | checkpoint_missing:/home/lyj/mnt/project/clash2feedback_gc/external/DiffSBDD/checkpoints/crossdocked_fullatom_joint.ckpt |
| diffdec_single_rgroup | blocked | checkpoint_missing:/home/lyj/mnt/project/clash2feedback_gc/external/DiffDec/checkpoints/diffdec_single.ckpt;conda_env_not_ready:failed |

## 4. Backend Outcomes

| backend_name | attempts | candidate_rows | failure_attempts | sample_reliable_success_count |
|---|---:|---:|---:|---:|
| diffdec_single_rgroup | 5 | 5 | 5 | 0 |
| diffsbdd_conditional_inpainting | 10 | 10 | 10 | 0 |
| diffsbdd_joint_inpainting | 5 | 5 | 5 | 0 |
| rule_fixed_topology | 5 | 40 | 0 | 4 |

## 5. Verification

- candidate manifest rows: 60.
- verifier outcome rows: 60.
- reliable candidate successes: 31.
- phase4_mask_seed unchanged: True.
