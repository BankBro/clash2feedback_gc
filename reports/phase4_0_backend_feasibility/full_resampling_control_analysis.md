# DiffSBDD Full Resampling Control Analysis

## 1. Role

`diffsbdd_full_resampling` 是全配体重采样对照, 不是局部修复后端.

## 2. Why Local Repair Success Is Zero

- full resampling 不使用局部 reference mask.
- full resampling 不固定 keep region.
- full resampling 不保证 scaffold, anchor 或原 atom order 保留.
- 因此在阶段 4.0 的 reliable local repair 标准下, 0 reliable local repair success 是合理结果.

## 3. Global Control Metrics

| backend_name | candidate_denominator | candidate_readable_rate | ligand_valid_rate | pocket_retention_rate | no_new_severe_clash_rate | fixed_structure_match_rate | anchor_integrity_rate | reliable_local_repair_success_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| diffsbdd_full_resampling | 320 | 1.000000 | 0.978125 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0 |

## 4. Follow-Up

该后端只能作为“直接重新生成完整配体”的全局对照. 它不应进入阶段 4.1 的 Random / Predicted / Oracle 局部掩码组, 也不应被写成局部 mask repair 的成功后端.
