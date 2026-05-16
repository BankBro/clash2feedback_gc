# DiffDec Failure Analysis

## 1. Scope

- 本报告只读取已有 `candidate_manifest.csv`, `adapter_input_manifest.csv`, `verifier_outcome.csv`, `failure_cases.csv` 和 DiffDec 运行日志.
- 未重新调用 DiffDec, 未生成新候选, 未修改 `external/DiffDec` 源码或 denoising/sampling 过程.

## 2. Failure Funnel

| metric | count | denominator | rate | notes |
| --- | --- | --- | --- | --- |
| attempts | 40 | 40 | 1.000000 | DiffDec formal attempts. |
| execution_failures | 1 | 40 | 0.025000 | Execution-level failures before candidates. |
| generated_candidates | 312 | 312 | 1.000000 | Candidates emitted by attempts. |
| readable_candidates | 312 | 312 | 1.000000 |  |
| ligand_valid | 311 | 312 | 0.996795 |  |
| fixed_structure_match_success | 312 | 312 | 1.000000 |  |
| anchor_integrity_success | 309 | 312 | 0.990385 |  |
| generated_atom_count_mismatch | 194 | 312 | 0.621795 | Adapter mapping failure reason. |
| generated_atom_element_mismatch | 112 | 312 | 0.358974 | Adapter mapping failure reason. |
| old_clash_resolved | 0 | 312 | 0.000000 |  |
| no_new_severe_clash | 6 | 312 | 0.019231 |  |
| scaffold_stable | 6 | 312 | 0.019231 |  |
| keep_region_stable | 312 | 312 | 1.000000 |  |
| edit_compliance | 6 | 312 | 0.019231 |  |
| pocket_retention | 6 | 312 | 0.019231 |  |
| reliable_success | 0 | 312 | 0.000000 |  |

## 3. Top Failure Reasons

- top `failure_reason`: generated_atom_count_mismatch:3!=2 (37); generated_atom_element_mismatch:old_atom=30:Z=8 (36); generated_atom_element_mismatch:old_atom=31:Z=8 (33); generated_atom_count_mismatch:3!=4 (27); generated_atom_count_mismatch:6!=7 (22); generated_atom_count_mismatch:2!=7 (14); generated_atom_count_mismatch:3!=7 (12); generated_atom_count_mismatch:4!=5 (11); generated_atom_count_mismatch:8!=7 (10); generated_atom_element_mismatch:old_atom=12:Z=7 (9); generated_atom_count_mismatch:5!=4 (9); generated_atom_count_mismatch:3!=5 (8).
- top `verifier_failure_reasons`: old_clash_not_resolved (6).
- unsupported protein atom elements recovered from logs: CL=1.

## 4. Interpretation

DiffDec 当前不是环境阻塞. `model_inventory.csv` 显示环境和 checkpoint 已 ready, formal run 已使用 GPU 执行. 当前 0 reliable success 更应解释为输入适配, anchor/scaffold 匹配, candidate mapping 和 generated R-group size 控制尚未解决.

`CL` protein atom vocabulary 问题确实存在, 本次日志中对应 `case_002599` 的 `KeyError: 'CL'`, 但它只解释 1 个 execution failure. 其余 39 个 attempt 已生成候选并进入 verifier, 因此不能把 0 reliable success 简单归因于 protein atom vocabulary.

后续优先级建议:

- 先审计 `fixed_context.sdf` 和带星号出口 scaffold smiles 是否和 phase4 anchor 一致.
- 再修 generated R-group size / atom count 与 oracle mask size 的映射策略.
- 同步检查候选回填到原 ligand atom order 的 adapter, 尤其是 generated atom element mismatch 和 count mismatch.
- 最后修补 protein atom vocabulary, 包括 `CL` 等非标准或大写元素兼容.
