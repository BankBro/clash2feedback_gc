# DiffSBDD Conditional Center Sensitivity

## 1. Scope

- 本报告只读取既有 `candidate_manifest.csv` 和 `verifier_outcome.csv`, 未重新调用 DiffSBDD.
- `diffsbdd_conditional_inpainting` 对每个 selected case 分别尝试 `center=ligand` 和 `center=pocket`.
- center 优先从 `generation_metadata.center` 解析, 失败时回退到 `candidate_source` 或 `attempt_id`.

## 2. Center-Level Counters

| center | attempt_rows | candidate_count | execution_failure_count | candidate_readable_count | anchor_integrity_success_count | old_clash_resolved_count | no_new_severe_clash_count | reliable_candidate_success_count | sample_reliable_success_count |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ligand | 40 | 312 | 1 | 312 | 111 | 29 | 30 | 5 | 4 |
| pocket | 40 | 312 | 1 | 312 | 141 | 23 | 25 | 12 | 7 |

## 3. Failure Pattern

- `ligand` top failure reasons: generated_atom_element_mismatch:old_atom=12:Z=7 (30); generated_atom_element_mismatch:old_atom=32:Z=9 (26); generated_atom_element_mismatch:old_atom=13:Z=7 (25); anchor_integrity (24); generated_atom_element_mismatch:old_atom=33:Z=9 (23).
- `pocket` top failure reasons: generated_atom_element_mismatch:old_atom=33:Z=9 (31); generated_atom_element_mismatch:old_atom=13:Z=7 (27); generated_atom_element_mismatch:old_atom=32:Z=9 (25); generated_atom_element_mismatch:old_atom=12:Z=7 (24); generated_atom_element_mismatch:old_atom=31:Z=8 (20).

## 4. Interpretation

- 两个 center 均能产生可读候选, 但可靠修复数仍低, 主要瓶颈不是候选读取, 而是 anchor integrity, old clash resolved 和 no new severe clash 的联合满足.
- `sample_reliable_success_count` 是按单个 center 分别统计的 case 级成功数, ligand 和 pocket 之间可能重叠, 不能直接相加为总体 9/40.
- 当前结果证明 DiffSBDD conditional local completion 有非零可行性, 但进入后续阶段前需要 anchor-aware filtering, local reconnection check 和 adapter schema 的继续修补.
- `H_clash` 未进入 DiffSBDD 生成过程, 碰撞信息只在后验 verifier 中使用.
